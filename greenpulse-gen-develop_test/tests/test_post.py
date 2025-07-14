import os
import sys
import pytest
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pytz
from pytz import UTC

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.post.ST.post import PostProcess
from src.params import (
    CParamsInit,
    CParamsTask,
    CStaParams,
    CParamsPath
)

@pytest.fixture
def test_params():
    """Fixture providing test parameters."""
    sta = CStaParams()
    sta.staId = "1306320124660000"
    sta.staName = "华润分布式光伏"
    sta.staLon = 117.067
    sta.staLat = 38.404
    sta.staAlt = 0
    sta.staCap = 30
    sta.staType = "PV"
    sta.timeLiness = ["UST"]
    sta.algorithm = {"baseline": ["last"]}
    sta.dataset = ["EC_C1D"]
    return sta


def generate_test_data(sta_id="station001", n_days=30, end_date=None):
    """
    生成符合 load_data 方法要求的 X 和 Y 测试数据

    参数:
        sta_id: 站点ID (需与 self.staParam.staId 一致)
        n_days: 生成数据的天数
        end_date: 结束日期 (默认当前日期)

    返回:
        X (dict): 多天滚动预测结果
        Y (dict): 实况数据
    """

    # 1. 生成预测数据 X (dict of pd.DataFrame)
    X = {
        sta_id: {
            'ST': {
                'Forecast': {}  # 初始化空的 Forecast 字典
            }
        }
    }

    # 参数设置
    base_date = datetime(2025, 4, 2, 12, 0)
    timezone = pytz.timezone('UTC')
    base_date = timezone.localize(base_date)
    n_intervals = 1247  # 每个预报结果的时刻数

    # 生成列名（表示预报时间偏移量）
    col_names = [f"{(i * 15) // 60}h{(i * 15) % 60}m" for i in range(n_intervals)]
    # 示例输出：['0h0m', '0h15m', '0h30m', ...]

    # 初始化DataFrame（行=起报日，列=预报时刻）
    power_df = pd.DataFrame(
        index=[(base_date + timedelta(days=day))
               for day in range(n_days)],
        columns=col_names
    )

    # 填充数据
    for day in range(n_days):
        # 每行生成n_intervals个随机数
        power_df.iloc[day, :] = np.random.uniform(0, 30, n_intervals)

    # 存储到数据结构中
    X[sta_id]['ST']['Forecast'] = {
        'power': power_df,  # 形状: (n_days×n_intervals)
    }

    # 2. 生成实况数据 Y (dict of pd.Series)
    Y = {
        sta_id: {
            'power': pd.DataFrame(),
            'toradi': pd.DataFrame(),
            'dradi': pd.DataFrame(),
            'tpower': pd.DataFrame(),
            'start_capacity': pd.DataFrame(),
            'power_am': pd.DataFrame(),
            'power_pm': pd.DataFrame(),
            'opower': pd.DataFrame()
        }
    }

    # 参数设置
    total_points = n_days * 96  # 总数据点数 (10天×96个15分钟点)

    # 生成完整的时间索引（连续的15分钟间隔）
    full_time_index = pd.date_range(
        start=base_date,
        periods=total_points,
        freq="15T"
    )

    # 为每个变量创建DataFrame（单列，索引为完整时间序列）
    Y[sta_id]['power'] = pd.DataFrame({
        'power': np.random.uniform(0, 30, total_points)
    }, index=full_time_index)

    Y[sta_id]['toradi'] = pd.DataFrame({
        'toradi': np.random.uniform(0, 1, total_points)
    }, index=full_time_index)

    Y[sta_id]['dradi'] = pd.DataFrame({
        'dradi': np.random.uniform(0, 1, total_points)
    }, index=full_time_index)

    Y[sta_id]['tpower'] = pd.DataFrame({
        'tpower': np.random.uniform(0, 30, total_points)
    }, index=full_time_index)

    Y[sta_id]['start_capacity'] = pd.DataFrame({
        'start_capacity': np.random.uniform(0, 100, total_points)
    }, index=full_time_index)

    Y[sta_id]['power_am'] = pd.DataFrame({
        'power_am': np.random.uniform(30, 80, total_points)
    }, index=full_time_index)

    Y[sta_id]['power_pm'] = pd.DataFrame({
        'power_pm': np.random.uniform(70, 120, total_points)
    }, index=full_time_index)

    Y[sta_id]['opower'] = pd.DataFrame({
        'opower': np.random.uniform(0, 30, total_points)
    }, index=full_time_index)

    return X, Y


def generate_test_pre_data(sta_id="station001", n_days=30, start_date=None):
    """
    生成模拟光伏/风电预测数据 (未来数据)

    参数:
        sta_id (str): 站点ID
        n_days (int): 生成预测数据的天数
        start_date (str): 起始日期(格式: 'YYYY-MM-DD')，默认使用当前日期

    返回:
        dict: 包含模拟预测数据的嵌套字典，格式为:
            {
                sta_id: {
                    'ST': {
                        'Forecast': {
                            'power': df,
                            'toradi': df,
                            ...
                        }
                    }
                }
            }
            其中每个df包含两列: time(作为index)和value
    """


    end_date = start_date + timedelta(days=n_days)
    date_range = pd.date_range(start=start_date, end=end_date, freq='15T')
    time_mask = (date_range.hour >= 6) & (date_range.hour < 18)

    # 创建Forecast字典，直接包含各个变量的DataFrame
    forecast_dict = {
        'power': _create_var_df(sta_id, date_range, time_mask),
        'radi': _create_var_df(sta_id, date_range, time_mask),
        'ghi_pw': _create_var_df(sta_id, date_range, time_mask),
        'poa_pw': _create_var_df(sta_id, date_range, time_mask)
    }

    # 创建嵌套字典结构
    result = {
        sta_id: {
            'ST': {
                'Forecast': forecast_dict
            }
        }
    }

    return result


def _create_var_df(sta_id, date_range, time_mask):
    """创建单个变量的DataFrame"""
    return pd.DataFrame({
        'station_id': [sta_id] * len(date_range),
        'time': date_range,
        'value': np.where(time_mask, np.random.uniform(0, 100, len(date_range)), 0)
    }).set_index('time')

def test_post_process(test_params):
    log = logging.getLogger(__name__)
    sta = test_params

    post = PostProcess(sta)
    X , Y = generate_test_data(sta_id=sta.staId, n_days=30)
    # print(X)
    # print(Y)

    # 调用被测试函数
    fit_coef = post.fit(X, Y,log)
    print(fit_coef)
    if np.allclose(fit_coef, 1.0):
        raise ValueError("错误：所有拟合系数都为1")
    else:
        print("拟合系数验证通过")

    test_pre_data = generate_test_pre_data(sta_id=sta.staId, n_days=30,
                                           start_date=datetime(2025, 4, 2, 12, 0,tzinfo=UTC))
    dataColumn = post.transform(test_pre_data)
    print(dataColumn)



if __name__ == '__main__':
    pytest.main(["-v", "-s", "-k", "test_post_process"])


