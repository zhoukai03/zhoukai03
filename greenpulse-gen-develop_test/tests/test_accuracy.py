import unittest
import pytest
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import os
import sys
import importlib

from src.accuracy.base import BaseAccuracy
from src.accuracy.rmse import rmse
from src.accuracy.mae import mae
from src.accuracy.mape import mape
from src.accuracy.mre import mre
from src.params import CStaParams, CParams


class TestBaseAccuracy:
    """测试基础准确率抽象类"""

    def test_base_is_abstract(self):
            """测试BaseAccuracy是抽象类不能被实例化"""
            # 使用模拟对象作为参数
            mock_param = MagicMock(spec=CStaParams)
            with pytest.raises(TypeError):
                BaseAccuracy(mock_param)


class MockAccuracy(BaseAccuracy):
    """模拟实现BaseAccuracy的子类，用于测试"""
    
    def __init__(self, staParam: CStaParams, **kwargs):
        self.staParam = staParam
        self.logger = kwargs.get('logger')
    
    def ust_day(self, pred, obs, logger, **kwargs):
        return {pd.Timestamp("2023-01-01"): {"acc": 0.1, "score": 0.9}}
    
    def ust_month(self, pred, obs, logger, **kwargs):
        return {pd.Timestamp("2023-01-01"): {"acc": 0.2, "score": 0.8}}
    
    def st_day(self, pred, obs, logger, **kwargs):
        return {pd.Timestamp("2023-01-01"): {"acc": 0.3, "score": 0.7}}
    
    def st_month(self, pred, obs, logger, **kwargs):
        return {pd.Timestamp("2023-01-01"): {"acc": 0.4, "score": 0.6}}


@pytest.fixture
def sample_data():
    """创建测试数据"""
    # 创建观测数据
    dates = pd.date_range(start='2023-01-01', periods=24, freq='15min')
    obs_values = np.sin(np.linspace(0, 2*np.pi, 24)) * 100 + 100  # 模拟一天的功率曲线
    obs = pd.Series(obs_values, index=dates)
    
    # 创建预测数据
    # 略微偏离观测数据，以便计算准确率
    pred_values = obs_values + np.random.normal(0, 10, 24)
    pred = pd.Series(pred_values, index=dates)
    
    # 创建预测字典，模拟不同预测时间
    pred_dict = {
        pd.Timestamp('2023-01-01'): pred
    }
    
    return {
        'obs': obs,
        'pred_dict': pred_dict
    }


@pytest.fixture
def setup_params():
    """设置测试参数"""
    staParam = CStaParams()
    staParam.staId = "1306320124660000"
    staParam.staName = "回归测试站点"
    # 使用属性设置方法而不是直接赋值
    setattr(staParam, "capacity", 100.0)  # 100 MW容量
    
    logger = logging.getLogger("test_logger")
    
    return {
        'staParam': staParam,
        'logger': logger
    }


class TestRMSE:
    """测试RMSE准确率指标"""
    
    def test_rmse_initialization(self, setup_params):
        """测试RMSE实例化"""
        rmse_obj = rmse(setup_params['staParam'])
        assert isinstance(rmse_obj, BaseAccuracy)
        assert isinstance(rmse_obj, rmse)
    
    def test_rmse_calculation_ust_day(self, sample_data, setup_params):
        """测试RMSE超短期日尺度计算"""
        rmse_obj = rmse(setup_params['staParam'])
        result = rmse_obj.ust_day(
            sample_data['pred_dict'], 
            sample_data['obs'], 
            setup_params['logger']
        )
        
        # 验证结果格式
        assert isinstance(result, dict)
        for date, metrics in result.items():
            assert isinstance(date, pd.Timestamp)
            assert "acc" in metrics
            assert "score" in metrics
            assert isinstance(metrics["acc"], float)
            assert np.isnan(metrics["score"])  # 分数应该是NaN
        
        # 验证RMSE值在合理范围内
        for date, metrics in result.items():
            assert 0 <= metrics["acc"] <= 30  # 根据样本数据和噪声水平，RMSE应在这个范围内
    
    def test_rmse_calculation_st_day(self, sample_data, setup_params):
        """测试RMSE短期日尺度计算"""
        rmse_obj = rmse(setup_params['staParam'])
        result = rmse_obj.st_day(
            sample_data['pred_dict'], 
            sample_data['obs'], 
            setup_params['logger']
        )
        
        # 验证结果格式和值
        assert isinstance(result, dict)
        for date, metrics in result.items():
            assert "acc" in metrics
            assert 0 <= metrics["acc"] <= 30
    
    def test_rmse_with_missing_values(self, setup_params):
        """测试RMSE对缺失值的处理"""
        # 创建带有缺失值的数据
        dates = pd.date_range(start='2023-01-01', periods=24, freq='H')
        obs_values = np.sin(np.linspace(0, 2*np.pi, 24)) * 100 + 100
        obs_values[5:10] = np.nan  # 添加一些缺失值
        obs = pd.Series(obs_values, index=dates)
        
        pred_values = obs_values + np.random.normal(0, 10, 24)
        pred_values[15:20] = np.nan  # 添加一些不同位置的缺失值
        pred = pd.Series(pred_values, index=dates)
        
        pred_dict = {pd.Timestamp('2023-01-01'): pred}
        
        rmse_obj = rmse(setup_params['staParam'])
        
        # 由于存在NaN，预期会得到NaN结果或产生警告/错误
        result = rmse_obj.ust_day(pred_dict, obs, setup_params['logger'])
        
        # 验证结果包含NaN或已经处理了缺失值
        for date, metrics in result.items():
            assert isinstance(metrics["acc"], float) or np.isnan(metrics["acc"])


