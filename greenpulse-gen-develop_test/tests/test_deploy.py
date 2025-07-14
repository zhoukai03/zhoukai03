"""
测试 deploy.py 模块的单元测试和集成测试
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch, mock_open, call
from datetime import datetime, timedelta
from pathlib import Path

from sympy.codegen.cfunctions import isnan

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入被测试模块
from src import deploy
from src import message as mq
from src import params as pp

# 测试用的固定时间戳
TEST_DATETIME = pd.Timestamp('2023-05-01 12:00:00', tz='UTC')
TEST_DATETIME2 = pd.Timestamp('2023-05-11 11:45:00', tz='UTC')

# 测试用的站点ID
TEST_STA_ID = '1000000000000001'
TEST_STA_TYPE= 'PV'

# 测试用的时效类型
TEST_TIMELINESS = 'ST'
if TEST_TIMELINESS == 'UST':
    END_DATETIME = TEST_DATETIME + timedelta(hours=3,minutes=45)
elif TEST_TIMELINESS == 'ST':
    END_DATETIME = TEST_DATETIME + timedelta(days=2,hours=23, minutes=45)
elif TEST_TIMELINESS == 'MT':
    END_DATETIME = TEST_DATETIME + timedelta(days=9, hours=23, minutes=45)

# 测试用的算法和版本
TEST_ALGORITHM = 'test_algorithm'
TEST_VERSION = 'v1'

# 测试用的文件路径
TEST_OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_output'))
TEST_DEPLOY_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_deploy'))

@pytest.fixture
def setup_dirs():
    """创建和清理测试目录"""
    # 创建测试目录
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEST_DEPLOY_DIR, exist_ok=True)
    
    yield  # 测试运行
    
    # 清理测试目录
    # for dir_path in [TEST_OUTPUT_DIR, TEST_DEPLOY_DIR]:
    #     for root, dirs, files in os.walk(dir_path, topdown=False):
    #         for name in files:
    #             os.remove(os.path.join(root, name))
    #         for name in dirs:
    #             os.rmdir(os.path.join(root, name))
    #     os.rmdir(dir_path)

@pytest.fixture
def mock_logger():
    """创建一个模拟的日志记录器"""
    logger = MagicMock()

    return logger

@pytest.fixture
def mock_message_queue_producer():
    """创建一个模拟的消息队列生产者"""
    return MagicMock(spec=mq.CNullKafkaProducer)

@pytest.fixture
def sample_meteo_data():
    """生成测试用的气象数据"""
    p = 96 * 13 +1
    index = pd.date_range(start=TEST_DATETIME, periods= p, freq='15min',tz='UTC')
    data = {
        'time': index,
        'departureTime': [TEST_DATETIME] * p,
        'sp': np.random.uniform(980, 1020, p),  # 气压
        'tcc': np.random.uniform(0, 1, p),      # 云量
        'win10_spd': np.random.uniform(0, 20, p),  # 10米风速
        'win10_dir': np.random.uniform(0, 360, p),  # 10米风向
        'rhu': np.random.uniform(20, 100, p),      # 相对湿度
        't2': np.random.uniform(10, 30, p),        # 2米温度
        'tp': np.random.uniform(0, 10, p),          # 总降水
        'ghi': np.random.uniform(0, 1000, p),       # 全球水平辐照度
        'dni': np.random.uniform(0, 1000, p),       # 直接法向辐照度
        'dhi': np.random.uniform(0, 500, p)         # 散射水平辐照度
    }
    return pd.DataFrame(data, index=index)

@pytest.fixture
def sample_power_data():
    """生成测试用的功率数据，并将7点-19点以外的时间段值设为0"""
    p = 96 * 3
    index = pd.date_range(start=TEST_DATETIME, periods=p, freq='15min', tz='UTC')

    # 生成随机数据
    data = {
        'time': index,
        'power': np.random.uniform(0, 100, p),
        'radi': np.random.uniform(0, 1400, p),
        'ghi_pw': np.random.uniform(0, 100, p),
        'poa_pw': np.random.uniform(0, 100, p),
    }
    df = pd.DataFrame(data, index=index)

    # 获取小时数（UTC时间）
    hours = df.index.hour

    # 将7点-19点以外的时间段数据设为0
    mask = (hours >= 12)  # 条件：不在7:00-18:59范围内
    df.loc[mask, ['power', 'radi', 'ghi_pw', 'poa_pw']] = 0

    return df

def create_test_files(directory, filename, content=None):
    """创建测试文件"""
    filepath = os.path.join(directory, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if content is not None:
        content.to_csv(filepath, index=True if hasattr(content, 'index') else False)
    else:
        with open(filepath, 'w') as f:
            f.write("test content")
    return filepath

class TestDeployMeteo:
    """测试 deployMeteo 函数"""
    
    def test_deploy_meteo_success(self, setup_dirs, mock_logger, mock_message_queue_producer, sample_meteo_data):
        """测试气象数据部署成功的情况"""
        # 准备测试数据
        output_filename = f"meteo_{TEST_DATETIME.strftime('%Y%m%d%H%M')}_{TEST_DATETIME2.strftime('%Y%m%d%H%M')}.csv"
        output_path = os.path.join(TEST_OUTPUT_DIR, output_filename)
        deploy_path = os.path.join(TEST_DEPLOY_DIR, output_filename)
        
        # 保存测试数据到输出目录
        sample_meteo_data.to_csv(output_path)
        mock_message_queue_producer.send_meteo=MagicMock()

        # 调用被测试函数
        deploy.deployMeteo(
            staTaskId=TEST_STA_ID,
            staType= TEST_STA_TYPE,
            timeliness=TEST_TIMELINESS,
            outputPaths={'meteo': [output_path]},
            deployPaths={'meteo': [deploy_path]},
            logger=mock_logger,
            messageQueueProducer=mock_message_queue_producer
        )
        
        # 验证输出文件是否存在
        assert os.path.exists(deploy_path)

        # 验证文件名是否符合规范
        filename = os.path.basename(deploy_path)
        parts = filename.split('_')
        start_str = parts[-2]
        end_str = parts[-1].replace('.csv', '')
        start_time = datetime.strptime(start_str, "%Y%m%d%H%M")
        end_time = datetime.strptime(end_str, "%Y%m%d%H%M")
        assert end_time - start_time == timedelta(days=9,hours=23, minutes=45)

        #验证输出文件是否符合规范(包括文件名是否规范、数据内容是否规范)
        df = pd.read_csv(deploy_path, parse_dates=['time'])

        # 要素预报时长要求为13天，应对数据缺失情况，与文件名不同！
        time_diff = df['time'].max() - df['time'].min()
        assert time_diff == timedelta(days=12, hours=23, minutes=45)
        # 各项要素需求，按要求修改
        for index, row in df.iterrows():
            assert isinstance(row['time'], pd.Timestamp)
            assert 0 <= row['cloud'] <= 100
            assert 0 <= row['pre'] <= 100
            assert 0 <= row['wind_spd_10'] <= 120
            assert 0 <= row['wind_dir_10'] <= 360
            assert 0 <= row['hum'] <= 100
            assert not np.isnan(row['pressure'])
            assert -40 <= row['tem'] <= 60
            assert not np.isnan(row['radi'])
            assert not np.isnan(row['dni'])
            assert not np.isnan(row['dhi'])


        # 验证日志记录
        mock_logger.info.assert_called()
        
        # 验证消息队列调用
        assert mock_message_queue_producer.send_meteo.called
    

class TestDeployPower:
    """测试 deployPower 函数"""
    
    def test_deploy_power_success(self, setup_dirs, mock_logger, mock_message_queue_producer, sample_power_data):
        """测试功率数据部署成功的情况"""
        # 准备测试数据
        output_filename = f"power_{TEST_DATETIME.strftime('%Y%m%d%H%M')}_{END_DATETIME.strftime('%Y%m%d%H%M')}.csv"
        output_path = os.path.join(TEST_OUTPUT_DIR, output_filename)
        deploy_path = os.path.join(TEST_DEPLOY_DIR, output_filename)
        
        # 保存测试数据到输出目录
        sample_power_data.to_csv(output_path)
        mock_message_queue_producer.send_power=MagicMock()
        
        # 调用被测试函数
        deploy.deployPower(
            staTaskId=TEST_STA_ID,
            staType=TEST_STA_TYPE,
            taskDate=TEST_DATETIME,
            timeliness=TEST_TIMELINESS,
            outputPaths={'power': [output_path]},
            deployPaths={'power': [deploy_path]},
            logger=mock_logger,
            messageQueueProducer=mock_message_queue_producer
        )
        
        # 验证输出文件是否存在
        assert os.path.exists(deploy_path)

        # 验证文件名是否符合规范/验证输出文件是否符合规范(包括文件名是否规范、数据内容是否规范)
        df = pd.read_csv(deploy_path, parse_dates=['time'])

        filename = os.path.basename(deploy_path)
        parts = filename.split('_')
        start_str = parts[-2]
        end_str = parts[-1].replace('.csv', '')
        start_time = datetime.strptime(start_str, "%Y%m%d%H%M")
        end_time = datetime.strptime(end_str, "%Y%m%d%H%M")

        time_diff = df['time'].max() - df['time'].min()
        if TEST_TIMELINESS == 'UST':
            assert end_time - start_time == timedelta(hours=3, minutes=45)
            assert time_diff == timedelta(hours=3, minutes=45)
        elif TEST_TIMELINESS == 'ST':
            assert end_time - start_time == timedelta(days=2, hours=23, minutes=45)
            assert time_diff == timedelta(days=2, hours=23, minutes=45)
        elif TEST_TIMELINESS == 'MT':
            assert end_time - start_time == timedelta(days=9, hours=23, minutes=45)
            assert time_diff == timedelta(days=9, hours=23, minutes=45)

        df['hour'] = df['time'].dt.hour

        # 1. 检查 0-1 点均值是否为 0   避免时区发生错误
        mask_0_3 = (df['hour'] >= 0) & (df['hour'] < 1)
        mean_0_3 = df.loc[mask_0_3, 'power'].mean()
        assert mean_0_3 == 0, f"0-3点功率均值应为0，实际为 {mean_0_3}"

        # 2. 检查 12-13 点均值是否 >0
        mask_12_13 = (df['hour'] >= 12) & (df['hour'] < 13)
        mean_12_13 = df.loc[mask_12_13, 'power'].mean()
        assert mean_12_13 > 0, f"12-13点功率均值应大于0，实际为 {mean_12_13}"

        # 各项要素需求，按要求修改
        for index, row in df.iterrows():
            assert isinstance(row['time'], pd.Timestamp)
            assert row['power'] >= 0
            assert 0 <= row['radi'] <= 1400
            assert row['ghi_pw'] >= 0
            assert row['poa_pw'] >= 0

        
        # 验证日志记录
        mock_logger.info.assert_called()
        
        # 验证消息队列调用
        assert mock_message_queue_producer.send_power.called


class TestDeployModel:
    """测试 deployModel 函数"""
    
    def test_deploy_model_success(self, setup_dirs, mock_logger, mock_message_queue_producer):
        """测试模型部署成功的情况"""
        # 准备测试文件
        model_filename = f"model_{TEST_DATETIME.strftime('%Y%m%d%H%M')}.pth"
        hash_filename = f"model_{TEST_DATETIME.strftime('%Y%m%d%H%M')}.hash"
        key_filename = f"model_{TEST_DATETIME.strftime('%Y%m%d%H%M')}.key"
        
        output_paths = {
            'model': [os.path.join(TEST_OUTPUT_DIR, model_filename)],
            'hash': [os.path.join(TEST_OUTPUT_DIR, hash_filename)],
            'key': [os.path.join(TEST_OUTPUT_DIR, key_filename)]
        }
        
        deploy_paths = {
            'model': [os.path.join(TEST_DEPLOY_DIR, model_filename)],
            'hash': [os.path.join(TEST_DEPLOY_DIR, hash_filename)],
            'key': [os.path.join(TEST_DEPLOY_DIR, key_filename)]
        }
        
        # 创建测试文件
        for file_list in output_paths.values():
            for file_path in file_list:
                with open(file_path, 'w') as f:
                    f.write("test content")
        
        # 调用被测试函数
        deploy.deployModel(
            staTaskId=TEST_STA_ID,
            taskDate=TEST_DATETIME,
            timeliness=TEST_TIMELINESS,
            outputPaths=output_paths,
            deployPaths=deploy_paths,
            logger=mock_logger,
            messageQueueProducer=mock_message_queue_producer
        )
        
        # 验证输出文件是否存在
        for file_list in deploy_paths.values():
            for file_path in file_list:
                assert os.path.exists(file_path)
        
        # 验证日志记录
        mock_logger.info.assert_called()
        
        # 验证消息队列调用
        assert mock_message_queue_producer.send.called


class TestDeployIntegration:
    """测试 deploy 函数的集成测试"""
    
    @patch('src.deploy.deployMeteo')
    @patch('src.deploy.deployPower')
    @patch('src.deploy.deployModel')
    def test_deploy_with_different_timeliness(self, mock_deploy_model, mock_deploy_power, mock_deploy_meteo, mock_logger, mock_message_queue_producer):
        """测试不同时效类型的部署"""
        # 准备测试参数
        params = MagicMock()
        params.staParams = {
            'test_station': MagicMock(
                staId=TEST_STA_ID,
                staType='PV',
                timeLiness=['UST', 'ST', 'MT', 'SS'],
                algorithm={TEST_ALGORITHM: [TEST_VERSION]},
                dataset='test_dataset'
            )
        }
        
        params.task = MagicMock()
        params.task.dateRange = [TEST_DATETIME, TEST_DATETIME + timedelta(days=1)]
        params.task.taskType = 'FC'  # 预测任务
        
        # 模拟路径设置
        params.path.setOutputPath = MagicMock(return_value={
            'meteo': ['/fake/output/meteo.csv'],
            'power': ['/fake/output/power.csv']
        })
        
        params.path.setDeploymentPath = MagicMock(return_value={
            'meteo': ['/fake/deploy/meteo.csv'],
            'power': ['/fake/deploy/power.csv']
        })
        
        # 调用被测试函数
        deploy.deploy(
            params=params,
            checkpoint=None,
            logger=mock_logger,
            messageQueueProducer=mock_message_queue_producer
        )
        
        # 验证不同时效类型的部署函数被调用
        assert mock_deploy_meteo.called
        assert mock_deploy_power.called
        assert not mock_deploy_model.called  # FC任务不应该调用deployModel
        
        # 验证日志记录
        mock_logger.info.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-k", "TestDeployPower and test_deploy_power_success"])

