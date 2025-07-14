"""
测试 modelset 模块的单元测试和集成测试

本测试模块包含对 modelset 模块的全面测试，包括：
1. 测试模型动态加载功能
2. 测试模型基类的接口
3. 测试具体模型实现的功能
4. 测试模型预测流程
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime, timedelta
from enum import Enum

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入被测试模块
from src import modelset
from src.modelset.base import BaseModel
from src.params import CStaParams
from src.config.TypeDefine import TimeLiness

# 测试用的固定时间戳
TEST_DATETIME = pd.Timestamp('2023-05-01 12:00:00')

# 测试用的站点ID
TEST_STA_ID = '1000000000000001'

# 测试用的时效类型
TEST_TIMELINESS = TimeLiness.UST

# 测试用的算法和版本
TEST_ALGORITHM = 'baseline'
TEST_VERSION = 'last'#


class MockTimeLiness(Enum):
    """模拟 TimeLiness 枚举用于测试"""
    UST = 1
    ST = 2
    MT = 3
    SS = 4


@pytest.fixture
def mock_sta_params():
    """创建一个模拟的站点参数对象"""
    params = MagicMock(spec=CStaParams)
    params.staId = TEST_STA_ID
    params.staName = "Test Station"
    params.staLon = 120.0  # 经度
    params.staLat = 30.0   # 纬度
    params.staAlt = 50.0   # 海拔高度(米)
    params.staCap = 10.0   # 装机容量(MW)
    params.timeLiness = ['UST', 'ST', 'MT', 'SS']
    params.algorithm = {TEST_ALGORITHM: [TEST_VERSION]}
    params.dataset = ['test_dataset']
    return params


@pytest.fixture
def mock_logger():
    """创建一个模拟的日志记录器"""
    return MagicMock()


@pytest.fixture
def mock_data_loader():
    """创建一个模拟的数据加载器"""
    return MagicMock()


class TestModelSetModule:
    """测试 modelset 模块的基本功能"""

    def test_get_version_success(self, mock_sta_params):
        """测试成功获取模型版本"""
        # 模拟 importlib.import_module 的行为
        with patch('importlib.import_module') as mock_import:
            # 设置模拟返回值
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            
            # 调用被测试函数
            module = modelset.getVersion(TEST_TIMELINESS, TEST_ALGORITHM)
            
            # 验证导入的模块
            assert module == mock_module
            mock_import.assert_called_once_with(
                f'.{TEST_TIMELINESS.name}.{TEST_ALGORITHM}', 
                'src.modelset'
            )
    
    def test_get_version_import_error(self, mock_sta_params):
        """测试导入不存在的模块时的错误处理"""
        with patch('importlib.import_module') as mock_import:
            # 模拟导入错误
            mock_import.side_effect = ImportError("Module not found")
            
            # 验证抛出 ImportError
            with pytest.raises(ImportError):
                modelset.getVersion(TEST_TIMELINESS, "nonexistent_algorithm")
    
    def test_modelget_success(self, mock_sta_params, mock_logger):
        """测试成功获取模型实例"""
        # 模拟模型类
        mock_model_class = MagicMock()
        mock_model_instance = MagicMock()
        mock_model_class.return_value = mock_model_instance
        
        # 模拟 getVersion 返回的模块
        mock_module = MagicMock()
        mock_module.last = mock_model_class  # 使用版本名称作为属性
        
        with patch('src.modelset.getVersion', return_value=mock_module) as mock_get_version:
            # 调用被测试函数
            model = modelset.modelget(
                mock_sta_params,
                TEST_TIMELINESS,
                TEST_ALGORITHM,
                TEST_VERSION,
                logger=mock_logger
            )
            
            # 验证返回的模型实例
            assert model == mock_model_instance
            
            # 验证模型类被正确初始化
            mock_model_class.assert_called_once_with(mock_sta_params, logger=mock_logger)
            
            # 验证日志记录
            mock_logger.info.assert_any_call(
                f"Loading model: {TEST_TIMELINESS.name}.{TEST_ALGORITHM}"
            )
            mock_logger.info.assert_any_call(
                f"Initializing model: [{TEST_ALGORITHM}] with version: [{TEST_VERSION}]"
            )
            mock_logger.info.assert_any_call(f"Model initialized: {mock_model_instance}")
    
    def test_modelget_version_not_found(self, mock_sta_params, mock_logger):
        """测试版本不存在时的错误处理"""
        # 模拟模块，但不包含请求的版本
        mock_module = MagicMock()
        mock_module.some_other_version = MagicMock()
        
        with patch('src.modelset.getVersion', return_value=mock_module):
            # 验证抛出 AttributeError
            with pytest.raises(AttributeError) as exc_info:
                modelset.modelget(
                    mock_sta_params,
                    TEST_TIMELINESS,
                    TEST_ALGORITHM,
                    "nonexistent_version",
                    logger=mock_logger
                )
            
            # 验证错误消息
            assert "Model version 'nonexistent_version' not found in module" in str(exc_info.value)


class TestBaseModel:
    """测试 BaseModel 基类"""
    
    def test_base_model_abstract_methods(self):
        """测试 BaseModel 的抽象方法"""
        # 创建一个具体的子类，不实现任何抽象方法
        class ConcreteModel(BaseModel):
            pass
        
        # 验证实例化会引发 TypeError
        with pytest.raises(TypeError) as exc_info:
            ConcreteModel()
        
        # 验证错误消息包含所有未实现的抽象方法
        error_msg = str(exc_info.value)
        assert "Can't instantiate abstract class" in error_msg
        assert "__init__" in error_msg
        assert "load" in error_msg
        assert "predict" in error_msg
        assert "train" in error_msg
        assert "tuning" in error_msg
    
    def test_base_model_implementation(self, mock_sta_params, mock_logger, mock_data_loader):
        """测试实现 BaseModel 的具体类"""
        # 创建一个实现所有抽象方法的具体类
        class TestModel(BaseModel):
            def __init__(self, staParam, **kwargs):
                self.staParam = staParam
                self.kwargs = kwargs
                self.model = None
            
            def load(self, model, patternLogger=None):
                self.model = model
                if patternLogger:
                    patternLogger.info("Model loaded")
            
            def predict(self, X, taskDate, staParam, patternLogger, dataLoader, **kwargs):
                if patternLogger:
                    patternLogger.info(f"Predicting for {taskDate}")
                # 返回一个简单的预测结果
                return pd.DataFrame({
                    'time': [taskDate + timedelta(minutes=15*i) for i in range(4)],
                    'power': [0.0, 0.5, 1.0, 0.5]
                }).set_index('time')
            
            def train(self, X, Y, taskDateList, staParam, patternLogger, dataLoader, **kwargs):
                if patternLogger:
                    patternLogger.info(f"Training with {len(taskDateList)} dates")
                # 返回一个简单的模型
                return {"trained": True}
            
            def tuning(self, X, Y, taskDateList, staParam, patternLogger, dataLoader, **kwargs):
                if patternLogger:
                    patternLogger.info("Tuning model")
                # 返回调优后的模型
                return {"tuned": True}
        
        # 测试初始化
        model = TestModel(mock_sta_params, logger=mock_logger)
        assert model.staParam == mock_sta_params
        assert model.kwargs == {"logger": mock_logger}
        
        # 测试 load 方法
        test_model = {"test": "model"}
        model.load(test_model, patternLogger=mock_logger)
        assert model.model == test_model
        mock_logger.info.assert_called_with("Model loaded")
        
        # 测试 predict 方法
        X = {"test": "data"}
        predictions = model.predict(
            X=X,
            taskDate=TEST_DATETIME,
            staParam=mock_sta_params,
            patternLogger=mock_logger,
            dataLoader=mock_data_loader
        )
        assert isinstance(predictions, pd.DataFrame)
        assert 'power' in predictions.columns
        assert len(predictions) == 4
        mock_logger.info.assert_called_with(f"Predicting for {TEST_DATETIME}")
        
        # 测试 train 方法
        Y = {"test": "labels"}
        task_dates = [TEST_DATETIME - timedelta(days=i) for i in range(3)]
        trained_model = model.train(
            X=X,
            Y=Y,
            taskDateList=task_dates,
            staParam=mock_sta_params,
            patternLogger=mock_logger,
            dataLoader=mock_data_loader
        )
        assert trained_model == {"trained": True}
        mock_logger.info.assert_called_with(f"Training with {len(task_dates)} dates")
        
        # 测试 tuning 方法
        tuned_model = model.tuning(
            X=X,
            Y=Y,
            taskDateList=task_dates,
            staParam=mock_sta_params,
            patternLogger=mock_logger,
            dataLoader=mock_data_loader
        )
        assert tuned_model == {"tuned": True}
        mock_logger.info.assert_called_with("Tuning model")


class TestBaselineModel:
    """测试基线模型实现"""
    
    @patch('pvlib.location.Location.get_solarposition')
    @patch('pvlib.location.Location.get_clearsky')
    def test_baseline_model_predict(self, mock_clearsky, mock_solar_position, mock_sta_params, mock_logger, mock_data_loader):
        """测试基线模型的预测功能"""
        # 导入基线模型
        from src.modelset.UST.baseline import last as BaselineModel
        
        # 准备测试数据
        X = {
            TEST_STA_ID: {
                'UST': {
                    'test_dataset': {
                        'test_element': pd.DataFrame(
                            index=[TEST_DATETIME],
                            columns=[f"col_{i}" for i in range(10)]
                        )
                    }
                }
            }
        }
        
        # 模拟 pvlib 返回值
        mock_solar_position.return_value = pd.DataFrame({
            'zenith': [45.0] * 4,
            'azimuth': [180.0] * 4
        }, index=pd.date_range(start=TEST_DATETIME, periods=4, freq='15T'))
        
        mock_clearsky.return_value = pd.DataFrame({
            'ghi': [0, 500, 1000, 800],
            'dni': [0, 400, 800, 600],
            'dhi': [0, 100, 200, 200]
        }, index=pd.date_range(start=TEST_DATETIME, periods=4, freq='15T'))
        
        # 创建模型实例
        model = BaselineModel(mock_sta_params, logger=mock_logger)
        
        # 训练模型（设置拟合参数）
        model.model = {
            'fit_radi': np.linspace(0, 1000, 1000),
            'fit_pw': np.linspace(0, mock_sta_params.staCap, 1000)
        }
        
        # 执行预测
        predictions = model.predict(
            X=X,
            taskDate=TEST_DATETIME,
            staParam=mock_sta_params,
            patternLogger=mock_logger,
            dataLoader=mock_data_loader
        )
        
        # 验证返回结果
        assert isinstance(predictions, pd.DataFrame)
        assert 'power' in predictions.columns
        assert 'radi' in predictions.columns
        assert len(predictions) > 0
        
        # 验证功率值在合理范围内
        assert predictions['power'].between(0, mock_sta_params.staCap).all()
        
        # 验证辐射值在合理范围内
        assert predictions['radi'].between(0, 1200).all()
    
    def test_baseline_model_train(self, mock_sta_params, mock_logger, mock_data_loader):
        """测试基线模型的训练功能"""
        # 导入基线模型
        from src.modelset.UST.baseline import last as BaselineModel
        
        # 准备测试数据
        X = {"test": "data"}
        Y = {"test": "labels"}
        task_dates = [TEST_DATETIME - timedelta(days=i) for i in range(3)]
        
        # 创建模型实例
        model = BaselineModel(mock_sta_params, logger=mock_logger)
        
        # 训练模型
        trained_model = model.train(
            X=X,
            Y=Y,
            taskDateList=task_dates,
            staParam=mock_sta_params,
            patternLogger=mock_logger,
            dataLoader=mock_data_loader
        )
        
        # 验证返回的模型
        assert isinstance(trained_model, dict)
        assert 'fit_radi' in trained_model
        assert 'fit_pw' in trained_model
        assert len(trained_model['fit_radi']) == len(trained_model['fit_pw'])
        
        # 验证功率值在合理范围内
        assert np.all(trained_model['fit_pw'] >= 0)
        assert np.all(trained_model['fit_pw'] <= mock_sta_params.staCap)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-k", "TestBaseModel and test_base_model_implementation"])