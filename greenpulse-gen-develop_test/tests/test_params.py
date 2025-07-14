#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test suite for params.py module using pytest.

This module contains unit tests for all classes in the params.py module,
including parameter parsing, validation, and management.
"""

import os
import sys
import pytest
import tempfile
import shutil
import yaml
import logging
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.params import (
    CParamsInit,
    CParamsResource,
    CParamsTask,
    CParamsPath,
    CStaParams,
    CParams,
    TaskType,
    Arg
)

# Set up test logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def test_config_path():
    """Fixture to create a temporary test configuration file."""
    test_dir = tempfile.mkdtemp()
    test_config = os.path.join(test_dir, "test_config.yaml")
    
    test_config_data = {
        "init": {
            "logLevel": "DEBUG",
            "messageQueue": True,
            "messageQueueTopic": "test_topic",
            "messageQueueURL": ["kafka:9092"]
        },
        "resource": {
            "CPU": 8,
            "CMEM": 16384,
            "GPU": 1,
            "GMEM": 8192,
            "Node": 1
        },
        "task": {
            "taskID": ["TASK001"],
            "taskType": 1,
            "dateRange": ["2023-01-01", "2023-01-31"],
            "staListFile": "stations.csv",
            "staListType": "area",
            "timeLiness": ["UST", "ST"]
        },
        "path": {
            "inPath": {
                "root": ["/test/input"],
                "meteo": {
                    "business": "{dataSet}/{dataType}/business/{date}/{timeliness}_{staId}.nc",
                    "original": "{dataSet}/{dataType}/original/{date}/{timeliness}_{staId}.nc"
                },
                "obs": "obs/{date}/{timeliness}_{staId}.csv"
            },
            "outPath": {
                "root": "/test/output",
                "model": "models/{algorithm}/{version}/{date}_{staId}.pkl",
                "result": "results/{date}/{timeliness}_{algorithm}_{version}_{staId}.csv"
            }
        }
    }
    
    with open(test_config, 'w') as f:
        yaml.dump(test_config_data, f)
    
    yield test_config
    
    shutil.rmtree(test_dir)

@pytest.fixture
def params_init():
    """Fixture for CParamsInit instance."""
    return CParamsInit()

@pytest.fixture
def params_resource():
    """Fixture for CParamsResource instance."""
    return CParamsResource()

@pytest.fixture
def params_task():
    """Fixture for CParamsTask instance."""
    return CParamsTask()

@pytest.fixture
def params_path():
    """Fixture for CParamsPath instance."""
    return CParamsPath()

@pytest.fixture
def params_full(test_config_path):
    """Fixture for fully configured CParams instance."""
    params = CParams()
    params.paramsParse(test_config_path, logger)
    return params

@pytest.fixture
def test_stations():
    """Fixture providing test station data."""
    return [
        {
            "staId": "S001",
            "staName": "Station 1",
            "staLon": 121.0,
            "staLat": 31.0,
            "staAlt": 100.0,
            "staCap": 5000.0,
            "staType": "solar",
            "timeLiness": ["UST", "ST"],
            "algorithm": {"catboost": ["v1.0"]},
            "dataset": ["EC_IFS"],
            "accuracy": ["mae"],
            "postProcess": ["smoothing"]
        },
        {
            "staId": "S002",
            "staName": "Station 2",
            "staLon": 122.0,
            "staLat": 32.0,
            "staAlt": 200.0,
            "staCap": 10000.0,
            "staType": "wind",
            "timeLiness": ["UST"],
            "algorithm": {"xgboost": ["v1.0"]},
            "dataset": ["GFS"],
            "accuracy": ["rmse"],
            "postProcess": ["normalization"]
        }
    ]

@pytest.fixture
def test_tasks():
    """Fixture providing test task data."""
    return [
        {
            "taskID": "TASK001",
            "taskType": TaskType.FORECAST,
            "dateRange": ["2023-01-01", "2023-01-31"],
            "staListFile": "stations.csv",
            "staListType": "area",
            "timeLiness": ["UST", "ST"],
            "algorithm": {"catboost": ["v1.0"]},
            "dataset": ["EC_IFS"],
            "accuracy": ["mae"],
            "postProcess": ["smoothing"]
        },
        {
            "taskID": "TASK002",
            "taskType": TaskType.OPTIMIZATION,
            "dateRange": ["2023-02-01", "2023-02-28"],
            "staListFile": "stations2.csv",
            "staListType": "point",
            "timeLiness": ["ST"],
            "algorithm": {"xgboost": ["v1.0"]},
            "dataset": ["GFS"],
            "accuracy": ["rmse"],
            "postProcess": ["normalization"]
        }
    ]

@pytest.fixture
def test_config(test_config_path):
    """Fixture providing test configuration data."""
    with open(test_config_path, 'r') as f:
        return yaml.safe_load(f)

def test_params_init_initialization(params_init):
    """Test CParamsInit initialization."""
    assert params_init.logLevel == "INFO"
    assert not params_init.messageQueue
    assert params_init.messageQueueTopic == ""
    assert params_init.messageQueueURL == []
    assert not params_init.ray
    assert params_init.retry == 0
    assert params_init.retryInterval == 0
    assert params_init.runTimeMax == 0
    assert not params_init.database
    assert params_init.databaseURL == ""
    assert params_init.databaseName == ""
    assert params_init.databaseUser == ""
    assert params_init.databasePassword == ""
    assert params_init.databasePort == ""
    assert params_init.dbcursor is None
    assert params_init.dbconn is None

    # Test that all expected attributes exist
    expected_attrs = [
        'logLevel', 'messageQueue', 'messageQueueTopic', 'messageQueueURL',
        'ray', 'retry', 'retryInterval', 'runTimeMax', 'database',
        'databaseURL', 'databaseName', 'databaseUser', 'databasePassword',
        'databasePort', 'dbconn', 'dbcursor'
    ]
    for attr in expected_attrs:
        assert hasattr(params_init, attr), f"Missing attribute: {attr}"

def test_params_init_dict_access(params_init):
    """Test CParamsInit dictionary-style access."""
    # Test reading existing parameters
    assert params_init["logLevel"] == "INFO"
    assert params_init["messageQueue"] is False
    
    # Test setting parameters
    params_init["logLevel"] = "DEBUG"
    assert params_init.logLevel == "DEBUG"
    
    # Test non-existent parameter
    with pytest.raises(KeyError):
        _ = params_init["nonexistent"]
    
    # Test setting non-existent parameter
    with pytest.raises(KeyError):
        params_init["nonexistent"] = "value"

def test_params_init_log_level_validation(params_init):
    """Test log level validation."""
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    for level in valid_levels:
        params_init.logLevel = level
        assert params_init.logLevel == level
    
    # Test invalid log level
    with pytest.raises(ValueError):
        params_init.logLevel = "INVALID_LEVEL"

def test_params_resource_initialization(params_resource):
    """Test CParamsResource initialization."""
    assert params_resource.CPU == 0
    assert params_resource.CMEM == 0
    assert params_resource.GPU == 0
    assert params_resource.GMEM == 0
    assert params_resource.Node == 0
    
    # Test that all expected attributes exist
    expected_attrs = ['CPU', 'CMEM', 'GPU', 'GMEM', 'Node']
    for attr in expected_attrs:
        assert hasattr(params_resource, attr), f"Missing attribute: {attr}"

def test_params_resource_dict_access(params_resource):
    """Test CParamsResource dictionary-style access."""
    # Test reading existing parameters
    assert params_resource["CPU"] == 0
    assert params_resource["GPU"] == 0
    
    # Test setting parameters
    params_resource["CPU"] = 4
    assert params_resource.CPU == 4
    
    # Test non-existent parameter
    with pytest.raises(KeyError):
        _ = params_resource["nonexistent"]
    
    # Test setting non-existent parameter
    with pytest.raises(KeyError):
        params_resource["nonexistent"] = 1

def test_params_task_initialization(params_task):
    """Test CParamsTask initialization."""
    assert params_task.taskID is None
    assert params_task.taskType == 0
    assert params_task.dateRange == [None, None]
    assert params_task.staListFile is None
    assert params_task.staListType == ""
    assert params_task.timeLiness == []
    assert params_task.algorithm == {}
    assert params_task.dataset == []
    assert params_task.accuracy == []
    assert params_task.postProcess == []
    
    # Test that all expected attributes exist
    expected_attrs = [
        'taskID', 'taskType', 'dateRange', 'staListFile', 'staListType',
        'timeLiness', 'algorithm', 'dataset', 'accuracy', 'postProcess'
    ]
    for attr in expected_attrs:
        assert hasattr(params_task, attr), f"Missing attribute: {attr}"

def test_params_task_task_type_enum(params_task):
    """Test task type enum handling."""
    # Test all enum values
    for task_type in TaskType:
        params_task.taskType = task_type
        assert params_task.taskType == task_type
        assert int(params_task.taskType) == task_type.value
    
    # Test integer assignment
    params_task.taskType = 1
    assert params_task.taskType == TaskType.FORECAST
    
    # Test invalid task type
    with pytest.raises(ValueError):
        params_task.taskType = 999

def test_params_task_date_range_validation(params_task):
    """Test date range validation."""
    # Test valid date range
    valid_dates = ["2023-01-01", "2023-12-31"]
    params_task.dateRange = valid_dates
    assert params_task.dateRange == valid_dates
    
    # Test single date
    params_task.dateRange = ["2023-01-01"]
    assert params_task.dateRange == ["2023-01-01", None]
    
    # Test invalid date format
    with pytest.raises(ValueError):
        params_task.dateRange = ["2023/01/01", "2023/12/31"]

def test_params_task_algorithm_management(params_task):
    """Test algorithm management."""
    # Test adding algorithms
    params_task.algorithm = {"xgboost": ["1.0.0"], "lightgbm": ["3.0.0"]}
    assert len(params_task.algorithm) == 2
    assert "xgboost" in params_task.algorithm
    assert "lightgbm" in params_task.algorithm
    
    # Test getting algorithm versions
    assert params_task.algorithm["xgboost"] == ["1.0.0"]

def test_params_path_initialization(params_path):
    """Test CParamsPath initialization."""
    assert params_path.inPath == {}
    assert params_path.outPath == {}
    assert params_path.deployment == {}

def test_params_path_load_from_config(test_config_path, params_path):
    """Test loading path configuration from YAML file."""
    with open(test_config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    params_path.inPath = config['path']['inPath']
    params_path.outPath = config['path']['outPath']
    params_path.deployment = config['path']['deployment']
    
    assert params_path.inPath['root'] == ['/test/input']
    assert params_path.outPath['root'] == '/test/output'
    assert params_path.deployment['deployRoot'] == ['/test/deploy']

def test_params_full_initialization(params_full):
    """Test full CParams initialization."""
    assert isinstance(params_full.init, CParamsInit)
    assert isinstance(params_full.res, CParamsResource)
    assert isinstance(params_full.task, CParamsTask)
    assert isinstance(params_full.path, CParamsPath)
    assert isinstance(params_full.staParams, dict)
    assert len(params_full.staParams) == 0

def test_params_full_params_parse(params_full):
    """Test parameter parsing from config file."""
    assert params_full.init.logLevel == "DEBUG"
    assert params_full.init.messageQueue is True
    assert params_full.res.CPU == 8
    assert params_full.res.CMEM == 16384
    assert params_full.task.taskID == ["TASK001"]
    assert params_full.task.taskType == TaskType.FORECAST
    assert params_full.task.dateRange == ["2023-01-01", "2023-01-31"]
    assert params_full.task.staListFile == "stations.csv"
    assert params_full.task.staListType == "area"
    assert params_full.task.timeLiness == ["UST", "ST"]

def test_params_full_add_station_from_config(params_full):
    """Test adding station from config."""
    params_full.addStaFromConfig(
        staId="S001",
        staTaskId="TASK001_S001",
        staType="solar",
        staName="Test Solar Station",
        staLon=121.0,
        staLat=31.0,
        staAlt=100.0,
        staCap=5000.0,
        timeLiness=["UST", "ST"],
        algorithm={"catboost": ["v1.0"]},
        dataset=["EC_IFS"],
        accuracy=["mae"],
        postProcess=["smoothing"]
    )
    
    assert "TASK001_S001" in params_full.staParams
    station = params_full.staParams["TASK001_S001"]
    assert station.staId == "S001"
    assert station.staName == "Test Solar Station"
    assert station.staType == "solar"
    assert station.algorithm == {"catboost": ["v1.0"]}

def test_params_full_clean(params_full):
    """Test cleaning up resources."""
    # Mock database connection
    params_full.init.dbconn = MagicMock()
    params_full.init.dbcursor = MagicMock()
    
    # Add some station parameters
    params_full.staParams["S001"] = CStaParams()
    
    # Clean up
    params_full.clean(logger)
    
    # Verify database connection was closed
    assert params_full.init.dbconn is None
    assert params_full.init.dbcursor is None
    
    # Verify station parameters were cleared
    assert len(params_full.staParams) == 0

@pytest.mark.integration
def test_params_full_integration(params_full, test_stations, test_tasks):
    """Test full integration of parameter management."""
    # Add multiple stations
    for station_data in test_stations:
        params_full.addStaFromConfig(
            staId=station_data["staId"],
            staTaskId=f"{station_data["staId"]}_TASK",
            staType=station_data["staType"],
            staName=station_data["staName"],
            staLon=station_data["staLon"],
            staLat=station_data["staLat"],
            staAlt=station_data["staAlt"],
            staCap=station_data["staCap"],
            timeLiness=station_data["timeLiness"],
            algorithm=station_data["algorithm"],
            dataset=station_data["dataset"],
            accuracy=station_data["accuracy"],
            postProcess=station_data["postProcess"]
        )
    
    # Verify stations were added
    assert len(params_full.staParams) == len(test_stations)
    
    # Add multiple tasks
    for task_data in test_tasks:
        params_full.task.taskID = task_data["taskID"]
        params_full.task.taskType = task_data["taskType"]
        params_full.task.dateRange = task_data["dateRange"]
        params_full.task.staListFile = task_data["staListFile"]
        params_full.task.staListType = task_data["staListType"]
        params_full.task.timeLiness = task_data["timeLiness"]
        params_full.task.algorithm = task_data["algorithm"]
        params_full.task.dataset = task_data["dataset"]
        params_full.task.accuracy = task_data["accuracy"]
        params_full.task.postProcess = task_data["postProcess"]
    
    # Verify tasks were added
    assert len(params_full.task.taskID) == len(test_tasks)
    
    # Test parameter validation
    for task_id in params_full.task.taskID:
        assert task_id.startswith("TASK")
        assert params_full.task.dateRange[0] <= params_full.task.dateRange[1]
        assert params_full.task.staListType in ["area", "point"]
        assert all(tl in ["UST", "ST"] for tl in params_full.task.timeLiness)
        assert all(alg in params_full.task.algorithm for alg in ["catboost", "xgboost"])
        assert all(ds in params_full.task.dataset for ds in ["EC_IFS", "GFS"])
        assert all(acc in params_full.task.accuracy for acc in ["mae", "rmse"])
        assert all(pp in params_full.task.postProcess for pp in ["smoothing", "normalization"])

@pytest.mark.integration
def test_params_full_database_integration(params_full, test_config):
    """Test database integration with parameter management."""
    # Setup database connection
    params_full.init.database = True
    params_full.init.databaseURL = "localhost"
    params_full.init.databaseName = "test_db"
    params_full.init.databaseUser = "test_user"
    params_full.init.databasePassword = "test_pass"
    params_full.init.databasePort = "5432"

    # Mock database cursor
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("S001", "Station 1", 121.0, 31.0, 100.0, 5000.0, "solar"),
        ("S002", "Station 2", 122.0, 32.0, 200.0, 10000.0, "wind")
    ]
    
    # Mock database connection
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    with patch('psycopg2.connect', return_value=mock_conn):
        # Add stations from database
        params_full.addStaFromDB(logger)
        
        # Verify database connection
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        
        # Verify stations were added
        assert len(params_full.staParams) == 2
        
        # Verify station data
        for station_id, station in params_full.staParams.items():
            assert station.staId in ["S001", "S002"]
            assert station.staType in ["solar", "wind"]
            assert 120.0 <= station.staLon <= 123.0
            assert 30.0 <= station.staLat <= 33.0
            assert 99.0 <= station.staAlt <= 201.0
            assert 4999.0 <= station.staCap <= 10001.0

@pytest.mark.integration
def test_params_full_path_integration(params_full, test_config_path):
    """Test path configuration integration."""
    # Load paths from config
    with open(test_config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Set paths
    params_full.path.inPath = config['path']['inPath']
    params_full.path.outPath = config['path']['outPath']
    params_full.path.deployment = config['path']['deployment']
    
    # Test path generation
    test_data = {
        'algorithm': 'catboost',
        'version': 'v1.0',
        'date': '2023-01-01',
        'staId': 'S001',
        'timeliness': 'UST'
    }
    
    # Test input path
    input_path = params_full.path.inPath['root'][0]
    meteo_path = params_full.path.inPath['meteo']['business'].format(**test_data)
    assert meteo_path == "EC_IFS/business/2023-01-01/UST_S001.nc"
    
    # Test output path
    output_path = params_full.path.outPath['root']
    model_path = params_full.path.outPath['model'].format(**test_data)
    assert model_path == "models/catboost/v1.0/2023-01-01_S001.pkl"
    
    # Test deployment path
    deploy_root = params_full.path.deployment['deployRoot'][0]
    meteo_deploy = params_full.path.deployment['meteo']
    assert meteo_deploy['PATH'] == "meteo"
    assert meteo_deploy['FILENAME'] == "output_meteo.csv"

@pytest.mark.integration
def test_params_full_task_validation(params_full):
    """Test task parameter validation."""
    # Test invalid task type
    with pytest.raises(ValueError):
        params_full.task.taskType = 999
    
    # Test invalid date range
    with pytest.raises(ValueError):
        params_full.task.dateRange = ["2023/01/01", "2023/01/31"]
    
    # Test invalid timeLiness
    with pytest.raises(ValueError):
        params_full.task.timeLiness = ["INVALID"]
    
    # Test invalid algorithm
    with pytest.raises(ValueError):
        params_full.task.algorithm = {"invalid": ["v1.0"]}
    
    # Test invalid dataset
    with pytest.raises(ValueError):
        params_full.task.dataset = ["INVALID"]
    
    # Test invalid accuracy
    with pytest.raises(ValueError):
        params_full.task.accuracy = ["INVALID"]
    
    # Test invalid postProcess
    with pytest.raises(ValueError):
        params_full.task.postProcess = ["INVALID"]

@pytest.mark.performance
@pytest.mark.parametrize("num_stations", [1, 10, 100, 1000])
def test_params_performance(params_full, num_stations):
    """测试参数管理的性能"""
    import time
    
    # 生成测试数据
    stations = []
    for i in range(num_stations):
        station = {
            "staId": f"S{i:04d}",
            "staName": f"Station {i}",
            "staLon": 120.0 + (i % 10) * 0.1,
            "staLat": 30.0 + (i % 10) * 0.1,
            "staAlt": 100 + (i % 10) * 10,
            "staCap": 5000 + (i % 10) * 1000,
            "staType": "solar" if i % 2 == 0 else "wind",
            "timeLiness": ["UST", "ST"] if i % 2 == 0 else ["UST"],
            "algorithm": {"catboost": ["v1.0"]},
            "dataset": ["EC_IFS"],
            "accuracy": ["mae"],
            "postProcess": ["smoothing"]
        }
        stations.append(station)
    
    # 测试添加性能
    start_time = time.time()
    for station in stations:
        params_full.addStaFromConfig(
            staId=station["staId"],
            staTaskId=f"TASK_{station["staId"]}",
            **station
        )
    add_time = time.time() - start_time
    
    # 测试查询性能
    start_time = time.time()
    for _ in range(100):
        _ = params_full.staParams[stations[0]["staId"]]
    query_time = time.time() - start_time
    
    # 打印性能指标
    print(f"\n性能测试结果 (stations={num_stations}):")
    print(f"添加 {num_stations} 个站点耗时: {add_time:.2f} 秒")
    print(f"查询 100 次耗时: {query_time:.2f} 秒")
    print(f"平均查询耗时: {query_time/100:.6f} 秒")

@pytest.mark.config
@pytest.mark.parametrize("invalid_config", [
    {"init": {"logLevel": "INVALID"}},
    {"resource": {"CPU": -1}},
    {"task": {"dateRange": ["2023-01-01", "2022-12-31"]}},
    {"path": {"inPath": {"root": ["invalid_path"]}}},
    {"task": {"algorithm": {"invalid": ["v1.0"]}}}
])
def test_invalid_config(params_full, invalid_config, test_config_path):
    """测试无效配置文件的处理"""
    # 加载原始配置
    with open(test_config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # 添加无效配置
    for key, value in invalid_config.items():
        config[key] = value
    
    # 保存修改后的配置
    with open(test_config_path, 'w') as f:
        yaml.dump(config, f)
    
    # 测试配置加载
    with pytest.raises(ValueError):
        params_full.paramsParse(test_config_path, logger)

@pytest.mark.exception
@pytest.mark.parametrize("exception_case", [
    ("database", "invalid_host", "ConnectionError"),
    ("file", "invalid_path", "FileNotFoundError"),
    ("yaml", "invalid_yaml", "yaml.YAMLError")
])
def test_exception_handling(params_full, exception_case):
    """测试异常处理"""
    error_type, error_value, expected_exception = exception_case
    
    if error_type == "database":
        # 测试数据库连接异常
        params_full.init.databaseURL = error_value
        with pytest.raises(Exception) as excinfo:
            params_full.addStaFromDB(logger)
        assert expected_exception in str(excinfo.value)
    
    elif error_type == "file":
        # 测试文件操作异常
        invalid_path = error_value
        with pytest.raises(Exception) as excinfo:
            params_full.path.inPath = {"root": [invalid_path]}
        assert expected_exception in str(excinfo.value)
    
    elif error_type == "yaml":
        # 测试无效 YAML 配置
        invalid_yaml = error_value
        with pytest.raises(Exception) as excinfo:
            yaml.safe_load(invalid_yaml)
        assert expected_exception in str(excinfo.value)

@pytest.mark.combination
@pytest.mark.parametrize("combination", [
    ("solar", "EC_IFS", "catboost", "mae", "smoothing"),
    ("wind", "GFS", "xgboost", "rmse", "normalization"),
    ("solar", "GFS", "xgboost", "mae", "normalization"),
    ("wind", "EC_IFS", "catboost", "rmse", "smoothing")
])
def test_parameter_combinations(params_full, combination):
    """测试参数组合"""
    staType, dataset, algorithm, accuracy, postProcess = combination
    
    # 添加站点
    params_full.addStaFromConfig(
        staId="S001",
        staTaskId="TASK001",
        staType=staType,
        dataset=[dataset],
        algorithm={algorithm: ["v1.0"]},
        accuracy=[accuracy],
        postProcess=[postProcess]
    )
    
    # 验证组合是否有效
    station = params_full.staParams["TASK001"]
    assert station.staType == staType
    assert station.dataset[0] == dataset
    assert list(station.algorithm.keys())[0] == algorithm
    assert station.accuracy[0] == accuracy
    assert station.postProcess[0] == postProcess

@pytest.mark.cleanup
@pytest.mark.parametrize("cleanup_type", ["database", "files", "memory"])
def test_cleanup(params_full, cleanup_type):
    """测试清理功能"""
    # 设置测试数据
    params_full.init.dbconn = MagicMock()
    params_full.init.dbcursor = MagicMock()
    params_full.staParams["S001"] = CStaParams()
    
    # 执行清理
    params_full.clean(logger)
    
    # 验证清理结果
    assert params_full.init.dbconn is None
    assert params_full.init.dbcursor is None
    assert len(params_full.staParams) == 0
    
    # 验证日志记录
    with patch.object(logger, 'info') as mock_info:
        params_full.clean(logger)
        mock_info.assert_called()

if __name__ == '__main__':
    pytest.main([__file__])
