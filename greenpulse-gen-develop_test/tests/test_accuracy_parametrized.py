import pytest
import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Union, Optional

from src.accuracy.base import BaseAccuracy
from src.accuracy.rmse import rmse
from src.accuracy.mae import mae
from src.accuracy.mape import mape
from src.accuracy.mre import mre
from src.params import CStaParams

from accuracy_test_utils import (
    create_sample_timeseries_data,
    create_pred_dict,
    get_null_logger,
    compute_expected_metrics,
    compare_metrics
)


@pytest.fixture
def logger():
    """返回用于测试的日志记录器"""
    return get_null_logger()


@pytest.fixture
def staParam():
    """返回用于测试的站点参数"""
    param = CStaParams()
    param.staId = "test_station"
    param.staName = "Test Station"
    setattr(param, "capacity", 200.0)  # 200 MW容量
    return param


@pytest.mark.parametrize("accuracy_class", [rmse, mae, mape, mre])
def test_accuracy_class_initialization(accuracy_class, staParam):
    """测试各种准确率指标类的初始化"""
    obj = accuracy_class(staParam)
    assert isinstance(obj, BaseAccuracy)
    assert isinstance(obj, accuracy_class)


@pytest.mark.parametrize("method_name", ["ust_day", "ust_month", "st_day", "st_month"])
@pytest.mark.parametrize("accuracy_class", [rmse, mae, mape, mre])
def test_accuracy_methods_exist(accuracy_class, method_name, staParam):
    """测试各种准确率指标类是否实现了所有必要的方法"""
    obj = accuracy_class(staParam)
    assert hasattr(obj, method_name)
    assert callable(getattr(obj, method_name))


@pytest.mark.parametrize("start_date", ["2023-01-01", "2023-06-15", "2023-12-31"])
@pytest.mark.parametrize("num_days", [1, 3, 7])
@pytest.mark.parametrize("error_level", [0.05, 0.1, 0.2])
@pytest.mark.parametrize("accuracy_class,metric_name", [
    (rmse, "rmse"), 
    (mae, "mae"),
    (mape, "mape"),
    (mre, "mre")
])
def test_accuracy_calculation(start_date, num_days, error_level, 
                              accuracy_class, metric_name, staParam, logger):
    """参数化测试不同情况下的准确率计算"""
    # 创建样本数据
    periods = 24 * num_days
    obs = create_sample_timeseries_data(
        start_date=start_date,
        periods=periods,
        freq='H',
        pattern='sin',
        base_value=100.0,
        amplitude=80.0,
        noise_level=5.0,
        capacity=staParam.capacity
    )
    
    # 创建预测字典
    pred_dict = create_pred_dict(
        obs=obs,
        start_date=start_date,
        num_days=num_days,
        error_level=error_level
    )
    
    # 初始化准确率对象
    acc_obj = accuracy_class(staParam)
    
    # 调用准确率计算方法
    result = acc_obj.ust_day(pred_dict, obs, logger)
    
    # 验证结果
    assert isinstance(result, dict)
    assert len(result) == num_days
    
    # 对每个预测日期进行验证
    for day in range(num_days):
        pred_date = pd.Timestamp(start_date) + pd.Timedelta(days=day)
        
        # 确保结果中有该日期
        assert pred_date in result
        
        # 获取该日期的预测
        day_pred = pred_dict[pred_date]
        
        # 计算期望指标值
        expected = compute_expected_metrics(obs, day_pred, [metric_name])
        computed = {"acc": result[pred_date]["acc"]}
        
        # 比较计算值与期望值
        match, details = compare_metrics(
            {metric_name: computed["acc"]}, 
            expected,
            tolerance=1e-5
        )
        
        assert match, f"指标不匹配: {details}"


@pytest.mark.parametrize("missing_ratio", [0.0, 0.1, 0.3])
@pytest.mark.parametrize("zero_ratio", [0.0, 0.1, 0.2])
@pytest.mark.parametrize("accuracy_class", [rmse, mae, mape, mre])
def test_accuracy_with_special_values(missing_ratio, zero_ratio, 
                                      accuracy_class, staParam, logger):
    """测试特殊值(缺失值、零值)情况下的准确率计算"""
    # 创建带有缺失值和零值的观测数据
    obs = create_sample_timeseries_data(
        periods=24,
        missing_ratio=missing_ratio,
        zero_ratio=zero_ratio
    )
    
    # 创建预测数据
    pred_dict = create_pred_dict(obs, error_level=0.1)
    
    # 初始化准确率对象并计算
    acc_obj = accuracy_class(staParam)
    result = acc_obj.ust_day(pred_dict, obs, logger)
    
    # 针对不同的准确率类型进行特殊处理
    if accuracy_class == mape and zero_ratio > 0:
        # MAPE可能会因零值而产生问题
        assert isinstance(result, dict)
    else:
        # 其他准确率指标应该能正常处理
        assert isinstance(result, dict)
        assert pd.Timestamp('2023-01-01') in result
        assert "acc" in result[pd.Timestamp('2023-01-01')]