class TestMAE:
    """测试MAE准确率指标"""
    
    def test_mae_initialization(self, setup_params):
        """测试MAE实例化"""
        mae_obj = mae(setup_params['staParam'])
        assert isinstance(mae_obj, BaseAccuracy)
        assert isinstance(mae_obj, mae)
    
    def test_mae_calculation_ust_day(self, sample_data, setup_params):
        """测试MAE超短期日尺度计算"""
        mae_obj = mae(setup_params['staParam'])
        result = mae_obj.ust_day(
            sample_data['pred_dict'], 
            sample_data['obs'], 
            setup_params['logger']
        )
        
        # 验证结果格式
        assert isinstance(result, dict)
        for date, metrics in result.items():
            assert "acc" in metrics
            assert isinstance(metrics["acc"], float)
            assert np.isnan(metrics["score"])  # 分数应该是NaN
        
        # 验证MAE值在合理范围内
        for date, metrics in result.items():
            assert 0 <= metrics["acc"] <= 20  # 根据样本数据和噪声水平，MAE应在这个范围内
    
    def test_mae_st_month(self, sample_data, setup_params):
        """测试MAE短期月尺度计算"""
        mae_obj = mae(setup_params['staParam'])
        result = mae_obj.st_month(
            sample_data['pred_dict'], 
            sample_data['obs'], 
            setup_params['logger']
        )
        
        # 验证结果格式和值
        assert isinstance(result, dict)
        for date, metrics in result.items():
            assert "acc" in metrics
            assert 0 <= metrics["acc"] <= 20


class TestMAPE:
    """测试MAPE准确率指标"""
    
    def test_mape_initialization(self, setup_params):
        """测试MAPE实例化"""
        mape_obj = mape(setup_params['staParam'])
        assert isinstance(mape_obj, BaseAccuracy)
        assert isinstance(mape_obj, mape)
    
    def test_mape_calculation_ust_day(self, sample_data, setup_params):
        """测试MAPE超短期日尺度计算"""
        mape_obj = mape(setup_params['staParam'])
        result = mape_obj.ust_day(
            sample_data['pred_dict'], 
            sample_data['obs'], 
            setup_params['logger']
        )
        
        # 验证结果格式
        assert isinstance(result, dict)
        for date, metrics in result.items():
            assert "acc" in metrics
            assert isinstance(metrics["acc"], float)
        
        # 验证MAPE值在合理范围内 (百分比)
        for date, metrics in result.items():
            assert 0 <= metrics["acc"] <= 30  # 预期MAPE在0-30%之间


class TestMRE:
    """测试MRE准确率指标"""
    
    def test_mre_initialization(self, setup_params):
        """测试MRE实例化"""
        mre_obj = mre(setup_params['staParam'])
        assert isinstance(mre_obj, BaseAccuracy)
        assert isinstance(mre_obj, mre)
    
    def test_mre_calculation_ust_day(self, sample_data, setup_params):
        """测试MRE超短期日尺度计算"""
        mre_obj = mre(setup_params['staParam'])
        result = mre_obj.ust_day(
            sample_data['pred_dict'], 
            sample_data['obs'], 
            setup_params['logger']
        )
        
        # 验证结果格式
        assert isinstance(result, dict)
        for date, metrics in result.items():
            assert "acc" in metrics
            assert isinstance(metrics["acc"], float)
        
        # 验证MRE值在合理范围内
        for date, metrics in result.items():
            assert 0 <= metrics["acc"] <= 0.3  # 预期MRE在0-0.3之间


