"""
Test suite for task.HFC functionality.
"""

import os
import sys
import pytest
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import patch, MagicMock
from enum import Enum

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.task import taskSingleForecast,taskSingleHistryForecast
from src.params import (
    CParamsInit,
    CParamsTask,
    CStaParams,
    CParamsPath
)
from src.message import Cproducer
from src.config.TypeDefine import TaskType, TimeLiness


class AccuracyMetric(Enum):
    rmse = "rmse"

# Test fixtures
@pytest.fixture
def test_params():
    """Fixture providing test parameters."""
    init = CParamsInit()
    init.logLevel = "INFO"
    init.databaseURL = "test_db_url"

    task = CParamsTask()
    task.taskType = TaskType.FC
    task.dateRange = ["2025-04-15 04:00:00Z" , "2025-04-15 05:00:00Z"]
    task.algorithm = {"baseline": ["last"]}
    task.dataset = ["EC_C1D"]
    task.accuracy = ["rmse"]
    task.postProcess = ["dynamicOptimization"]

    sta = CStaParams()
    sta.staId = "1309210200000000"
    sta.staName = "华润分布式光伏"
    sta.staLon = 117.067
    sta.staLat = 38.404
    sta.staAlt = 0
    sta.staCap = 30
    sta.staType = "PV"
    sta.timeLiness = ["UST"]
    sta.algorithm = {"baseline": ["last"]}
    sta.dataset = ["EC_C1D"]
    sta.accuracy = [AccuracyMetric.rmse ]

    path = CParamsPath()
    path.inPath = {
        "root": ["/home/k8user/workspace/python/yz/greenpulse-gen/tests/test/output"],
        "meteo": {
            "business": "Business/{dataSet}/{dataType}/{date}/{staId}.csv",
            "original": "Original/{dataSet}/{dataType}/{date}/{staId}.csv"
        },
        "obs": ""
    }

    # outPath 配置
    path.outPath = {
        "root": ["/home/k8user/workspace/python/yz/greenpulse-gen/tests/test/output"],
        "meteo": "{staID}/meteo/{timeliness}/{year:>04d}/{year:>04d}{month:>02d}{day:>02d}{hour:>02d}/{dataSet}.csv",
        "power": "{staID}/power/{timeliness}/{year:>04d}/{year:>04d}{month:>02d}{day:>02d}/{year:>04d}{month:>02d}{day:>02d}{hour:>02d}{minute:>02d}/{algorithm}.{version}.csv",
        "acc": "{staID}/acc/{timeliness}/{year:>04d}/{year:>04d}{month:>02d}{day:>02d}{hour:>02d}/{algorithm}.{version}.csv",
        "log": "{staID}/log/{timeliness}/{year:>04d}{month:>02d}{day:>02d}{hour:>02d}/{algorithm}.{version}.log",
        "model": "{staID}/model/{timeliness}/{algorithm}.{version}/{checkpoint}.pkl",
        "hash": "{staID}/hash/{timeliness}/{algorithm}.{version}/{checkpoint}.hash",
        "key": "{staID}/key/{timeliness}/{algorithm}.{version}/{checkpoint}.key"
    }

    # deployment 配置
    path.deployment = {
        "deployment104": False,
        "deployRoot": ["/test/deploy"],
        "meteo": {
            "PATH": "/test/meteo",
            "FILENAME": "F_NWP_FARM_WHOLE_{duration}H_{yearS:>04d}{monthS:>02d}{dayS:>02d}{hourS:>02d}{minuteS:>02d}_{yearE:>04d}{monthE:>02d}{dayE:>02d}{hourE:>02d}{minuteE:>02d}.csv"
        },
        "power": {
            "PATH": "{staID}/FCST/F_{staType}_FARM_WHOLE/{year:>04d}{month:>02d}",
            "FILENAME": "F_PV_FARM_WHOLE_{duration}H_{yearS:>04d}{monthS:>02d}{dayS:>02d}{hourS:>02d}{minuteS:>02d}_{yearE:>04d}{monthE:>02d}{dayE:>02d}{hourE:>02d}{minuteE:>02d}.csv"
        },
        "acc": {
            "DAY": {
                "PATH": "{staID}/FCST/F_{staType}_ACC_SCORE_DAY/{year:>04d}{month:>02d}",
                "FILENAME": "F_{staType}_ACC_SCORE_DAY_{duration}H_{yearS:>04d}{monthS:>02d}{dayS:>02d}_{yearE:>04d}{monthE:>02d}{dayE:>02d}.csv"
            },
            "MONTH": {
                "PATH": "{staID}/FCST/F_{staType}_ACC_SCORE_MONTH/{year:>04d}{month:>02d}",
                "FILENAME": "F_{staType}_ACC_SCORE_MONTH_{duration}H_{yearS:>04d}{monthS:>02d}_{yearE:>04d}{monthE:>02d}.csv"
            }
        }
    }

    return init, task, sta, path

