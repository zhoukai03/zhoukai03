import pytest
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import patch, MagicMock
from enum import Enum
import os
import random
import sys

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.params import (
    CParamsInit,
    CParamsTask,
    CStaParams,
    CParamsPath
)
from src.message import Cproducer
from src.config.TypeDefine import TaskType, TimeLiness
from src.datasets.dataLoader import CDataLoader


@pytest.fixture
def test_params():
    """Fixture providing test parameters."""
    init = CParamsInit()
    init.logLevel = "INFO"

    init.databaseURL = "192.168.1.106"
    init.database = True
    init.databaseName = "postgres"
    init.databaseUser = "postgres"
    init.databasePassword = "energyhxkj123#@!"
    init.databasePort = "32320"

    task = CParamsTask()
    task.taskType = TaskType.FC
    task.dateRange = ["2024-05-1 00:00:00Z", "2024-05-2 00:00:00Z"]
    task.algorithm = {"baseline": ["last"]}
    task.dataset = ["EC_C1D"]
    task.accuracy = ["rmse"]
    task.postProcess = ["dynamicOptimization"]

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


"需连接服务器测试，不同子模块查询的库表不同，数据时间也不同，按需修改"
TEST_DATETIME = pd.Timestamp('2025-05-22 8:30:00', tz='UTC')
TEST_DATETIME_TOP = pd.Timestamp('2025-05-22 8:30:00', tz='UTC')
dataSource = ['EC_C1D']
logger =  logging.getLogger()

def sample_data(starttime = TEST_DATETIME, p = 48, missing_count=4):
    """生成测试用的数据，逐小时间隔，并且将除去首末以外的随机几行设置为nan"""

    index = pd.date_range(start=starttime, periods=p, freq='1h', tz='UTC')

    # 生成随机数据
    data = {
        'departureTime': [starttime] * p,
        't2': np.random.uniform(-10, 40, p),
        'rhu': np.random.uniform(0, 100, p),
    }
    df = pd.DataFrame(data, index=index)

    # 随机选择要删除的行，但不能是第一行或最后一行
    possible_missing_indices = list(range(1, p - 1))  # 排除首尾
    missing_indices = random.sample(possible_missing_indices, k=missing_count)
    numeric_cols = ['t2', 'rhu']
    df.loc[df.index[missing_indices], numeric_cols] = np.nan

    return df


def test_DataFrame2Dict(test_params):
    """测试插补模块"""
    init, task, sta, path = test_params

    p = 48
    missing_count = 4
    test_df = sample_data(TEST_DATETIME, p, missing_count)



    print(test_df)
    # 调用插补函数
    data_loader = CDataLoader()
    dataColumn = data_loader.DataFrame2Dict(
        dataFrame=test_df,
        staId=sta.staId,
        dataSource=dataSource,
        logger=logger,
        timestart=TEST_DATETIME,
        ratio=0.1,
        isTrain=True,
        isPower=False
    )

    # 检查输出 dataColumn ,行数正确，时间连续，间隔15min，且无nan值，则结果正确
    assert isinstance(dataColumn, dict)

    expected_columns = [col for col in test_df.columns if col not in ['departureTime']]
    for col in expected_columns:
        assert col in dataColumn, f"字典缺少关键列 {col}"

    for key, df in dataColumn.items():
        assert isinstance(df, pd.DataFrame), f"{key} 对应的值不是 DataFrame"
        assert len(df) == 1, "每个变量应为单行数据"
        assert len(df.columns) == 4 * (p - 1) + 1, f"每个变量时间节点不符合"

    for df in dataColumn.values():
        assert not df.isnull().any().any(), "存在未填充的缺失值"

