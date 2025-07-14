import pytest
import numpy as np
import pandas as pd
import logging
import os
import importlib
from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta

from src.accuracy.base import BaseAccuracy
from src.params import CStaParams, CParams
from src.accuracy import __getattr__ as accuracy_getattr
from accuracy_test_utils import create_sample_timeseries_data, create_pred_dict, get_null_logger


@pytest.fixture
def setup_environment():
    """设置测试环境"""
    # 创建测试目录
    os.makedirs("test_output", exist_ok=True)
    
    # 设置测试参数
    staParam = CStaParams()
    staParam.staId = "test_station"
    staParam.staName = "Test Station"
    setattr(staParam, "capacity", 200.0)  # 200 MW容量
    staParam.accuracy = ["rmse", "mae", "mape", "mre"]
    
    # 设置日志
    logger = logging.getLogger("test_logger")
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    return {
        "staParam": staParam,
        "logger": logger
    }


def test_accuracy_dynamic_import():
    """测试准确率模块的动态导入机制"""
    # 测试导入存在的模块
    rmse_module = accuracy_getattr("rmse")
    assert hasattr(rmse_module, "rmse")
    
    mae_module = accuracy_getattr("mae")
    assert hasattr(mae_module, "mae")
    
    # 测试导入不存在的模块
    with pytest.raises(AttributeError):
        accuracy_getattr("non_existent_module")


def test_all_accuracy_metrics_implementation(setup_environment):
    """测试所有准确率指标的实现"""
    staParam = setup_environment["staParam"]
    logger = setup_environment["logger"]
    
    # 创建测试数据
    obs = create_sample_timeseries_data(
        start_date='2023-01-01',
        periods=72,
        pattern='sin',
        base_value=100.0,
        amplitude=80.0
    )
    
    pred_dict = create_pred_dict(
        obs=obs,
        start_date='2023-01-01',
        num_days=3,
        error_level=0.1
    )
    
    # 测试所有准确率指标
    for acc_name in staParam.accuracy:
        # 动态导入准确率模块
        acc_module = accuracy_getattr(acc_name)
        acc_class = getattr(acc_module, acc_name)
        
        # 创建准确率对象
        acc_obj = acc_class(staParam)
        
        # 测试所有时间尺度方法
        for method_name in ["ust_day", "ust_month", "st_day", "st_month"]:
            method = getattr(acc_obj, method_name)
            
            # 调用准确率计算方法
            result = method(pred_dict, obs, logger)
            
            # 验证结果
            assert isinstance(result, dict)
            if method_name.endswith("day"):
                assert len(result) == 3  # 3天的结果
            else:
                assert len(result) >= 1  # 至少一个月度结果
            
            # 验证结果格式
            for date, metrics in result.items():
                assert isinstance(date, pd.Timestamp)
                assert "acc" in metrics
                assert isinstance(metrics["acc"], float) or np.isnan(metrics["acc"])
                assert "score" in metrics


def test_integrating_with_task_workflow(setup_environment):
    """测试准确率模块与任务工作流的集成"""
    staParam = setup_environment["staParam"]
    logger = setup_environment["logger"]
    
    # 模拟任务工作流中使用的数据格式
    obs = create_sample_timeseries_data(
        start_date='2023-01-01',
        periods=24,
        pattern='sin'
    )
    
    pred_dict = create_pred_dict(
        obs=obs,
        start_date='2023-01-01',
        num_days=1,
        error_level=0.1
    )
    
    # 创建结果容器
    acc_results = {}
    
    # 为每个准确率指标计算结果
    for acc_name in staParam.accuracy:
        # 动态导入准确率模块
        acc_module = accuracy_getattr(acc_name)
        acc_class = getattr(acc_module, acc_name)
        
        # 创建准确率对象
        acc_obj = acc_class(staParam, logger=logger)
        
        # 计算超短期日准确率
        result = acc_obj.ust_day(pred_dict, obs, logger)
        
        # 保存结果
        acc_results[acc_name] = result
    
    # 验证所有准确率指标都已计算
    assert len(acc_results) == len(staParam.accuracy)
    
    # 验证所有准确率指标的结果格式
    for acc_name, result in acc_results.items():
        assert isinstance(result, dict)
        assert pd.Timestamp('2023-01-01') in result
        assert "acc" in result[pd.Timestamp('2023-01-01')]
        assert "score" in result[pd.Timestamp('2023-01-01')]