@pytest.fixture
def test_logger():
    """Fixture providing test logger."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    return logger

@pytest.fixture
def test_message_queue():
    """Fixture providing test message queue producer."""
    producer = Cproducer(["host1:9092"])
    producer.connect = MagicMock()
    producer.send = MagicMock()
    producer.send_log = MagicMock()
    producer.send_acc = MagicMock()
    producer.send_pick_best_algorithm = MagicMock()
    return producer


def generate_mock_weather_data(start_date, end_date, freq='15min'):
    """Generate mock weather data for testing."""
    date_range = pd.date_range(start=start_date, end=end_date, freq=freq)
    return pd.DataFrame({
        'datetime': date_range,
        'temperature': np.random.uniform(0, 30, len(date_range)),
        'humidity': np.random.uniform(20, 90, len(date_range)),
        'wind_speed': np.random.uniform(0, 15, len(date_range)),
        'irradiance': np.random.uniform(0, 1000, len(date_range))
    }).set_index('datetime')

def generate_mock_observation_data(start_date, end_date, freq='15min'):
    """Generate mock observation data for testing."""
    date_range = pd.date_range(start=start_date, end=end_date, freq=freq)
    return pd.DataFrame({
        'datetime': date_range,
        'power': np.random.uniform(0, 5000, len(date_range))
    }).set_index('datetime')


def generate_mock_ST_data(start_date: str, end_date: str, freq: str = '15min',
                         station_id: str = '1309210200000000',
                         timeliness: str = 'UST') :
    date_range = pd.date_range(start=start_date, end=end_date, freq=freq)
    df = pd.DataFrame({
        'time': date_range,
        'power': np.random.uniform(0, 5000, len(date_range)),
        'radi': np.random.uniform(0, 5000, len(date_range)),
        'ghi_pw': np.random.uniform(0, 5000, len(date_range)),
        'poa_pw': np.random.uniform(0, 5000, len(date_range))
    }).set_index('time')

    # Create the nested dictionary structure
    result = {
        station_id: {
            timeliness: {
                'Business': {
                    'data_element': df
                }
            }
        }
    }
    return result


def generate_mock_NWP_data(start_date: str, end_date: str, freq: str = '15min',
                         station_id: str = '1309210200000000',
                         timeliness: str = 'UST') :
    date_range = pd.date_range(start=start_date, end=end_date, freq=freq)
    df = pd.DataFrame({
        'time': date_range,
        'sp': np.random.uniform(0, 5000, len(date_range)),
        'departureTime': start_date,
        'tcc': np.random.uniform(0, 5000, len(date_range)),
        'u100': np.random.uniform(0, 5000, len(date_range))
    }).set_index('time')

    # Create the nested dictionary structure
    result = {
        station_id: {
            timeliness: {
                'Business': {
                    'data_element': df
                }
            }
        }
    }
    return result

def generate_mock_OBS_data(start_date: str, end_date: str, freq: str = '15min',
                         station_id: str = '1309210200000000',
                         timeliness: str = 'UST'):
    time_index = pd.date_range(start=start_date, end=end_date, freq=freq)
    num_points = len(time_index)

    # 生成模拟功率数据（白天有值，夜间为0）
    hours = time_index.hour
    power_values = np.where(
        (hours >= 7) & (hours < 19),  # 白天时段7:00-18:59
        np.random.uniform(0, 100, num_points),  # 白天随机功率值0-100
        0  # 夜间功率为0
    )

    # 添加一些NaN模拟缺失值
    mask = np.random.rand(num_points) < 0.05  # 5%的数据点设为NaN
    power_values[mask] = np.nan

    # 创建功率DataFrame
    power_df = pd.DataFrame(
        data={'power': power_values},
        index=time_index
    )
    power_df.index.name = 'time'  # 设置索引名称

    # 构造返回字典
    return {
        station_id: {
            'time': time_index,  # 返回DatetimeIndex
            'power': power_df  # 返回DataFrame
        }
    }


# Unit Tests
def test_valid_input(test_params, test_logger, test_message_queue):
    """Test with valid input parameters."""
    init, task, sta, path = test_params

    # Mock required dependencies
    with (patch('src.task.dataLoader') as mock_loader, \
         patch('src.task.modelget') as mock_model,\
         patch('src.task.modelLoad') as mock_load,\
         patch('src.task.modelDump') as mock_dump, \
          patch('src.task.pp') as mock_params):

        # Setup mock returns
        mock_loader_instance = MagicMock()
        mock_loader.CDataLoader.return_value = mock_loader_instance

        # 设置 load 方法的返回值
        dq_obs = generate_mock_ST_data(task.dateRange[0], task.dateRange[1])
        nwp_obs = generate_mock_NWP_data(task.dateRange[0], task.dateRange[1])
        mock_loader_instance.FCLoadPoint.return_value = dq_obs
        mock_loader_instance.NWPLoadPoint.return_value = nwp_obs
        mock_loader_instance.OBSLoadPoint.return_value = generate_mock_OBS_data(task.dateRange[0], task.dateRange[1])


        mock_lr_model = MagicMock()
        mock_predict_result = pd.DataFrame({
            'time': pd.date_range(start=task.dateRange[0], end=task.dateRange[1], freq='15min'),
            'power': np.random.uniform(0, 5000,len(pd.date_range(start=task.dateRange[0], end=task.dateRange[1], freq='15min'))),
            'radi': np.random.uniform(0, 5000, len(pd.date_range(start=task.dateRange[0], end=task.dateRange[1], freq='15min')))
        }).set_index('time')
        mock_lr_model.predict.return_value = mock_predict_result
        mock_model.return_value = mock_lr_model

        mock_load.modelLoad.return_value = MagicMock()
        mock_dump.modelDump.return_value = MagicMock()
        mock_params.return_value = MagicMock()


        # Mock model with predict method
        mock_model_instance = MagicMock()
        mock_model_instance.predict.return_value = np.random.rand(672)  # 7 days * 24 hours * 4 (15min intervals)
        mock_model.getModel.return_value = mock_model_instance

        # Call the function
        taskSingleHistryForecast(
            sta.staId,
            init,
            task,
            sta,
            path,
            test_logger,
            test_message_queue
        )
        #
        # # Verify mocks were called
        # assert mock_loader.load.call_count == 2  # Called for weather and observation data
        # mock_model.getModel.assert_called()
        # mock_dump.dump.assert_called()
        # test_message_queue.send.assert_called()

# Integration Tests
# @pytest.mark.integration
# def test_complete_historical_forecast_process(test_params, test_logger, test_message_queue):
#     """Test complete historical forecast process with all components."""
#     init, task, sta, path = test_params
#
#     # Mock all dependencies
#     with patch('src.task.dataLoader') as mock_loader, \
#          patch('src.task.modelget') as mock_model, \
#          patch('src.task.dataDump') as mock_dump, \
#          patch('src.task.accuracy') as mock_accuracy:
#
#         # Setup mock returns
#         weather_data = generate_mock_weather_data(task.dateRange[0], task.dateRange[1])
#         obs_data = generate_mock_observation_data(task.dateRange[0], task.dateRange[1])
#         mock_loader.load.side_effect = [weather_data, obs_data]
#
#         # Mock model with predict method
#         mock_model_instance = MagicMock()
#         mock_model_instance.predict.return_value = np.random.rand(len(weather_data))
#         mock_model.getModel.return_value = mock_model_instance
#
#         # Mock accuracy calculation
#         mock_accuracy.calculate.return_value = {"mae": 0.1, "rmse": 0.15}
#
#         # Call the function
#         taskSingleHistryForecast(
#             sta.staId,
#             init,
#             task,
#             sta,
#             path,
#             test_logger,
#             test_message_queue
#         )
#
#         # Verify model was used for prediction
#         mock_model_instance.predict.assert_called()
#
#         # Verify accuracy was calculated for each metric
#         assert mock_accuracy.calculate.call_count == len(task.accuracy)
#
#         # Verify results were saved
#         mock_dump.dump.assert_called()
#
#         # Verify message was sent
#         test_message_queue.send.assert_called()
#
# @pytest.mark.parametrize("metrics,expected_calls", [
#     (["mae"], 1),
#     (["mae", "rmse"], 2),
#     (["mae", "rmse", "mbe"], 3)
# ])
# def test_historical_forecast_with_different_metrics(test_params, test_logger, test_message_queue, metrics, expected_calls):
#     """Test historical forecast with different accuracy metrics."""
#     init, task, sta, path = test_params
#     task.accuracy = metrics
#
#     with patch('src.task.dataLoader') as mock_loader, \
#          patch('src.task.modelget') as mock_model, \
#          patch('src.task.accuracy') as mock_accuracy, \
#          patch('src.task.dataDump'):
#
#         # Setup mock returns
#         weather_data = generate_mock_weather_data(task.dateRange[0], task.dateRange[1])
#         obs_data = generate_mock_observation_data(task.dateRange[0], task.dateRange[1])
#         mock_loader.load.side_effect = [weather_data, obs_data]
#
#         mock_model.getModel.return_value = MagicMock()
#         mock_accuracy.calculate.return_value = {m: 0.1 for m in metrics}
#
#         # Call the function
#         taskSingleHistryForecast(
#             sta.staId,
#             init,
#             task,
#             sta,
#             path,
#             test_logger,
#             test_message_queue
#         )
#
#         # Verify accuracy was calculated for each metric
#         assert mock_accuracy.calculate.call_count == expected_calls

if __name__ == '__main__':
    pytest.main(["-v", "-s", "-k", "test_task_HFC.py"])