def test_OBSLoadPoint(test_params):

    init, task, sta, path = test_params
    data_loader = CDataLoader(
                        meotoCachePaths=None,
                        meotoOriginalCsvPaths=None,
                        meotoBusinessCsvPaths=None,
                        powerOriginalCsvPaths=None,
                        powerBusinessCsvPaths=None,
                        logger=logger,
                        DataBase=init.database,
                        DataBaseURL=init.databaseURL,
                        DataBaseName=init.databaseName,
                        DataBasePort=init.databasePort,
                        DataBaseUser=init.databaseUser,
                        DataBasePassword=init.databasePassword)

    dataColumn = data_loader.OBSLoadPoint(
            staIds=sta.staId,
            staTypes=sta.staType,
            key=None,
            timestart=TEST_DATETIME,
            timestop=TEST_DATETIME_TOP,
            logger=logger)

    assert isinstance(dataColumn, dict)
    assert len(dataColumn) > 0  # 至少有一个站点

def test_NWPLoadPoint(test_params):
    dataSource = ['EC_C1D']
    dataElements = ['tcc','u10', 'v10', 'u100', 'v100', 't2',
                    'sp', 'rhu', 'skt', 'win10_spd', 'win10_dir', 'd2', 'tp']
    init, task, sta, path = test_params
    data_loader = CDataLoader(
                        meotoCachePaths=None,
                        meotoOriginalCsvPaths=None,
                        meotoBusinessCsvPaths=None,
                        powerOriginalCsvPaths=None,
                        powerBusinessCsvPaths=None,
                        logger=logger,
                        DataBase=init.database,
                        DataBaseURL=init.databaseURL,
                        DataBaseName=init.databaseName,
                        DataBasePort=init.databasePort,
                        DataBaseUser=init.databaseUser,
                        DataBasePassword=init.databasePassword)

    dataColumn = data_loader.NWPLoadPoint(
        staId=sta.staId,
        staLat = sta.staLat,
        staLon=sta.staLon,
        timelinessList = sta.timeLiness,
        dataSources=dataSource,
        dataElements=dataElements,
        timestart=TEST_DATETIME,
        timestop=TEST_DATETIME_TOP,
        logger=logger,
        businessFlag=False,
        originMeteoFileFlag=False,
        isTrain=True)
    assert isinstance(dataColumn, dict)
    assert len(dataColumn) > 0  # 至少有一个站点
    expected_columns = [col for col in dataElements if col not in ['departureTime']]
    for var in expected_columns:
        df = dataColumn[sta.staId][sta.timeLiness[0]][dataSource[0]][var]

        # 检查是否是 DataFrame
        assert isinstance(df, pd.DataFrame), f"{var} 不是 DataFrame"

        # 检查形状：1 行 × 961 列
        assert df.shape == (1, 961), f"{var} 的形状应为 (1, 961)，实际为 {df.shape}"

        # 检查无 NaN 值
        assert not df.isna().any().any(), f"{var} 包含 NaN 值"

def test_FCLoadPoint(test_params):
    init, task, sta, path = test_params
    data_loader = CDataLoader(
                        meotoCachePaths=None,
                        meotoOriginalCsvPaths=None,
                        meotoBusinessCsvPaths=None,
                        powerOriginalCsvPaths=None,
                        powerBusinessCsvPaths=None,
                        logger=logger,
                        DataBase=init.database,
                        DataBaseURL=init.databaseURL,
                        DataBaseName=init.databaseName,
                        DataBasePort=init.databasePort,
                        DataBaseUser=init.databaseUser,
                        DataBasePassword=init.databasePassword)

    dataColumn = data_loader.FCLoadPoint(
        staId=sta.staId,
        staType=sta.staType,
        timelinessList = sta.timeLiness,
        timestart=TEST_DATETIME,
        timestop=TEST_DATETIME_TOP,
        logger=logger,
        businessFlag=False)

    assert isinstance(dataColumn, dict)
    assert len(dataColumn) > 0  # 至少有一个站点



if __name__ == '__main__':
    pytest.main(["-v", "-s", "-k", "test_FCLoadPoint"])