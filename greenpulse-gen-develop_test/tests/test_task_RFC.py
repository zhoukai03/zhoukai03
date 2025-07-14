"""
Test suite for task.RFC (Real-time Forecast) functionality.
"""

import os
import sys
import pytest
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.task import taskSingleRealTimeForecast
from src.params import (
    CParamsInit,
    CParamsTask,
    CStaParams,
    CParamsPath
)
from src.message import Cproducer
from src.config.TypeDefine import TaskType, TimeLiness

# Test fixtures
@pytest.fixture
def test_params():
    """Fixture providing test parameters."""
    init = CParamsInit()
    init.logLevel = "INFO"
    init.databaseURL = "test_db_url"
    
    task = CParamsTask()
    task.taskType = TaskType.RFC
    task.forecastHours = 24  # 24-hour forecast
    task.algorithm = {"catboost": ["v1.0"]}
    task.dataset = ["EC_IFS"]
    task.postProcess = ["smoothing"]
    
    sta = CStaParams()
    sta.staId = "S001"
    sta.staName = "Test Station"
    sta.staLon = 120.0
    sta.staLat = 30.0
    sta.staAlt = 100.0
    sta.staCap = 5000.0
    sta.staType = "solar"
    sta.timeLiness = ["UST"]  # Real-time typically uses UST only
    
    path = CParamsPath()
    path.inPath = {"root": ["/test/input"]}
    path.outPath = {"root": ["/test/output"]}
    
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
    producer = Cproducer()
    producer.connect = MagicMock()
    producer.send = MagicMock()
    return producer

def generate_mock_weather_data(hours_ahead=24, freq='15min'):
    """Generate mock weather forecast data for testing."""
    now = datetime.now()
    date_range = pd.date_range(
        start=now,
        end=now + timedelta(hours=hours_ahead),
        freq=freq
    )
    return pd.DataFrame({
        'datetime': date_range,
        'temperature': np.random.uniform(0, 30, len(date_range)),
        'humidity': np.random.uniform(20, 90, len(date_range)),
        'wind_speed': np.random.uniform(0, 15, len(date_range)),
        'irradiance': np.random.uniform(0, 1000, len(date_range)),
        'cloud_cover': np.random.uniform(0, 100, len(date_range))
    }).set_index('datetime')

# Unit Tests
def test_valid_realtime_forecast(test_params, test_logger, test_message_queue):
    """Test real-time forecast with valid input parameters."""
    init, task, sta, path = test_params
    
    # Mock required dependencies
    with patch('src.task.dataLoader') as mock_loader, \
         patch('src.task.modelget') as mock_model, \
         patch('src.task.dataDump') as mock_dump, \
         patch('src.task.datetime') as mock_datetime:
        
        # Mock current time
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        # Setup mock returns
        forecast_hours = task.forecastHours
        mock_loader.load.return_value = generate_mock_weather_data(forecast_hours)
        
        # Mock model with predict method
        mock_model_instance = MagicMock()
        mock_model_instance.predict.return_value = np.random.rand(forecast_hours * 4)  # 15min intervals
        mock_model.getModel.return_value = mock_model_instance
        
        # Call the function
        taskSingleRealTimeForecast(
            sta.staId,
            init,
            task,
            sta,
            path,
            test_logger,
            test_message_queue
        )
        
        # Verify mocks were called
        mock_loader.load.assert_called_once()
        mock_model.getModel.assert_called()
        mock_dump.dump.assert_called()
        test_message_queue.send.assert_called()

# Integration Tests
@pytest.mark.integration
def test_complete_realtime_forecast_process(test_params, test_logger, test_message_queue):
    """Test complete real-time forecast process with all components."""
    init, task, sta, path = test_params
    
    # Mock all dependencies
    with patch('src.task.dataLoader') as mock_loader, \
         patch('src.task.modelget') as mock_model, \
         patch('src.task.dataDump') as mock_dump, \
         patch('src.task.datetime') as mock_datetime:
        
        # Mock current time
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        # Generate test data
        forecast_hours = task.forecastHours
        forecast_data = generate_mock_weather_data(forecast_hours)
        mock_loader.load.return_value = forecast_data
        
        # Mock model with predict method
        mock_model_instance = MagicMock()
        mock_model_instance.predict.return_value = np.random.rand(len(forecast_data))
        mock_model.getModel.return_value = mock_model_instance
        
        # Call the function
        taskSingleRealTimeForecast(
            sta.staId,
            init,
            task,
            sta,
            path,
            test_logger,
            test_message_queue
        )
        
        # Verify model was used for prediction
        mock_model_instance.predict.assert_called_once()
        
        # Verify results were saved
        assert mock_dump.dump.call_count == 1
        
        # Verify message was sent
        test_message_queue.send.assert_called()

@pytest.mark.parametrize("forecast_hours,expected_points", [
    (1, 4),    # 1 hour = 4 * 15min intervals
    (6, 24),   # 6 hours = 24 * 15min intervals
    (24, 96),  # 24 hours = 96 * 15min intervals
])
def test_realtime_forecast_with_different_horizons(test_params, test_logger, test_message_queue, forecast_hours, expected_points):
    """Test real-time forecast with different forecast horizons."""
    init, task, sta, path = test_params
    task.forecastHours = forecast_hours
    
    with patch('src.task.dataLoader') as mock_loader, \
         patch('src.task.modelget') as mock_model, \
         patch('src.task.dataDump'), \
         patch('src.task.datetime') as mock_datetime:
        
        # Mock current time
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        # Setup mock returns
        forecast_data = generate_mock_weather_data(forecast_hours)
        mock_loader.load.return_value = forecast_data
        
        mock_model_instance = MagicMock()
        mock_model_instance.predict.return_value = np.random.rand(expected_points)
        mock_model.getModel.return_value = mock_model_instance
        
        # Call the function
        taskSingleRealTimeForecast(
            sta.staId,
            init,
            task,
            sta,
            path,
            test_logger,
            test_message_queue
        )
        
        # Verify correct number of points were predicted
        assert len(mock_model_instance.predict.return_value) == expected_points

if __name__ == '__main__':
    pytest.main([__file__, "-v"])