class TestAccuracyEdgeCases:
    """测试边界情况"""
    
    def test_empty_data(self, setup_params):
        """测试空数据处理"""
        # 创建空数据
        empty_dates = pd.DatetimeIndex([])
        empty_obs = pd.Series([], index=empty_dates)
        empty_pred = pd.Series([], index=empty_dates)
        empty_pred_dict = {pd.Timestamp('2023-01-01'): empty_pred}
        
        # 测试各个准确率指标
        rmse_obj = rmse(setup_params['staParam'])
        mae_obj = mae(setup_params['staParam'])
        
        # 对于空数据，预期结果可能是NaN或引发警告/错误
        rmse_result = rmse_obj.ust_day(empty_pred_dict, empty_obs, setup_params['logger'])
        mae_result = mae_obj.ust_day(empty_pred_dict, empty_obs, setup_params['logger'])
        
        # 验证结果
        for result in [rmse_result, mae_result]:
            assert isinstance(result, dict)
            for date, metrics in result.items():
                assert isinstance(metrics, dict)
                assert "acc" in metrics
    
    def test_mismatched_indices(self, setup_params):
        """测试索引不匹配的情况"""
        # 创建不匹配的数据
        obs_dates = pd.date_range(start='2023-01-01', periods=24, freq='H')
        pred_dates = pd.date_range(start='2023-01-01 12:00:00', periods=24, freq='H')
        
        obs_values = np.sin(np.linspace(0, 2*np.pi, 24)) * 100 + 100
        pred_values = np.cos(np.linspace(0, 2*np.pi, 24)) * 100 + 100
        
        obs = pd.Series(obs_values, index=obs_dates)
        pred = pd.Series(pred_values, index=pred_dates)
        
        pred_dict = {pd.Timestamp('2023-01-01'): pred}
        
        # 测试RMSE
        rmse_obj = rmse(setup_params['staParam'])
        result = rmse_obj.ust_day(pred_dict, obs, setup_params['logger'])
        
        # 验证结果 - 只有重叠的部分应该被使用
        assert isinstance(result, dict)
        for date, metrics in result.items():
            assert isinstance(metrics["acc"], float) or np.isnan(metrics["acc"])
    
    def test_zero_values(self, setup_params):
        """测试观测值为零的情况（重要测试MAPE）"""
        # 创建包含零值的数据
        dates = pd.date_range(start='2023-01-01', periods=24, freq='H')
        obs_values = np.ones(24) * 10  # 设置为10
        obs_values[5:10] = 0  # 添加一些零值
        obs = pd.Series(obs_values, index=dates)
        
        pred_values = np.ones(24) * 12  # 略高于观测值
        pred = pd.Series(pred_values, index=dates)
        
        pred_dict = {pd.Timestamp('2023-01-01'): pred}
        
        # 测试MAPE (可能会因零值而出现问题)
        mape_obj = mape(setup_params['staParam'])
        result = mape_obj.ust_day(pred_dict, obs, setup_params['logger'])
        
        # 验证结果 - 应该能处理零值
        assert isinstance(result, dict)


class TestAccuracyIntegration:
    """集成测试"""
    
    def test_multiple_timestamps(self, setup_params):
        """测试处理多个时间戳的预测"""
        # 创建多个时间点的数据
        all_dates = pd.date_range(start='2023-01-01', periods=72, freq='H')
        obs_values = np.sin(np.linspace(0, 6*np.pi, 72)) * 100 + 100
        obs = pd.Series(obs_values, index=all_dates)
        
        # 创建三天的预测，每天单独一个条目
        pred_dict = {}
        for day in range(3):
            day_start = pd.Timestamp('2023-01-01') + pd.Timedelta(days=day)
            day_end = day_start + pd.Timedelta(days=1) - pd.Timedelta(hours=1)
            day_indices = pd.date_range(start=day_start, end=day_end, freq='H')
            day_values = obs_values[day*24:(day+1)*24] + np.random.normal(0, 5, 24)
            pred_dict[day_start] = pd.Series(day_values, index=day_indices)
        
        # 测试RMSE
        rmse_obj = rmse(setup_params['staParam'])
        result = rmse_obj.ust_day(pred_dict, obs, setup_params['logger'])
        
        # 验证结果 - 应该有3个日期条目
        assert len(result) == 3
        for date, metrics in result.items():
            assert isinstance(metrics["acc"], float)
    
    def test_module_import(self):
        """测试动态导入准确率算法"""
        # 测试从accuracy模块动态导入算法
        import src.accuracy
        
        # 测试导入rmse
        rmse_module = getattr(src.accuracy, 'rmse')
        assert hasattr(rmse_module, 'rmse')
        
        # 测试导入不存在的算法
        with pytest.raises(AttributeError):
            getattr(src.accuracy, 'non_existent_algorithm')


if __name__ == "__main__":
    pytest.main(["-v", "test_accuracy.py"])