@pytest.mark.parametrize("diurnal_error", [False, True])
@pytest.mark.parametrize("systematic_bias", [-0.2, 0.0, 0.2])
@pytest.mark.parametrize("accuracy_class", [rmse, mae, mape, mre])
def test_accuracy_with_error_patterns(diurnal_error, systematic_bias, 
                                     accuracy_class, staParam, logger):
    """测试不同误差模式下的准确率计算"""
    # 创建观测数据
    obs = create_sample_timeseries_data(periods=48, freq='H')
    
    # 创建带有不同误差模式的预测数据
    pred_dict = create_pred_dict(
        obs,
        num_days=2,
        error_level=0.1,
        systematic_bias=systematic_bias,
        diurnal_error=diurnal_error
    )
    
    # 初始化准确率对象并计算
    acc_obj = accuracy_class(staParam)
    result = acc_obj.ust_day(pred_dict, obs, logger)
    
    # 验证结果
    assert isinstance(result, dict)
    assert len(result) == 2  # 应该有两天的结果


@pytest.mark.parametrize("method_name", ["ust_day", "ust_month", "st_day", "st_month"])
@pytest.mark.parametrize("accuracy_class", [rmse, mae])
def test_different_time_scales(method_name, accuracy_class, staParam, logger):
    """测试不同时间尺度下的准确率计算"""
    # 创建样本数据 - 为月尺度创建更长的序列
    periods = 24 * 30 if "month" in method_name else 24
    obs = create_sample_timeseries_data(periods=periods, freq='H')
    
    # 创建预测字典
    num_days = 30 if "month" in method_name else 1
    pred_dict = create_pred_dict(obs, num_days=num_days)
    
    # 初始化准确率对象
    acc_obj = accuracy_class(staParam)
    
    # 调用对应的方法
    method = getattr(acc_obj, method_name)
    result = method(pred_dict, obs, logger)
    
    # 验证结果
    assert isinstance(result, dict)
    expected_days = num_days if "day" in method_name else 1
    assert len(result) == expected_days


@pytest.mark.parametrize("accuracy_class", [rmse, mae, mape, mre])
def test_empty_pred_dict(accuracy_class, staParam, logger):
    """测试空预测字典的情况"""
    # 创建观测数据
    obs = create_sample_timeseries_data()
    
    # 创建空预测字典
    pred_dict = {}
    
    # 初始化准确率对象
    acc_obj = accuracy_class(staParam)
    
    # 验证行为
    result = acc_obj.ust_day(pred_dict, obs, logger)
    assert isinstance(result, dict)
    assert len(result) == 0


@pytest.mark.parametrize("accuracy_class", [rmse, mae, mape, mre])
def test_one_point_prediction(accuracy_class, staParam, logger):
    """测试只有一个点的预测"""
    # 创建只有一个点的观测和预测
    index = [pd.Timestamp('2023-01-01 12:00:00')]
    obs = pd.Series([100.0], index=index)
    pred = pd.Series([110.0], index=index)
    pred_dict = {pd.Timestamp('2023-01-01'): pred}
    
    # 初始化准确率对象
    acc_obj = accuracy_class(staParam)
    
    # 计算准确率
    result = acc_obj.ust_day(pred_dict, obs, logger)
    
    # 验证结果
    assert isinstance(result, dict)
    assert pd.Timestamp('2023-01-01') in result
    assert "acc" in result[pd.Timestamp('2023-01-01')]
    
    # 验证计算值
    if accuracy_class == rmse:
        assert result[pd.Timestamp('2023-01-01')]["acc"] == 10.0
    elif accuracy_class == mae:
        assert result[pd.Timestamp('2023-01-01')]["acc"] == 10.0
    elif accuracy_class == mape:
        assert result[pd.Timestamp('2023-01-01')]["acc"] == 10.0
    elif accuracy_class == mre:
        assert result[pd.Timestamp('2023-01-01')]["acc"] == 0.1


if __name__ == "__main__":
    pytest.main(["-v", "test_accuracy_parametrized.py"])