def test_different_time_periods(setup_environment):
    """测试不同时间周期的准确率计算"""
    staParam = setup_environment["staParam"]
    logger = setup_environment["logger"]
    
    # 测试不同的时间周期
    time_periods = [
        # (开始日期, 结束日期, 周期)
        ('2023-01-01', '2023-01-03', 'day'),
        ('2023-01-01', '2023-01-31', 'month'),
        ('2023-01-01', '2023-03-01', 'month'),
    ]
    
    for start_date, end_date, period_type in time_periods:
        # 计算测试数据的周期
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
        days = (end - start).days + 1
        hours = int(days * 24)  # 确保是整数
        
        # 创建观测数据
        obs = create_sample_timeseries_data(
            start_date=start_date,
            periods=hours,
            pattern='sin'
        )
        
        # 创建预测字典
        pred_dict = create_pred_dict(
            obs=obs,
            start_date=start_date,
            num_days=int(days),  # 确保是整数
            error_level=0.1
        )
        
        # 测试rmse指标
        rmse_module = accuracy_getattr("rmse")
        rmse_obj = rmse_module.rmse(staParam)
        
        # 根据周期类型选择方法
        if period_type == 'day':
            method = rmse_obj.ust_day
        else:
            method = rmse_obj.ust_month
        
        # 计算准确率
        result = method(pred_dict, obs, logger)
        
        # 验证结果
        assert isinstance(result, dict)
        if period_type == 'day':
            assert len(result) == days
        else:
            # 月度结果可能按月聚合
            months_in_range = len(set([(date.year, date.month) for date in pd.date_range(start_date, end_date)]))
            assert len(result) <= months_in_range


def test_real_world_data_simulation(setup_environment):
    """测试模拟真实世界数据的准确率计算"""
    staParam = setup_environment["staParam"]
    logger = setup_environment["logger"]
    
    # 创建复杂的观测数据，包含日间变化和季节性模式
    # 一年的小时数据 (8760小时)
    start_date = '2023-01-01'
    periods = 365 * 24
    
    # 基础数据
    dates = pd.date_range(start=start_date, periods=periods, freq='H')
    base_values = np.zeros(periods)
    
    # 添加日间模式 (白天发电，夜间不发电)
    for i, date in enumerate(dates):
        hour = date.hour
        # 白天 (6:00-18:00)
        if 6 <= hour < 18:
            # 日间曲线，上午上升，下午下降
            if hour < 12:
                base_values[i] = (hour - 6) / 6 * 180  # 上升到180
            else:
                base_values[i] = (18 - hour) / 6 * 180  # 从180下降到0
        else:
            # 夜间保持零
            base_values[i] = 0
    
    # 添加季节性变化 (夏季发电更多)
    for i, date in enumerate(dates):
        month = date.month
        # 夏季 (5-8月) 产能提高
        if 5 <= month <= 8:
            base_values[i] *= 1.3
        # 冬季 (11-2月) 产能降低
        elif month <= 2 or month >= 11:
            base_values[i] *= 0.7
    
    # 添加云量影响 (随机波动)
    cloud_impact = np.random.normal(0, 0.2, periods)
    for i in range(periods):
        if base_values[i] > 0:  # 只在白天有云的影响
            base_values[i] *= (1 + cloud_impact[i])
    
    # 添加随机噪声
    noise = np.random.normal(0, 5, periods)
    base_values += noise
    
    # 确保数值在合理范围内
    base_values = np.clip(base_values, 0, staParam.capacity)
    
    # 创建观测序列
    obs = pd.Series(base_values, index=dates)
    
    # 创建预测字典 (按季度的一个样本)
    seasons = [
        ('2023-01-15', 7),  # 冬季
        ('2023-04-15', 7),  # 春季
        ('2023-07-15', 7),  # 夏季
        ('2023-10-15', 7),  # 秋季
    ]
    
    # 测试每个季节的数据
    for start_date, days in seasons:
        # 提取该时间段的观测数据
        start_ts = pd.Timestamp(start_date)
        end_ts = start_ts + pd.Timedelta(days=days)
        period_mask = (obs.index >= start_ts) & (obs.index < end_ts)
        period_obs = pd.Series(obs[period_mask])  # 确保是Series类型
        
        # 创建预测数据
        pred_dict = create_pred_dict(
            obs=period_obs,
            start_date=start_date,
            num_days=days,
            error_level=0.15,  # 增加误差水平
            systematic_bias=0.05,  # 添加系统性偏差
            diurnal_error=True  # 添加日间误差模式
        )
        
        # 测试所有准确率指标
        for acc_name in ["rmse", "mae"]:
            # 动态导入准确率模块
            acc_module = accuracy_getattr(acc_name)
            acc_class = getattr(acc_module, acc_name)
            
            # 创建准确率对象
            acc_obj = acc_class(staParam)
            
            # 计算准确率
            result = acc_obj.ust_day(pred_dict, period_obs, logger)
            
            # 验证结果
            assert isinstance(result, dict)
            assert len(result) == days
            
            # 日志记录平均准确率
            avg_acc = np.mean([metrics["acc"] for metrics in result.values()])
            logger.info(f"季节: {start_date}, 指标: {acc_name}, 平均准确率: {avg_acc:.2f}")


if __name__ == "__main__":
    pytest.main(["-v", "test_accuracy_integration.py"])