"""
Test suite for task.FT (Full Training) functionality.
"""

import os
import sys
import pytest
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.task import taskSingleTrain
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
    task.taskType = TaskType.FT
    task.dateRange = ["2023-01-01", "2023-01-31"]  # One month of training data
    task.algorithm = {"catboost": ["v1.0"]}
    task.dataset = ["EC_IFS"]
    task.accuracy = ["mae"]
    task.postProcess = ["smoothing"]
    
    sta = CStaParams()
    sta.staId = "S001"
    sta.staName = "Test Station"
    sta.staLon = 120.0
    sta.staLat = 30.0
    sta.staAlt = 100.0
    sta.staCap = 5000.0
    sta.staType = "solar"
    sta.timeLiness = ["UST", "ST"]
    
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

# Unit Tests
def test_valid_training_input(test_params, test_logger, test_message_queue):
    """Test training with valid input parameters."""
    init, task, sta, path = test_params
    checkpoint = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Mock required dependencies
    with patch('src.task.dataLoader') as mock_loader, \
         patch('src.task.modelget') as mock_model, \
         patch('src.task.modelDump') as mock_dump:
        
        # Setup mock returns
        mock_loader.load.side_effect = [
            generate_mock_weather_data(task.dateRange[0], task.dateRange[1]),  # Weather data
            generate_mock_observation_data(task.dateRange[0], task.dateRange[1])  # Observation data
        ]
        
        mock_model.getModel.return_value = MagicMock()
        mock_dump.dump.return_value = None
        
        # Call the function
        taskSingleTrain(
            sta.staId,
            checkpoint,
            init,
            task,
            sta,
            path,
            test_logger,
            test_message_queue
        )
        
        # Verify mocks were called
        assert mock_loader.load.call_count == 2  # Called for weather and observation data
        mock_model.getModel.assert_called()
        mock_dump.dump.assert_called()
        test_message_queue.send.assert_called()

# Integration Tests
@pytest.mark.integration
def test_complete_training_process(test_params, test_logger, test_message_queue):
    """Test complete training process with all components."""
    init, task, sta, path = test_params
    checkpoint = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Mock all dependencies
    with patch('src.task.dataLoader') as mock_loader, \
         patch('src.task.modelget') as mock_model, \
         patch('src.task.modelDump') as mock_dump:
        
        # Setup mock returns
        mock_loader.load.side_effect = [
            generate_mock_weather_data(task.dateRange[0], task.dateRange[1]),  # Weather data
            generate_mock_observation_data(task.dateRange[0], task.dateRange[1])  # Observation data
        ]
        
        # Create a mock model with fit method
        mock_model_instance = MagicMock()
        mock_model.getModel.return_value = mock_model_instance
        
        # Call the function
        taskSingleTrain(
            sta.staId,
            checkpoint,
            init,
            task,
            sta,
            path,
            test_logger,
            test_message_queue
        )
        
        # Verify model was trained
        mock_model_instance.fit.assert_called()
        
        # Verify model was saved
        mock_dump.dump.assert_called()
        
        # Verify message was sent
        test_message_queue.send.assert_called()

@pytest.mark.parametrize("timeliness,expected_calls", [
    (["UST"], 1),
    (["UST", "ST"], 2),
    (["UST", "ST", "MT", "LT"], 4)
])
def test_training_with_different_timeliness(test_params, test_logger, test_message_queue, timeliness, expected_calls):
    """Test training with different time scales."""
    init, task, sta, path = test_params
    sta.timeLiness = timeliness
    checkpoint = datetime.now().strftime("%Y%m%d%H%M%S")
    
    with patch('src.task.dataLoader') as mock_loader, \
         patch('src.task.modelget') as mock_model, \
         patch('src.task.modelDump'):
        
        # Setup mock returns
        mock_loader.load.side_effect = [
            generate_mock_weather_data(task.dateRange[0], task.dateRange[1]),  # Weather data
            generate_mock_observation_data(task.dateRange[0], task.dateRange[1])  # Observation data
        ]
        
        mock_model.getModel.return_value = MagicMock()
        
        # Call the function
        taskSingleTrain(
            sta.staId,
            checkpoint,
            init,
            task,
            sta,
            path,
            test_logger,
            test_message_queue
        )
        
        # Verify model was created for each time scale
        assert mock_model.getModel.call_count == expected_calls

if __name__ == '__main__':
    pytest.main([__file__, "-v"])