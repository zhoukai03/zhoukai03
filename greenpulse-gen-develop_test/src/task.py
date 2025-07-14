"""
# GreenPulse 新能源功率预测系统 - 核心任务处理模块

## 模块概述
`task.py` 是 GreenPulse 新能源功率预测系统的核心任务处理模块，负责执行各种类型的预测、训练和后处理任务。
该模块采用模块化设计，支持单站点任务，并可通过 Ray 框架实现分布式计算，提高大规模数据处理效率。

## 主要功能

### 1. 预测任务
- **超短期预测 (UST)**: 15分钟间隔的短期功率预测
- **短期预测 (ST)**: 日级功率预测
- **中期预测 (MT)**: 中长期功率预测
- **次季节预测 (SS)**: 次季节尺度预测

### 2. 模型训练
- **全量训练 (FT)**: 完整模型训练
- **增量更新训练 (UPT)**: 模型增量更新
- **模型评估**: 提供多种评估指标

### 3. 后处理
- 预测结果后处理
- 历史预测后处理
- 模型训练后处理

### 4. 分布式计算
- 基于 Ray 框架的分布式任务处理
- 支持任务并行执行

## 核心函数

### 预测相关
- `taskSingleForecast`: 单站点预测主函数
- `taskSingleForecastRemote`: Ray 远程预测任务
- `taskSingleHistryForecast`: 历史预测主函数
- `taskSingleHistryForecastRemote`: Ray 远程历史预测

### 训练相关
- `taskSingleTrain`: 模型训练主函数
- `taskSingleTrainRemote`: Ray 远程训练任务
- `taskSinglePostTrain`: 训练后处理

### 后处理
- `taskSinglePostForecast`: 预测后处理
- `taskSinglePostHistoryForecast`: 历史预测后处理
- `taskSingleMeteoPickBest`: 气象数据优选

### 任务分发
- `taskDeal`: 任务分发主入口，支持以下任务类型：
  - `FC`: 普通预测任务
  - `RFC`: 实时预测任务
  - `HFC`: 历史预测任务
  - `FT`: 全量训练任务
  - `UPT`: 更新训练任务
  - `PHFC`: 历史预测后处理

## 使用示例

```python
from task import taskDeal
import params as pp
import logger as lg
from message import Cproducer

# 初始化参数
params = pp.CParams()
logger = lg.setLogger()
messageQueueProducer = Cproducer()

# 执行任务
taskDeal(params, logger, messageQueueProducer)
```

## 数据流
1. **输入数据**: 
   - 气象数据 (NWP, 观测数据等)
   - 历史功率数据
   - 模型参数

2. **处理流程**:
   - 数据加载与预处理
   - 特征工程
   - 模型推理/训练
   - 结果后处理
   - 输出保存

## 依赖项
- **标准库**: 
  - os, sys, logging, datetime, typing, glob, traceback

- **第三方库**: 
  - ray: 分布式计算框架
  - pandas: 数据处理
  - numpy: 数值计算

- **项目模块**:
  - src.params: 参数配置
  - src.logger: 日志管理
  - src.message: 消息队列
  - src.config.TypeDefine: 类型定义
  - src.modelset: 模型管理
  - src.post: 后处理模块
  - src.datasets: 数据加载与保存

## 注意事项
1. **环境要求**:
   - 使用 Ray 分布式计算时需要先初始化 Ray 环境
   - 确保正确配置数据库连接参数

2. **功能限制**:
   - 目前仅支持单站点任务，区域任务尚未实现
   - 模型版本目前仅支持 "last" 版本

3. **性能考虑**:
   - 大数据量时建议使用分布式模式
   - 注意内存使用情况，适当控制批量大小

## TODO
1. 优化数据加载类引入逻辑
2. 实现区域任务功能
3. 支持更多模型版本管理
4. 增强错误处理和重试机制
"""
import os
import ray
import glob
import logging
import traceback
import numpy as np
import pandas as pd
from typing import Union

from . import accuracy
from . import params as pp
from . import logger as lg
from .modelset import modelget
from .post import postget
from .message import Cproducer
from .config.TypeDefine import TaskType, TimeLiness, TimeLinessFcHour
from .datasets import dataLoader, dataDump, modelLoad, modelDump

@ray.remote
def taskSingleForecastRemote(
        staTaskId: str,
        initParams: pp.CParamsInit,
        taskParams: pp.CParamsTask,
        staParam: pp.CStaParams,
        pathParams: pp.CParamsPath,
        logger: lg.logging.Logger,
        messageQueueProducer: Cproducer,
):
    taskSingleForecast(staTaskId, initParams, taskParams, staParam, pathParams, logger, messageQueueProducer)


def taskSingleForecast(
        staTaskId: str,
        initParams: pp.CParamsInit,
        taskParams: pp.CParamsTask,
        staParam: pp.CStaParams,
        pathParams: pp.CParamsPath,
        logger: lg.logging.Logger,
        messageQueueProducer: Cproducer,
):
    """
    执行单站点功率预测任务。

    该函数是GreenPulse系统的核心预测函数，负责加载模型、处理输入数据、执行预测并保存预测结果。
    支持多种时间尺度（超短期、短期、中期、次季节）的功率预测，能够处理不同类型（光伏、风电）的站点。
    函数会自动处理气象数据加载、特征工程、模型推理和结果保存等完整预测流程。

    预测流程：
    1. 根据时间尺度配置生成预测时间序列
    2. 加载对应站点的预测模型
    3. 获取并预处理气象数据（NWP等）
    4. 执行模型预测
    5. 保存预测结果到指定路径
    6. 记录执行日志和状态

    参数
    ----------
    staTaskId : str
        站点任务ID，用于唯一标识当前预测任务
    initParams : pp.CParamsInit
        初始化参数对象，包含以下关键配置：
        - database: 数据库连接信息
        - logLevel: 日志级别
        - 其他数据库相关认证信息
    taskParams : pp.CParamsTask
        任务参数对象，包含：
        - taskType: 任务类型（FC/RFC/HFC等）
        - dateRange: 预测日期范围 [start_date, end_date]
        - 其他任务相关配置
    staParam : pp.CStaParams
        站点参数对象，包含：
        - staId: 站点ID
        - staLat/staLon: 站点经纬度
        - dataset: 使用的数据集
        - timeLiness: 时间尺度列表 ["UST", "ST", "MT", "SS"]
        - algorithm: 算法配置字典
        - staType: 站点类型（光伏/风电）
    pathParams : pp.CParamsPath
        路径参数对象，用于构建：
        - 模型加载路径
        - 预测结果保存路径
        - 日志文件路径
    logger : logging.Logger
        日志记录器实例，用于记录：
        - 任务开始/结束状态
        - 关键步骤执行情况
        - 警告和错误信息
    messageQueueProducer : Cproducer
        消息队列生产者实例，用于：
        - 发送任务执行状态更新
        - 记录预测结果路径
        - 报告任务执行异常

    返回
    -------
    None
        该函数不直接返回值，预测结果会保存到 pathParams 指定的输出路径中

    异常
    ------
    ValueError
        - 当日期参数无效时
        - 当预测结果验证失败时
    RuntimeError
        - 当时间尺度配置无效时（非UST/ST/MT/SS）
        - 当模型加载或预测失败时
    Exception
        - 当发生其他未处理的异常时

    示例
    --------
    >>> from task import taskSingleForecast
    >>> from config import CParamsInit, CParamsTask, CStaParams, CParamsPath
    >>> import logger as lg
    >>> from message import Cproducer
    >>>
    >>> # 初始化参数
    >>> init_params = CParamsInit()
    >>> task_params = CParamsTask(taskType="FC", dateRange=["2023-01-01", "2023-01-02"])
    >>> sta_param = CStaParams(staId="SITE001", staLat=30.5, staLon=120.5, 
    ...                        dataset=["EC_C1D", "EC_C3E"], 
    ...                        timeLiness=["UST", "ST"],
    ...                        algorithm={"XGBoost": ["v1"]},
    ...                        staType="PV")
    >>> path_params = CParamsPath()
    >>> logger = lg.setLogger()
    >>> producer = Cproducer()
    >>>
    >>> # 执行预测
    >>> taskSingleForecast("SITE001_202301011200", init_params, task_params, 
    ...                   sta_param, path_params, logger, producer)

    注意事项
    --------
    1. 确保在调用前已正确初始化Ray环境（如果使用分布式模式）
    2. 确保数据库连接参数配置正确
    3. 预测结果将保存到 pathParams 指定的路径中
    4. 对于 UST（超短期）预测，时间粒度为15分钟
    5. 函数会处理时区转换（Asia/Shanghai）
    """

    for timeliness in staParam.timeLiness:
        if taskParams.dateRange[0] and taskParams.dateRange[1]:
            if timeliness == "UST":
                taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                             freq="15min")
            elif timeliness == "ST":
                taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                             freq="D")
            elif timeliness == "MT":
                taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                             freq="D")
            elif timeliness == "SS":
                taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                             freq="D")
            else:
                raise RuntimeError("Invalid timeLiness")
        else:
            raise ValueError("日期参数传输错误")
        for taskDate in taskDateList:
            for algorithm, versions in staParam.algorithm.items():
                for version in versions:

                    taskDate = taskDate.replace(minute = int(taskDate.minute / 15) * 15)

                    logger.info(f"站点: {staParam.staId} 日期: {taskDate} 时效: {timeliness} 算法: {algorithm} 版本: {version}")

                    outputPath = pathParams.setOutputPath(staParam.staId, staParam.dataset, timeliness, taskDate,
                                                          algorithm, version)

                    inputPath = pathParams.setInputPath(staParam.staId, staParam.dataset, timeliness, taskDate,
                                                        algorithm, version)

                    fcDataDateStart = taskDate.tz_convert("Asia/Shanghai").replace(hour=0, minute=0, second=0, microsecond=0)
                    fcDataDateEnd = fcDataDateStart + pd.to_timedelta(72, 'hour') - pd.to_timedelta(15, 'min')
                    # TODO taskDate - pd.to_timedelta(1, 'day') 是否能匹配上中间文件生成的时间?
                    outputPath_fc = pathParams.setOutputPath(staParam.staId, staParam.dataset, "ST", taskDate - pd.to_timedelta(1, 'day'),
                                                          algorithm, version, checkpoint='noNONE')
                    delopymentPath = pathParams.setDeploymentPath(staParam.staId, staParam.staType, fcDataDateStart, fcDataDateEnd)

                    outputPathPattern = pathParams.returnOutputPath()
                    inputPathPattern = pathParams.returnInputPath()

                    dataLoaderInstance = dataLoader.CDataLoader(
                        meotoCachePaths=outputPathPattern['meteo'],
                        meotoOriginalCsvPaths=inputPath['meteo']['original'],
                        meotoBusinessCsvPaths=inputPath['meteo']['business'],
                        powerOriginalCsvPaths=outputPath_fc['power'],
                        powerBusinessCsvPaths=delopymentPath['power'],
                        logger=logger,
                        DataBase=initParams.database,
                        DataBaseURL=initParams.databaseURL,
                        DataBaseName=initParams.databaseName,
                        DataBasePort=initParams.databasePort,
                        DataBaseUser=initParams.databaseUser,
                        DataBasePassword=initParams.databasePassword)

                    if timeliness == "UST":
                        timeLinessEnum = TimeLiness.UST
                    elif timeliness == "ST":
                        timeLinessEnum = TimeLiness.ST
                    elif timeliness == "MT":
                        timeLinessEnum = TimeLiness.MT
                    elif timeliness == "SS":
                        timeLinessEnum = TimeLiness.SS
                    else:
                        raise RuntimeError("Invalid timeLiness")

                    staParamOne = staParam
                    staParamOne.algorithm = { algorithm:[version] }
                    staParamOne.timeLiness = [ timeliness ]
                    pattern = modelget(staParamOne, timeLinessEnum, algorithm, version, logger=logger)
                    patternLogger = lg.setTaskLogger(logFileFullPath=outputPath['log'], logLevel=initParams.logLevel)
                    for path in outputPath['log']:
                        messageQueueProducer.send_log(
                            staTaskId,
                            timeliness,
                            path
                        )

                    try:
                        taskMeteoTime = taskDate.replace(minute=0)
                        while taskMeteoTime.hour != 12:
                            taskMeteoTime = taskMeteoTime - pd.Timedelta(hours=1)
                        X = dataLoaderInstance.NWPLoadPoint(
                            staId=staParam.staId,
                            staLat=staParam.staLat,
                            staLon=staParam.staLon,
                            timelinessList=[timeliness],
                            dataSources=staParam.dataset,
                            dataElements=["sp", "tcc", "u100", "v100", "u10", "v10", "win10_spd", "win10_dir", "rhu", "skt", "t2", "d2", "tp"],
                            timestart=taskMeteoTime,
                            timestop=taskMeteoTime,
                            logger=logger,
                            businessFlag=True,
                            isTrain=False
                        )
                    except Exception as e:
                        taskMeteoTime = taskMeteoTime - pd.Timedelta(1, 'd')
                        X = dataLoaderInstance.NWPLoadPoint(
                            staId=staParam.staId,
                            staLat=staParam.staLat,
                            staLon=staParam.staLon,
                            timelinessList=[timeliness],
                            dataSources=staParam.dataset,
                            dataElements=["sp", "tcc", "u100", "v100", "u10", "v10", "win10_spd", "win10_dir", "rhu", "skt",
                                        "t2", "d2", "tp"],
                            timestart=taskMeteoTime,
                            timestop=taskMeteoTime,
                            logger=logger,
                            businessFlag=True,
                            isTrain=False
                        )
                    if timeliness != TimeLiness.UST.name:
                        EC_C3E = dataLoaderInstance.NWPLoadPoint(
                            staId=staParam.staId,
                            staLat=staParam.staLat,
                            staLon=staParam.staLon,
                            timelinessList=[timeliness],
                            dataSources=['EC_C3E'],
                            dataElements=["sp", "tcc", "u100", "v100", "u10", "v10", "win10_spd", "win10_dir", "rhu", "skt",
                                          "t2", "d2", "tp"],
                            timestart=taskMeteoTime,
                            timestop=taskMeteoTime,
                            logger=logger,
                            businessFlag=True,
                            isTrain=False
                        )

                        for _staId, Vaule1 in EC_C3E.items():
                            for _timeliness, Vaule2 in Vaule1.items():
                                X[_staId][_timeliness]["EC_C3E"] = EC_C3E[_staId][_timeliness]['EC_C3E']
                                for _dataSources, Vaule3 in Vaule2.items():
                                    for _dataElements, Vaule4 in Vaule3.items():
                                        X[_staId][_timeliness]["EC_C1D"][_dataElements] = pd.concat([X[_staId][_timeliness]['EC_C1D'][_dataElements], Vaule4], axis=1)
                                        combined = X[_staId][_timeliness]["EC_C1D"][_dataElements]
                                        combined = combined.loc[:, ~combined.columns.duplicated(keep='first')]
                                        X[_staId][_timeliness]["EC_C1D"][_dataElements] = combined

                    for meteoPath in outputPath['meteo']:
                        dataset = meteoPath.split('/')[-1].split('.')[0]
                        X_df = dataLoaderInstance.Dict2DataFrame(X)
                        X_df2output = X_df[staParam.staId][timeliness][dataset][taskMeteoTime]
                        dataDump.meteoDump(staTaskId, staParam.staType, X_df2output, timeliness, meteoPath, taskMeteoTime, logger)

                    modelFileFlag = False
                    for i in range(len(outputPath['model'])):
                        try:
                            model = modelLoad.modelLoad(outputPath['model'][i],
                                                        outputPath['hash'][i],
                                                        outputPath['key'][i],
                                                        logger)
                            modelFileFlag = True
                        except Exception as e:
                            logger.warning(f"模型文件加载失败: {e}")
                    if not modelFileFlag:
                        raise ValueError(f"模型文件加载失败")

                    if timeliness == TimeLiness.UST.name:
                        minute = int(taskDate.minute / 15) * 15
                        # 超短期提前45分钟预报
                        fcTaskDate = taskDate.tz_convert('Asia/Shanghai').replace(minute=minute, second=0, microsecond=0).tz_convert('UTC')
                    elif timeliness == TimeLiness.ST.name:
                        fcTaskDate = taskDate.tz_convert('Asia/Shanghai').replace(hour=0, minute=0, second=0, microsecond=0).tz_convert('UTC') + pd.Timedelta(8, 'h')
                    elif timeliness == TimeLiness.MT.name:
                        fcTaskDate = taskDate.tz_convert('Asia/Shanghai').replace(hour=0, minute=0, second=0, microsecond=0).tz_convert('UTC') + pd.Timedelta(8, 'h')
                    elif timeliness == TimeLiness.SS.name:
                        fcTaskDate = taskDate.tz_convert('Asia/Shanghai').replace(hour=0, minute=0, second=0, microsecond=0).tz_convert('UTC') + pd.Timedelta(8, 'h')
                    else:
                        raise ValueError(f"时间尺度错误: {timeliness}")

                    if timeliness == "UST":
                        try:
                            taskFcMeteoTime = taskDate.tz_convert('Asia/Shanghai').replace(hour=0, minute=0, second=0, microsecond=0, nanosecond=0)
                            logger.info(f"尝试读取短期预测数据：{taskFcMeteoTime}")
                            Z = dataLoaderInstance.FCLoadPoint(
                                staId=staParam.staId,
                                staType=staParam.staType,
                                timelinessList=["ST"],
                                timestart=taskFcMeteoTime,
                                timestop=taskFcMeteoTime,
                                logger=logger,
                                businessFlag=False,
                            )

                            for _staId, Vaule1 in Z.items():
                                for _timeliness, Vaule2 in Vaule1.items():
                                    for _dataSources, Vaule3 in Vaule2.items():
                                        _dataElementsDict = dict()
                                        for _dataElements, Vaule4 in Vaule3.items():
                                            _dataElementsDict.update({_dataElements: Vaule4})
                                        X[_staId].update({_timeliness: {_dataSources: _dataElementsDict}})
                        except Exception as e:
                            try:
                                taskFcMeteoTime = taskFcMeteoTime - pd.Timedelta(1, 'd')
                                logger.error(f"尝试读取短期预测数据失败：{e}, 再次尝试: {taskFcMeteoTime}")
                                Z = dataLoaderInstance.FCLoadPoint(
                                    staId=staParam.staId,
                                    staType=staParam.staType,
                                    timelinessList=["ST"],
                                    timestart=taskFcMeteoTime,
                                    timestop=taskFcMeteoTime,
                                    logger=logger,
                                    businessFlag=False
                                )

                                for _staId, Vaule1 in Z.items():
                                    for _timeliness, Vaule2 in Vaule1.items():
                                        for _dataSources, Vaule3 in Vaule2.items():
                                            _dataElementsDict = dict()
                                            for _dataElements, Vaule4 in Vaule3.items():
                                                _dataElementsDict.update({_dataElements: Vaule4})
                                            X[_staId].update({_timeliness: {_dataSources: _dataElementsDict}})
                            except Exception as e:
                                logger.error(f"未能加载短期预测数据: {e}")

                        try:
                            Y = dataLoaderInstance.OBSLoadPoint(
                                staIds=[staParam.staId],
                                staTypes=[staParam.staType],
                                key=None,
                                timestart=None,
                                timestop=None,
                                logger=logger
                            )
                            X[staParam.staId]['UST']['OBS'] = Y[staParam.staId]
                        except Exception as e:
                            logger.error(f"未能加载观测数据: {e}")

                    pattern.load(model, patternLogger)

                    if algorithm == "machinelearning":
                        # 生成输出路径, 其中日期无用，模型路径无需日期
                        outputPathBaseline = pathParams.setOutputPath(staParam.staId, staParam.dataset, timeliness,
                                                              pd.Timestamp.utcnow(),
                                                              "baseline", version, None)
                        modelFileFlag = False
                        for i in range(len(outputPathBaseline['model'])):
                            try:
                                baselinemodel = modelLoad.modelLoad(outputPathBaseline['model'][i],
                                                                    outputPathBaseline['hash'][i],
                                                                    outputPathBaseline['key'][i],
                                                                    logger)
                                modelFileFlag = True
                            except Exception as e:
                                logger.warning(f"模型文件加载失败: {e}")
                        if not modelFileFlag:
                            raise ValueError(f"模型文件加载失败")

                    # 预测
                    if "baselinemodel" in locals():
                        fcdata = pattern.predict(X, fcTaskDate, staParam, patternLogger, dataLoader, baselinemodel=baselinemodel)
                    else:
                        fcdata: pd.DataFrame = pattern.predict(X, fcTaskDate, staParam, patternLogger, dataLoader)

                    # 预测结果检验
                    if 'time' not in fcdata.columns and fcdata.index.name != 'time':
                        raise ValueError(f"预测结果列缺失: time")
                    if 'power' not in fcdata.columns:
                        raise ValueError(f"预测结果列缺失: power")
                    if staParam.staType == "PV":
                        if 'radi' not in fcdata.columns:
                            raise ValueError(f"预测结果列缺失: radi, {fcdata.columns}")
                    elif staParam.staType == "WD":
                        if 'wind' not in fcdata.columns:
                            raise ValueError(f"预测结果列缺失: wind, {fcdata.columns}")

                    if staParam.staType == "PV":
                        for column in fcdata.columns:
                            errorFlag = False
                            if timeliness == TimeLiness.UST.name:
                                if column != 'power' and column != 'time' and column != 'radi': errorFlag = True
                            else:
                                if column != 'power' and column != 'time' and column != 'radi' and column != 'ghi_pw' and column != 'poa_pw': errorFlag = True
                            if errorFlag:
                                logger.warning(f"预测结果中存在异常列: {column}")
                                #raise ValueError(f"预测结果中存在异常列: {column}")
                    elif staParam.staType == "WD":
                        for column in fcdata.columns:
                            errorFlag = False
                            if column != 'power' and column != 'time' and column != 'wind': errorFlag = True
                            if errorFlag:
                                logger.warning(f"预测结果中存在异常列: {column}")
                                raise ValueError(f"预测结果中存在异常列: {column}")

                    if timeliness == TimeLiness.UST.name:
                        countRight = TimeLinessFcHour.UST.value
                        fcDateStart = taskDate
                        minute = int(taskDate.minute / 15) * 15
                        # 超短期提前45分钟预报
                        fcDateStart = fcDateStart.replace(minute=minute, second=0, microsecond=0) + pd.Timedelta(minutes=45)
                        fcDateEnd = fcDateStart + pd.Timedelta(minutes=15 * countRight * 4 - 1)
                    elif timeliness == TimeLiness.ST.name:
                        countRight = TimeLinessFcHour.ST.value
                        fcDateStart = taskDate.tz_convert('Asia/Shanghai') + pd.Timedelta(days=1)
                        fcDateStart = fcDateStart.replace(hour=0, minute=0, second=0, microsecond=0)
                        fcDateEnd = fcDateStart + pd.Timedelta(minutes=15 * countRight * 4 - 1)
                    elif timeliness == TimeLiness.MT.name:
                        countRight = TimeLinessFcHour.MT.value
                        fcDateStart = taskDate.tz_convert('Asia/Shanghai') + pd.Timedelta(days=1)
                        fcDateStart = fcDateStart.replace(hour=0, minute=0, second=0, microsecond=0)
                        fcDateEnd = fcDateStart + pd.Timedelta(minutes=15 * countRight * 4 - 1)
                    elif timeliness == TimeLiness.SS.name:
                        countRight = TimeLinessFcHour.SS.value
                        fcDateStart = taskDate.tz_convert('Asia/Shanghai') + pd.Timedelta(days=1)
                        fcDateStart = fcDateStart.replace(hour=0, minute=0, second=0, microsecond=0)
                        fcDateEnd = fcDateStart + pd.Timedelta(minutes=15 * countRight * 4 - 1)
                    else:
                        raise ValueError(f"时间尺度错误: {timeliness}")

                    logger.info(f"任务时间: {taskDate} 预测时间范围: {fcDateStart} ~ {fcDateEnd}")

                    count = fcdata.count()
                    if count[0] == 0:
                        logger.critical(f"预测结果为空: {staParam.staId}")
                    elif count[0] < countRight:
                        logger.critical(f"预测结果不完整: {staParam.staId}")
                    elif count[0] > countRight:
                        logger.warning(f"预测结果数据过多: {staParam.staId}")
                    else:
                        logger.info(f"预测结果完整: {staParam.staId} 校验时序是否完整")
                        fcTime = pd.date_range(start=fcDateStart, end=fcDateEnd, freq="15min")
                        if not fcTime.isin(fcdata.index).all():
                            logger.error(f"预测结果时序不完整: {staParam.staId}")
                        else:
                            logger.info(f"预测结果时序完整: {staParam.staId}")

                    # 预测结果保存
                    # TODO: Delete the following 2 lines to adapt to the official business
                    fcdata = fcdata[(fcdata.index >= fcDateStart) & (fcdata.index <= fcDateEnd)]
                    fcdata = fcdata.resample('15T').interpolate(method='linear')
                    for powerPath in outputPath['power']:
                        dataDump.powerDump(staTaskId, staParam.staId, fcdata, powerPath, timeliness, taskMeteoTime, logger)


@ray.remote
def taskSingleHistryForecastRemote(
        staTaskId: str,
        initParams: pp.CParamsInit,
        taskParams: pp.CParamsTask,
        staParam: pp.CStaParams,
        pathParams: pp.CParamsPath,
        logger: lg.logging.Logger,
        messageQueueProducer: Cproducer,
):
    taskSingleHistryForecast(staTaskId, initParams, taskParams, staParam, pathParams, logger, messageQueueProducer)


def taskSingleHistryForecast(
        staTaskId: str,
        initParams: pp.CParamsInit,
        taskParams: pp.CParamsTask,
        staParam: pp.CStaParams,
        pathParams: pp.CParamsPath,
        logger: lg.logging.Logger,
        messageQueueProducer: Cproducer,
):
    """
    执行单站点历史预测及准确性评估任务。

    该函数是GreenPulse系统的历史预测评估核心函数，通过以下流程完成历史预测和评估：
    1. 调用taskSingleForecast执行历史时间段的预测
    2. 加载历史观测数据
    3. 计算预测结果与观测数据之间的准确性指标
    4. 保存评估结果并记录执行日志

    支持的时间尺度：
    - UST (超短期): 15分钟间隔的短期预测
    - ST (短期): 日级预测
    - MT (中期): 中期预测
    - SS (次季节预测): 次季节尺度预测

    参数
    ----------
    staTaskId : str
        站点任务ID，用于唯一标识当前预测评估任务
    initParams : pp.CParamsInit
        初始化参数对象，包含以下关键配置：
        - database: 数据库连接信息
        - logLevel: 日志级别
        - 其他数据库相关认证信息
    taskParams : pp.CParamsTask
        任务参数对象，包含：
        - taskType: 任务类型（HFC）
        - dateRange: 历史日期范围 [start_date, end_date]
        - 其他任务相关配置
    staParam : pp.CStaParams
        站点参数对象，包含：
        - staId: 站点ID
        - staLat/staLon: 站点经纬度
        - dataset: 使用的数据集列表
        - timeLiness: 时间尺度列表 ["UST", "ST", "MT", "SS"]
        - algorithm: 算法配置字典
        - staType: 站点类型（光伏/风电）
        - accuracy: 需要计算的准确性指标列表
    pathParams : pp.CParamsPath
        路径参数对象，用于构建：
        - 模型加载路径
        - 预测结果保存路径
        - 评估结果保存路径
        - 日志文件路径
    logger : logging.Logger
        日志记录器实例，用于记录：
        - 任务开始/结束状态
        - 关键步骤执行情况
        - 警告和错误信息
    messageQueueProducer : Cproducer
        消息队列生产者实例，用于：
        - 发送任务执行状态更新
        - 记录评估结果路径
        - 报告任务执行异常

    返回
    -------
    None
        该函数不直接返回值，评估结果会保存到 pathParams 指定的输出路径中

    异常
    ------
    ValueError
        - 当日期参数无效时
        - 当观测数据加载失败时
    RuntimeError
        - 当时间尺度配置无效时（非UST/ST/MT/SS）
        - 当准确性指标计算失败时
    Exception
        - 当发生其他未处理的异常时

    示例
    --------
    >>> from task import taskSingleHistryForecast
    >>> from config import CParamsInit, CParamsTask, CStaParams, CParamsPath
    >>> import logger as lg
    >>> from message import Cproducer
    >>>
    >>> # 初始化参数
    >>> init_params = CParamsInit()
    >>> task_params = CParamsTask(taskType="HFC", dateRange=["2023-01-01", "2023-01-31"])
    >>> sta_param = CStaParams(staId="SITE001", staLat=30.5, staLon=120.5, 
    ...                        dataset=["EC_C1D", "EC_C3E"], 
    ...                        timeLiness=["UST", "ST"],
    ...                        algorithm={"XGBoost": ["v1"]},
    ...                        staType="PV",
    ...                        accuracy=["RMSE", "MAE", "MAPE"])
    >>> path_params = CParamsPath()
    >>> logger = lg.setLogger()
    >>> producer = Cproducer()
    >>>
    >>> # 执行历史预测评估
    >>> taskSingleHistryForecast("SITE001_202302011200", init_params, task_params, 
    ...                        sta_param, path_params, logger, producer)

    注意事项
    --------
    1. 确保在调用前已正确初始化Ray环境（如果使用分布式模式）
    2. 确保数据库连接参数配置正确，能够访问历史观测数据
    3. 评估结果将保存到 pathParams 指定的路径中
    4. 对于 UST（超短期）预测，时间粒度为15分钟
    5. 函数会处理时区转换（Asia/Shanghai）
    """

    taskSingleForecast(staTaskId, initParams, taskParams, staParam, pathParams, logger, messageQueueProducer)

    Y = None
    for timeliness in staParam.timeLiness:
        for algorithm, versions in staParam.algorithm.items():
            for version in versions:
                fcDataDict = dict()
                if taskParams.dateRange[0] and taskParams.dateRange[1]:
                    if timeliness == "UST":
                        taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                                     freq="15min")
                    elif timeliness == "ST":
                        taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                                     freq="D")
                    elif timeliness == "MT":
                        taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                                     freq="D")
                    elif timeliness == "SS":
                        taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                                     freq="D")
                    else:
                        raise RuntimeError("Invalid timeLiness")
                else:
                    raise ValueError("日期参数传输错误")

                if timeliness == "UST":
                    timeLinessEnum = TimeLiness.UST
                    timeLinessEnumFcHour = TimeLinessFcHour.UST
                elif timeliness == "ST":
                    timeLinessEnum = TimeLiness.ST
                    timeLinessEnumFcHour = TimeLinessFcHour.ST
                elif timeliness == "MT":
                    timeLinessEnum = TimeLiness.MT
                    timeLinessEnumFcHour = TimeLinessFcHour.MT
                elif timeliness == "SS":
                    timeLinessEnum = TimeLiness.SS
                    timeLinessEnumFcHour = TimeLinessFcHour.SS
                else:
                    raise RuntimeError("Invalid timeLiness")

                for taskDate in taskDateList:

                    taskDate = taskDate.replace(minute=int(taskDate.minute / 15) * 15)

                    outputPath = pathParams.setOutputPath(staParam.staId, staParam.dataset, timeliness, taskDate,
                                                          algorithm, version)
                    inputPath = pathParams.setInputPath(staParam.staId, staParam.dataset, timeliness, taskDate,
                                                        algorithm, version)
                    outputPathPattern = pathParams.returnOutputPath()
                    inputPathPattern = pathParams.returnInputPath()

                    for powerPath in outputPath['power']:
                        try:
                            fcDataSingle = pd.read_csv(powerPath, index_col='time')
                            fcDataSingle.index = pd.to_datetime(fcDataSingle.index)
                            fcDataDict.update({taskDate: fcDataSingle['power']})
                            break
                        except Exception as e:
                            logger.warning(f"读取 {powerPath} 文件错误: {e}")
                            continue
                    if Y is None:
                        # TODO: 这里需要优化, 数据读取应当支持更宽泛的自定义
                        dataLoaderInstance = dataLoader.CDataLoader(
                            meotoCachePaths=outputPathPattern['meteo'],
                            meotoOriginalCsvPaths=inputPathPattern['meteo']['original'],
                            meotoBusinessCsvPaths=inputPathPattern['meteo']['business'],
                            logger=logger,
                            DataBase=initParams.database,
                            DataBaseURL=initParams.databaseURL,
                            DataBaseName=initParams.databaseName,
                            DataBasePort=initParams.databasePort,
                            DataBaseUser=initParams.databaseUser,
                            DataBasePassword=initParams.databasePassword
                        )
                        # 加载观测数据
                        Y = dataLoaderInstance.OBSLoadPoint(staParam.staId, staParam.staType, None, taskDateList[0], taskDateList[-1] + pd.Timedelta(hours=timeLinessEnumFcHour.value),
                                                            logger)

                staParamOne = staParam
                staParamOne.algorithm = {algorithm: [version]}
                staParamOne.timeLiness = [timeliness]

                outputPath = pathParams.setOutputPath(staParam.staId, staParam.dataset, timeliness, taskDate,
                                                      algorithm, version)
                pattern = modelget(staParamOne, timeLinessEnum, algorithm, version, logger=logger)
                patternLogger = lg.setTaskLogger(logFileFullPath=outputPath['log'], logLevel=initParams.logLevel)
                for path in outputPath['log']:
                    messageQueueProducer.send_log(
                        staTaskId,
                        timeliness,
                        path
                    )

                acc = pd.DataFrame()
                acc['acc'] = pd.Series()
                acc['score'] = pd.Series()
                for detailEnum in staParam.accuracy:
                    detail = detailEnum.name
                    accModule = accuracy.__getattr__(detail)
                    accExecutor = accModule.__dict__[detail](staParam, logger=patternLogger)
                    obs = Y[staParam.staId]['power']

                    if timeliness == "UST":
                        accDicts: dict[str, float] = accExecutor.ust_day(fcDataDict, obs, patternLogger)
                    elif timeliness == "ST":
                        accDicts: dict[str, float] = accExecutor.st_day(fcDataDict, obs, patternLogger)
                    else:
                        raise NotImplementedError(f"acc calculate for timeliness {timeliness} not implemented!")

                    for taskDate, accDict in accDicts.items():
                        if acc['acc'].empty:
                            accDf = pd.DataFrame([[detail, accDict["acc"], accDict["score"]]],
                                                 columns=["detail", "acc", "score"], index=[taskDate])
                            accDf.fillna(-999, inplace=True)
                            accDf['start_time'] = taskDate
                            accDf["end_time"] = taskDate
                            acc = accDf
                        else:
                            accDf = pd.DataFrame([[detail, accDict["acc"], accDict["score"]]],
                                                 columns=["detail", "acc", "score"], index=[taskDate])
                            accDf.fillna(-999, inplace=True)
                            accDf['start_time'] = taskDate
                            accDf["end_time"] = taskDate
                            acc = pd.concat([acc, accDf])

                        acc.index.name = 'Datetime'
                        acc['sta_id'] = staParam.staId
                        acc['sta_type'] = staParam.staType
                        acc['algorithm'] = algorithm
                        acc['version'] = version

                acc = acc[
                    ['sta_id', 'sta_type', 'start_time', 'end_time', 'algorithm', 'version', 'detail', 'acc', 'score']]
                taskDateList = acc['start_time'].unique()  # 根据逐日的时效设置taskDateList
                for taskDate in acc['start_time'].unique():
                    accPaths = \
                    pathParams.setOutputPath(staParam.staId, staParam.dataset, timeliness, taskDate, algorithm,
                                             version)['acc']
                    if 'acc' not in locals():
                        raise ValueError("acc not calculated!")
                    else:
                        accSingle = acc[acc.index == taskDate]
                        for accPath in accPaths:
                            dataDump.accDump(staTaskId, accSingle, timeliness, accPath, logger, messageQueueProducer)

    accDict = dict()
    for timeliness in staParam.timeLiness:
        for algorithm, versions in staParam.algorithm.items():
            for version in versions:
                if version != "last":
                    raise NotImplementedError("version not last, not implemented! Now only support last!")
                accDf = pd.DataFrame()

                for taskDate in taskDateList:
                    accPaths = \
                    pathParams.setOutputPath(staParam.staId, staParam.dataset, timeliness, taskDate, algorithm,
                                             version)['acc']
                    for accPath in accPaths:
                        try:
                            acc = pd.read_csv(accPath)

                            break
                        except Exception as e:
                            logger.error(f"读取文件失败: {accPath}, 错误信息: {e}")
                            continue
                    if accDf.empty:
                        accDf = acc
                    else:
                        accDf = pd.concat([accDf, acc])
                accDf.reset_index(drop=True, inplace=True)
                accDfGroup = accDf.groupby(["algorithm", "version", "detail"])
                for key, group in accDfGroup:
                    detail = key[2]
                    accMean = group['acc'].mean()
                    scoreMean = group['score'].mean()
                    # 确保timeliness存在
                    if timeliness not in accDict:
                        accDict[timeliness] = {}

                    # 确保algorithm存在
                    if algorithm not in accDict[timeliness]:
                        accDict[timeliness][algorithm] = {}

                    # 更新或添加version的数据
                    accDict[timeliness][algorithm] = {
                        'acc': accMean,
                        'score': scoreMean
                    }

    for timeliness in staParam.timeLiness:
        # 将算法按照acc值排序 TODO: 优化支持多版本排序
        sorted_algorithms = sorted(accDict[timeliness].items(), key=lambda x: x[1]["acc"], reverse=True)
        # 更新order值
        for order, (algorithm, _) in enumerate(sorted_algorithms):
            accDict[timeliness][algorithm]["order"] = order + 1
        messageQueueProducer.send_pick_best_algorithm(staTaskId, timeliness, accDict[timeliness])


# @ray.remote
def taskSingleTrainRemote(
        staTaskId: str, initParams: pp.CParamsInit, taskParams: pp.CParamsTask, staParam: pp.CStaParams,
        pathParams: pp.CParamsPath, logger, messageQueueProducer: Cproducer
):
    taskSingleTrain(staTaskId, initParams, taskParams, staParam, pathParams, logger, messageQueueProducer)


def taskSingleTrain(
        staTaskId: str, checkpoint: str, initParams: pp.CParamsInit, taskParams: pp.CParamsTask, staParam: pp.CStaParams,
        pathParams: pp.CParamsPath, logger, messageQueueProducer: Cproducer
):
    """
    执行单站点预测模型的训练或更新任务。

    该函数是GreenPulse系统的核心训练接口，负责执行以下任务：
    1. 支持全量训练(FT)和增量更新训练(UPT)两种训练模式
    2. 处理多种时间尺度的预测模型训练（UST/ST/MT/SS）
    3. 管理模型版本和检查点
    4. 处理训练数据的加载和预处理
    5. 保存训练好的模型文件和相关元数据

    支持的时间尺度：
    - UST (超短期): 15分钟间隔的短期预测
    - ST (短期): 日级预测
    - MT (中期): 中期预测
    - SS (次季节预测): 次季节尺度预测

    参数
    ----------
    staTaskId : str
        站点任务ID，格式为"站点ID"，用于唯一标识当前训练任务
    checkpoint : str
        检查点标识，用于模型版本控制，格式为"时间戳"
    initParams : pp.CParamsInit
        初始化参数对象，包含以下关键配置：
        - database: 数据库连接信息
        - logLevel: 日志级别
        - 数据库认证信息（URL, 端口, 用户名, 密码等）
    taskParams : pp.CParamsTask
        任务参数对象，包含：
        - taskType: 任务类型（FT/UPT）
        - dateRange: 训练数据日期范围 [start_date, end_date]
        - 其他任务相关配置
    staParam : pp.CStaParams
        站点参数对象，包含：
        - staId: 站点ID
        - staLat/staLon: 站点经纬度
        - dataset: 使用的数据集列表
        - timeLiness: 时间尺度列表 ["UST", "ST", "MT", "SS"]
        - algorithm: 算法配置字典
        - staType: 站点类型（光伏/风电）
        - accuracy: 需要计算的准确性指标列表
    pathParams : pp.CParamsPath
        路径参数对象，用于构建：
        - 模型保存路径
        - 日志文件路径
        - 中间数据缓存路径
    logger : logging.Logger
        日志记录器实例，用于记录：
        - 任务开始/结束状态
        - 训练进度和指标
        - 警告和错误信息
    messageQueueProducer : Cproducer
        消息队列生产者实例，用于：
        - 发送任务执行状态更新
        - 记录模型保存路径
        - 报告训练异常

    返回
    -------
    None
        该函数不直接返回值，训练结果包括：
        - 训练好的模型文件（.pkl）
        - 模型哈希文件
        - 模型密钥文件
        - 训练日志文件

    异常
    ------
    ValueError
        - 当日期参数无效时
        - 当训练数据不足时
        - 当模型文件加载失败时
    RuntimeError
        - 当时间尺度配置无效时（非UST/ST/MT/SS）
        - 当算法实现不完整时
    Exception
        - 当发生其他未处理的异常时

    示例
    --------
    >>> from task import taskSingleTrain
    >>> from config import CParamsInit, CParamsTask, CStaParams, CParamsPath
    >>> import logger as lg
    >>> from message import Cproducer
    >>>
    >>> # 初始化参数
    >>> init_params = CParamsInit()
    >>> task_params = CParamsTask(taskType="FT", dateRange=["2023-01-01", "2023-01-31"])
    >>> sta_param = CStaParams(staId="SITE001", staLat=30.5, staLon=120.5, 
    ...                        dataset=["EC_C1D", "EC_C3E"], 
    ...                        timeLiness=["UST", "ST"],
    ...                        algorithm={"XGBoost": ["v1"]},
    ...                        staType="PV")
    >>> path_params = CParamsPath()
    >>> logger = lg.setLogger()
    >>> producer = Cproducer()
    >>>
    >>> # 执行模型训练
    >>> taskSingleTrain("SITE001_202302011200", "XGBoost_202302011200", 
    ...                init_params, task_params, sta_param, 
    ...                path_params, logger, producer)

    注意事项
    --------
    1. 全量训练(FT)会从头开始训练新模型，增量训练(UPT)会基于现有模型进行微调
    2. 训练过程中会生成详细的日志文件，记录训练进度和指标
    3. 模型文件会保存到 pathParams 指定的路径中
    4. 对于 baseline 算法有特殊处理逻辑，使用不同的训练流程
    5. 训练数据会自动从数据库加载，需要确保数据库连接配置正确
    6. 训练过程支持断点续训，会检查现有模型文件
    """
    # 训练超短期无需每15分钟都训练
    if taskParams.dateRange[0] and taskParams.dateRange[1]:
        taskDateStart = taskParams.dateRange[0]
        taskDateEnd = taskParams.dateRange[1]
    else:
        raise ValueError("日期参数传输错误")

    for timeLiness in staParam.timeLiness:
        for algorithm, versions in staParam.algorithm.items():
            for version in versions:

                logger.info(f"站点: {staParam.staId} 时效: {timeLiness} 算法: {algorithm} 版本: {version}")

                # 生成输出路径, 其中日期无用，模型路径无需日期
                outputPath = pathParams.setOutputPath(staParam.staId, staParam.dataset, timeLiness, pd.Timestamp.utcnow(),
                                                          algorithm, version, checkpoint)

                outputPathPattern = pathParams.returnOutputPath()
                inputPathPattern = pathParams.returnInputPath()

                pklList = []
                for modelPath in outputPath['model']:
                    modelDir = os.path.dirname(modelPath)
                    fileList = glob.glob(fr'{modelDir}/*.pkl')
                    for x in fileList:
                        if x.endswith('.pkl'):
                            pklList.append(x)

                logger.info(f"已有模型列表: {pklList}")

                if len(pklList) > 0:
                    # TODO : 关闭增量更新，后续算法完善后开启
                    taskParams.taskType = TaskType.FT
                else:
                    taskParams.taskType = TaskType.FT

                if algorithm == "baseline":

                    modelPath = outputPath['model']
                    hashPath = outputPath['hash']
                    keyPath = outputPath['key']

                    if timeLiness == "UST":
                        timeLinessEnum = TimeLiness.UST
                    elif timeLiness == "ST":
                        timeLinessEnum = TimeLiness.ST
                    elif timeLiness == "MT":
                        timeLinessEnum = TimeLiness.MT
                    elif timeLiness == "SS":
                        timeLinessEnum = TimeLiness.SS
                    else:
                        raise RuntimeError("Invalid timeLiness")

                    staParamOne = staParam
                    staParamOne.algorithm = { algorithm:[version] }
                    staParamOne.timeLiness = [ timeLiness ]
                    pattern = modelget(staParamOne, timeLinessEnum, algorithm, version, logger=logger)
                    patternLogger = lg.setTaskLogger(logFileFullPath=outputPath['log'],
                                                        logLevel=initParams.logLevel)
                    for path in outputPath['log']:
                        messageQueueProducer.send_log(
                            staTaskId,
                            timeLiness,
                            path
                        )

                    if taskParams.taskType == TaskType.FT:
                        logger.info(f"{algorithm} {version} {taskParams.taskType.name} 训练开始")
                        model = pattern.train(None, None, None, staParam, patternLogger, None, pyout=pathParams.deployment['root'])
                        for i in range(len(modelPath)):
                            modelDump.modelDump(staTaskId, model, timeLiness, modelPath[i], hashPath[i], keyPath[i],
                                                logger, messageQueueProducer)
                    elif taskParams.taskType == TaskType.UPT:
                        checkpointLast = pklList[-1].split('/')[-1].split('.')[0]
                        outpathLast = pathParams.setOutputPath(staParam.staId, staParam.dataset, timeLiness,
                                                                pd.Timestamp.utcnow(), # 对于模型路径来说，日期无用
                                                                algorithm, version, checkpointLast)
                        logger.info(f"{algorithm} {version} {taskParams.taskType.name} 训练开始")

                        modelFileFlag = False
                        for i in range(len(outputPath['model'])):
                            try:
                                logger.info(f"正在加载模型: {outputPath['model'][i]}")
                                logger.info(f"正在加载模型: {outputPath['hash'][i]}")
                                logger.info(f"正在加载模型: {outputPath['key'][i]}")
                                model = modelLoad.modelLoad(outpathLast['model'][i],
                                                            outpathLast['hash'][i],
                                                            outpathLast['key'][i],
                                                            logger)
                                modelFileFlag = True
                            except Exception as e:
                                logger.warning(f"模型文件加载失败: {e}")
                        if not modelFileFlag:
                            raise ValueError(f"模型文件加载失败")

                        pattern.load(model, patternLogger)
                        # 微调
                        model = pattern.tuning(None, None, None, staParam, patternLogger, None, pyout=pathParams.deployment['root'])
                        for i in range(len(modelPath)):
                            modelDump.modelDump(staTaskId, model, timeLiness, modelPath[i], hashPath[i], keyPath[i],
                                                logger, messageQueueProducer)

                else:

                    dataLoaderInstance = dataLoader.CDataLoader(
                        meotoCachePaths=outputPathPattern['meteo'],
                        meotoOriginalCsvPaths=inputPathPattern['meteo']['original'],
                        meotoBusinessCsvPaths=inputPathPattern['meteo']['business'],
                        logger=logger,
                        DataBase=initParams.database,
                        DataBaseURL=initParams.databaseURL,
                        DataBaseName=initParams.databaseName,
                        DataBasePort=initParams.databasePort,
                        DataBaseUser=initParams.databaseUser,
                        DataBasePassword=initParams.databasePassword
                    )

                    Y = dataLoaderInstance.OBSLoadPoint(staParam.staId, staParam.staType, "power", None, None, logger)
                    YDateStart = Y[staParam.staId]["power"].index[0]
                    YDateEnd = Y[staParam.staId]["power"].index[-1]

                    try:
                        taskMeteoTimeStart = YDateStart.replace(minute=0)
                        taskMeteoTimeEnd = YDateEnd.replace(minute=0)
                        while taskMeteoTimeStart.hour != 12:
                            taskMeteoTimeStart = taskMeteoTimeStart - pd.Timedelta(hours=1)
                        while taskMeteoTimeEnd.hour != 12:
                            taskMeteoTimeEnd = taskMeteoTimeEnd - pd.Timedelta(hours=1)
                        X = dataLoaderInstance.NWPLoadPoint(staId=staParam.staId,
                                                            staLat=staParam.staLat,
                                                            staLon=staParam.staLon,
                                                            timelinessList=[timeLiness],
                                                            dataSources=staParam.dataset,
                                                            dataElements=["sp", "tcc", "u100", "v100", "u10", "v10",
                                                                        "win10_spd", "win10_dir", "rhu", "skt", "t2",
                                                                        "d2"],  # TODO: 需要修改, 在staParam中添加dataElement
                                                            timestart=taskMeteoTimeStart,
                                                            timestop=taskMeteoTimeEnd,
                                                            businessFlag=True,
                                                            logger=logger,
                                                            isTrain=True)
                    except Exception as e:
                        taskMeteoTimeStart = YDateStart - pd.Timedelta(hours=1)
                        taskMeteoTimeEnd = YDateEnd - pd.Timedelta(hours=1)
                        while taskMeteoTimeStart.hour != 12:
                            taskMeteoTimeStart = taskMeteoTimeStart - pd.Timedelta(hours=1)
                        while taskMeteoTimeEnd.hour != 12:
                            taskMeteoTimeEnd = taskMeteoTimeEnd - pd.Timedelta(hours=1)
                        X = dataLoaderInstance.NWPLoadPoint(
                            staId=staParam.staId,
                            staLat=staParam.staLat,
                            staLon=staParam.staLon,
                            timelinessList=[timeLiness],
                            dataSources=staParam.dataset,
                            dataElements=[
                                "sp",
                                "tcc",
                                "u100",
                                "v100",
                                "u10",
                                "v10",
                                "win10_spd",
                                "win10_dir",
                                "rhu",
                                "skt",
                                "t2",
                                "d2",
                                "tp",
                            ],  # TODO: 需要修改, 在staParam中添加dataElement
                            timestart=taskMeteoTimeStart,
                            timestop=taskMeteoTimeEnd,
                            businessFlag=True,
                            logger=logger,
                            isTrain=True
                        )


                    if timeLiness != TimeLiness.UST.name and algorithm == "machinelearning":
                        EC_C3E = dataLoaderInstance.NWPLoadPoint(
                            staId=staParam.staId,
                            staLat=staParam.staLat,
                            staLon=staParam.staLon,
                            timelinessList=[timeLiness],
                            dataSources=['EC_C3E'],
                            dataElements=["sp", "tcc", "u100", "v100", "u10", "v10", "win10_spd", "win10_dir", "rhu", "skt",
                                          "t2", "d2", "tp"],
                            timestart=taskMeteoTimeStart,
                            timestop=taskMeteoTimeEnd,
                            logger=logger,
                            businessFlag=True,
                            isTrain=True
                        )

                        for _staId, Vaule1 in EC_C3E.items():
                            for _timeliness, Vaule2 in Vaule1.items():
                                X[_staId][_timeliness]["EC_C3E"] = EC_C3E[_staId][_timeliness]['EC_C3E']

                    modelPath = outputPath['model']
                    hashPath = outputPath['hash']
                    keyPath = outputPath['key']

                    if timeLiness == "UST":
                        timeLinessEnum = TimeLiness.UST
                    elif timeLiness == "ST":
                        timeLinessEnum = TimeLiness.ST
                    elif timeLiness == "MT":
                        timeLinessEnum = TimeLiness.MT
                    elif timeLiness == "SS":
                        timeLinessEnum = TimeLiness.SS
                    else:
                        raise RuntimeError("Invalid timeLiness")

                    staParamOne = staParam
                    staParamOne.algorithm = { algorithm:[version] }
                    staParamOne.timeLiness = [ timeLiness ]
                    pattern = modelget(staParamOne, timeLinessEnum, algorithm, version, logger=logger)
                    patternLogger = lg.setTaskLogger(logFileFullPath=outputPath['log'], logLevel=initParams.logLevel)
                    for path in outputPath['log']:
                        messageQueueProducer.send_log(
                            staTaskId,
                            timeLiness,
                            path
                        )
                    taskDateList = pd.date_range(start=taskDateStart, end=taskDateEnd, freq="D", tz="UTC")
                    if taskParams.taskType == TaskType.FT:
                        model = pattern.train(X, Y, taskDateList, staParam, patternLogger, dataLoader, pyout=pathParams.deployment['root'])
                        for i in range(len(modelPath)):
                            modelDump.modelDump(staTaskId, model, timeLiness, modelPath[i], hashPath[i], keyPath[i],
                                                logger, messageQueueProducer)
                    elif taskParams.taskType == TaskType.UPT:
                        model = pattern.tuning(X, Y, taskDateList, staParam, patternLogger, dataLoader, pyout=pathParams.deployment['root'])
                        for i in range(len(modelPath)):
                            modelDump.modelDump(staTaskId, model, timeLiness, modelPath[i], hashPath[i], keyPath[i],
                                                logger, messageQueueProducer)


def taskSingleMeteoPickBest(staTaskId: str, initParams: pp.CParamsInit, taskParams: pp.CParamsTask, staParam: pp.CStaParams,
        pathParams: pp.CParamsPath, logger, messageQueueProducer: Cproducer):
    if taskParams.dateRange[0] and taskParams.dateRange[1]:
        taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1], freq="D", tz="UTC")
    else:
        raise ValueError("日期参数传输错误")

    for timeliness in staParam.timeLiness:
            for algorithm, versions in staParam.algorithm.items():
                for version in versions:

                    logger.info(
                        f"站点: {staParam.staId} 时效: {timeliness} 算法: {algorithm} 版本: {version}")

                    outputPathPattern = pathParams.returnOutputPath()
                    inputPathPattern = pathParams.returnInputPath()

                    dataLoaderInstance = dataLoader.CDataLoader(
                        meotoCachePaths=outputPathPattern['meteo'],
                        meotoOriginalCsvPaths=inputPathPattern['meteo']['original'],
                        meotoBusinessCsvPaths=inputPathPattern['meteo']['business'],
                        powerOriginalCsvPaths=outputPathPattern['power']['original'],
                        powerbusinessCsvPaths=outputPathPattern['power']['business'],
                        logger=logger,
                        DataBase=initParams.database,
                        DataBaseURL=initParams.databaseURL,
                        DataBaseName=initParams.databaseName,
                        DataBasePort=initParams.databasePort,
                        DataBaseUser=initParams.databaseUser,
                        DataBasePassword=initParams.databasePassword)

                    taskMeteoTime = taskDateList.replace(hour=12, minute=0, second=0, microsecond=0) - pd.Timedelta(1, 'd')

                    X = dataLoaderInstance.NWPLoadPoint(
                        staId=staParam.staId,
                        staLat=staParam.staLat,
                        staLon=staParam.staLon,
                        timelinessList=[timeliness],
                        dataSources=staParam.dataset,
                        dataElements=["sp", "tcc", "u100", "v100", "u10", "v10", "win10_spd", "win10_dir", "rhu", "skt",
                                      "t2", "d2", "tp"],
                        timestart=taskMeteoTime[0],
                        timestop=taskMeteoTime[-1],
                        logger=logger,
                        businessFlag=True,
                        isTrain=False
                    )

                    Z = dataLoaderInstance.FCLoadPoint(
                        staId=staParam.staId,
                        staType=staParam.staType,
                        timelinessList=[timeliness],
                        timestart=taskMeteoTime[0],
                        timestop=taskMeteoTime[-1],
                        logger=logger,
                        businessFlag=True
                    )

                    # TODO: finish & test
                    pick = PickNWP(deploy_params,X,Z,logger)

                    messageQueueProducer.send_pick_best_meoto(staTaskId, timeliness, pick)


def taskSinglePostForecast(
        staTaskId: str, initParams: pp.CParamsInit, taskParams: pp.CParamsTask, staParam: pp.CStaParams,
        pathParams: pp.CParamsPath, logger, messageQueueProducer: Cproducer):
    """执行单站点预测数据的后处理任务。
    
    该函数负责对预测结果进行后处理，包括：
    1. 加载已训练的后处理模型
    2. 对预测结果进行后处理
    3. 验证后处理结果的完整性和正确性
    4. 保存处理后的预测结果
    
    支持的时间尺度：
    - UST (超短期): 15分钟间隔的超短期功率预测
    - ST (短期): 短期功率预测
    - MT (中期): 中期功率预测
    - SS (次季节预测): 次季节尺度功率预测
    
    参数
    ----------
    staTaskId : str
        站点任务ID，用于唯一标识当前后处理任务
    initParams : pp.CParamsInit
        初始化参数对象，包含：
        - database: 数据库连接信息
        - logLevel: 日志级别
        - 数据库认证信息（URL, 端口, 用户名, 密码等）
    taskParams : pp.CParamsTask
        任务参数对象，包含：
        - dateRange: 预测数据日期范围 [start_date, end_date]
        - 其他任务相关配置
    staParam : pp.CStaParams
        站点参数对象，包含：
        - staId: 站点ID
        - staType: 站点类型（PV/WD）
        - dataset: 使用的数据集列表
        - timeLiness: 时间尺度列表 ["UST", "ST", "MT", "SS"]
        - algorithm: 算法配置字典
    pathParams : pp.CParamsPath
        路径参数对象，用于构建：
        - 输入/输出路径
        - 模型文件路径
        - 日志文件路径
    logger : logging.Logger
        日志记录器实例，用于记录：
        - 任务开始/结束状态
        - 处理进度和指标
        - 警告和错误信息
    messageQueueProducer : Cproducer
        消息队列生产者实例，用于：
        - 发送任务执行状态更新
        - 记录处理结果路径
        - 报告处理异常
        
    异常
    ------
    ValueError
        - 当日期参数无效时
        - 当预测结果列缺失时
        - 当模型文件加载失败时
    RuntimeError
        - 当时间尺度配置无效时（非UST/ST/MT/SS）
    Exception
        - 当发生其他未处理的异常时
        
    注意事项
    --------
    1. 对于PV（光伏）站点，预测结果必须包含'power'和'radi'列
    2. 对于WD（风电）站点，预测结果必须包含'power'和'wind'列
    3. 处理后的结果会保存到指定的输出路径
    4. 对于UST时间尺度，时间会按15分钟间隔对齐
    """
    for timeliness in staParam.timeLiness:
        if taskParams.dateRange[0] and taskParams.dateRange[1]:
            if taskParams.dateRange[0] and taskParams.dateRange[1]:
                if timeliness == "UST":
                    taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                                 freq="15min")
                elif timeliness == "ST":
                    taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                                 freq="D")
                elif timeliness == "MT":
                    taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                                 freq="D")
                elif timeliness == "SS":
                    taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                                 freq="D")
                else:
                    raise RuntimeError("Invalid timeLiness")
        else:
            raise ValueError("日期参数传输错误")
        for taskDate in taskDateList:
            for algorithm, versions in staParam.algorithm.items():
                for version in versions:

                    taskDate = taskDate.replace(minute=int(taskDate.minute / 15) * 15)

                    logger.info(
                        f"站点: {staParam.staId} 日期: {taskDate} 时效: {timeliness} 算法: {algorithm} 版本: {version}")

                    outputPath = pathParams.setOutputPath(staParam.staId, staParam.dataset, timeliness, taskDate,
                                                          algorithm + "_post", version)

                    inputPath = pathParams.setInputPath(staParam.staId, staParam.dataset, timeliness, taskDate,
                                                        algorithm, version)

                    fcDataDateStart = taskDate.tz_convert("Asia/Shanghai").replace(hour=0, minute=0, second=0,
                                                                                   microsecond=0)
                    fcDataDateEnd = fcDataDateStart + pd.to_timedelta(72, 'hour') - pd.to_timedelta(15, 'min')
                    # TODO taskDate - pd.to_timedelta(1, 'day') 是否能匹配上中间文件生成的时间?
                    outputPath_fc = pathParams.setOutputPath(staParam.staId, staParam.dataset, "ST",
                                                             taskDate - pd.to_timedelta(1, 'day'),
                                                             algorithm, version, checkpoint='noNONE')
                    delopymentPath = pathParams.setDeploymentPath(staParam.staId, staParam.staType, fcDataDateStart,
                                                                  fcDataDateEnd)

                    outputPathPattern = pathParams.returnOutputPath()
                    inputPathPattern = pathParams.returnInputPath()

                    dataLoaderInstance = dataLoader.CDataLoader(
                        meotoCachePaths=outputPathPattern['meteo'],
                        meotoOriginalCsvPaths=inputPath['meteo']['original'],
                        meotoBusinessCsvPaths=inputPath['meteo']['business'],
                        powerOriginalCsvPaths=outputPath_fc['power'],
                        powerBusinessCsvPaths=delopymentPath['power'],
                        logger=logger,
                        DataBase=initParams.database,
                        DataBaseURL=initParams.databaseURL,
                        DataBaseName=initParams.databaseName,
                        DataBasePort=initParams.databasePort,
                        DataBaseUser=initParams.databaseUser,
                        DataBasePassword=initParams.databasePassword)

                    if timeliness == "UST":
                        timeLinessEnum = TimeLiness.UST
                    elif timeliness == "ST":
                        timeLinessEnum = TimeLiness.ST
                    elif timeliness == "MT":
                        timeLinessEnum = TimeLiness.MT
                    elif timeliness == "SS":
                        timeLinessEnum = TimeLiness.SS
                    else:
                        raise RuntimeError("Invalid timeLiness")

                    staParamOne = staParam
                    staParamOne.algorithm = {algorithm: [version]}
                    staParamOne.timeLiness = [timeliness]
                    pattern = postget(staParamOne, timeLinessEnum, 'post', 'PostProcess', logger=logger)
                    patternLogger = lg.setTaskLogger(logFileFullPath=outputPath['log'], logLevel=initParams.logLevel)
                    for path in outputPath['log']:
                        messageQueueProducer.send_log(
                            staTaskId,
                            timeliness,
                            path
                        )

                    modelFileFlag = False
                    for i in range(len(outputPath['model'])):
                        try:
                            model = modelLoad.modelLoad(outputPath['model'][i],
                                                        outputPath['hash'][i],
                                                        outputPath['key'][i],
                                                        logger)
                            modelFileFlag = True
                        except Exception as e:
                            logger.warning(f"模型文件加载失败: {e}")
                    if not modelFileFlag:
                        raise ValueError(f"模型文件加载失败")

                    if timeliness == TimeLiness.UST.name:
                        minute = int(taskDate.minute / 15) * 15
                        # 超短期提前45分钟预报
                        fcTaskDate = taskDate.replace(minute=minute, second=0, microsecond=0)
                    elif timeliness == TimeLiness.ST.name:
                        fcTaskDate = taskDate.replace(hour=0, minute=0, second=0, microsecond=0)
                    elif timeliness == TimeLiness.MT.name:
                        fcTaskDate = taskDate.replace(hour=0, minute=0, second=0, microsecond=0)
                    elif timeliness == TimeLiness.SS.name:
                        fcTaskDate = taskDate.replace(hour=0, minute=0, second=0, microsecond=0)
                    else:
                        raise ValueError(f"时间尺度错误: {timeliness}")

                    try:
                        taskFcMeteoTime = taskDate.tz_convert('Asia/Shanghai').replace(hour=0, minute=0, second=0,
                                                                                       microsecond=0, nanosecond=0)
                        logger.info(f"尝试读取短期预测数据：{taskFcMeteoTime}")
                        Z = dataLoaderInstance.FCLoadPoint(
                            staId=staParam.staId,
                            staType=staParam.staType,
                            timelinessList=[timeliness],
                            timestart=taskFcMeteoTime,
                            timestop=taskFcMeteoTime,
                            logger=logger,
                            businessFlag=False,
                        )

                    except Exception as e:
                        try:
                            taskFcMeteoTime = taskFcMeteoTime - pd.Timedelta(1, 'd')
                            logger.error(f"尝试读取短期预测数据失败：{e}, 再次尝试: {taskFcMeteoTime}")
                            Z = dataLoaderInstance.FCLoadPoint(
                                staId=staParam.staId,
                                staType=staParam.staType,
                                timelinessList=[timeliness],
                                timestart=taskFcMeteoTime,
                                timestop=taskFcMeteoTime,
                                logger=logger,
                                businessFlag=False
                            )

                        except Exception as e:
                            logger.error(f"未能加载短期预测数据: {e}")

                    pattern.load(model, patternLogger)
                    # 预测
                    fcdata: pd.DataFrame = pattern.transform(Z, patternLogger=patternLogger)

                    # 预测结果检验
                    if 'time' not in fcdata.columns and fcdata.index.name != 'time':
                        raise ValueError(f"预测结果列缺失: time")
                    if 'power' not in fcdata.columns:
                        raise ValueError(f"预测结果列缺失: power")
                    if staParam.staType == "PV":
                        if 'radi' not in fcdata.columns:
                            raise ValueError(f"预测结果列缺失: radi, {fcdata.columns}")
                    elif staParam.staType == "WD":
                        if 'wind' not in fcdata.columns:
                            raise ValueError(f"预测结果列缺失: wind, {fcdata.columns}")

                    if staParam.staType == "PV":
                        for column in fcdata.columns:
                            errorFlag = False
                            if timeliness == TimeLiness.UST.name:
                                if column != 'power' and column != 'time' and column != 'radi': errorFlag = True
                            else:
                                if column != 'power' and column != 'time' and column != 'radi' and column != 'ghi_pw' and column != 'poa_pw': errorFlag = True
                            if errorFlag:
                                logger.warning(f"预测结果中存在异常列: {column}")
                                # raise ValueError(f"预测结果中存在异常列: {column}")
                    elif staParam.staType == "WD":
                        for column in fcdata.columns:
                            errorFlag = False
                            if column != 'power' and column != 'time' and column != 'wind': errorFlag = True
                            if errorFlag:
                                logger.warning(f"预测结果中存在异常列: {column}")
                                # raise ValueError(f"预测结果中存在异常列: {column}")

                    if timeliness == TimeLiness.UST.name:
                        countRight = TimeLinessFcHour.UST.value
                        fcDateStart = taskDate
                        minute = int(taskDate.minute / 15) * 15
                        # 超短期提前45分钟预报
                        fcDateStart = fcDateStart.replace(minute=minute, second=0, microsecond=0) + pd.Timedelta(
                            minutes=45)
                        fcDateEnd = fcDateStart + pd.Timedelta(minutes=15 * countRight * 4 - 1)
                    elif timeliness == TimeLiness.ST.name:
                        countRight = TimeLinessFcHour.ST.value
                        fcDateStart = taskDate.tz_convert('Asia/Shanghai')
                        fcDateStart = fcDateStart.replace(hour=0, minute=0, second=0, microsecond=0)
                        fcDateEnd = fcDateStart + pd.Timedelta(minutes=15 * countRight * 4 - 1)
                    elif timeliness == TimeLiness.MT.name:
                        countRight = TimeLinessFcHour.MT.value
                        fcDateStart = taskDate.tz_convert('Asia/Shanghai')
                        fcDateStart = fcDateStart.replace(hour=0, minute=0, second=0, microsecond=0)
                        fcDateEnd = fcDateStart + pd.Timedelta(minutes=15 * countRight * 4 - 1)
                    elif timeliness == TimeLiness.SS.name:
                        countRight = TimeLinessFcHour.SS.value
                        fcDateStart = taskDate.tz_convert('Asia/Shanghai')
                        fcDateStart = fcDateStart.replace(hour=0, minute=0, second=0, microsecond=0)
                        fcDateEnd = fcDateStart + pd.Timedelta(minutes=15 * countRight * 4 - 1)
                    else:
                        raise ValueError(f"时间尺度错误: {timeliness}")

                    count = fcdata.count()
                    if count[0] == 0:
                        logger.critical(f"预测结果为空: {staParam.staId}")
                    elif count[0] < countRight:
                        logger.critical(f"预测结果不完整: {staParam.staId}")
                    elif count[0] > countRight:
                        logger.warning(f"预测结果数据过多: {staParam.staId}")
                    else:
                        logger.info(f"预测结果完整: {staParam.staId} 校验时序是否完整")
                        fcTime = pd.date_range(start=fcDateStart, end=fcDateEnd, freq="15min")
                        if not fcTime.isin(fcdata.index).all():
                            logger.error(f"预测结果时序不完整: {staParam.staId}")
                        else:
                            logger.info(f"预测结果时序完整: {staParam.staId}")

                    # 预测结果保存
                    # TODO: Delete the following 2 lines to adapt to the official business
                    fcdata = fcdata[(fcdata.index >= fcDateStart) & (fcdata.index <= fcDateEnd)]
                    fcdata = fcdata.resample('15T').interpolate(method='linear')
                    for powerPath in outputPath['power']:
                        dataDump.powerDump(staTaskId, staParam.staId, fcdata, powerPath, timeliness, taskFcMeteoTime,
                                           logger)


def taskSinglePostHistoryForecast(
        staTaskId: str,
        initParams: pp.CParamsInit,
        taskParams: pp.CParamsTask,
        staParam: pp.CStaParams,
        pathParams: pp.CParamsPath,
        logger: lg.logging.Logger,
        messageQueueProducer: Cproducer):
    """执行单站点历史预测数据的后处理任务。
    
    该函数是历史预测后处理的主入口，负责：
    1. 调用 taskSinglePostForecast 执行标准的后处理流程
    2. 收集并合并指定时间范围内的历史预测结果
    3. 对历史预测数据进行汇总和分析
    
    支持的时间尺度：
    - UST (超短期): 15分钟间隔的超短期功率预测
    - ST (短期): 短期功率预测
    - MT (中期): 中期功率预测
    - SS (次季节预测): 次季节尺度功率预测
    
    参数
    ----------
    staTaskId : str
        站点任务ID，用于唯一标识当前历史预测后处理任务
    initParams : pp.CParamsInit
        初始化参数对象，包含：
        - database: 数据库连接信息
        - logLevel: 日志级别
        - 数据库认证信息（URL, 端口, 用户名, 密码等）
    taskParams : pp.CParamsTask
        任务参数对象，包含：
        - dateRange: 历史数据日期范围 [start_date, end_date]
        - 其他任务相关配置
    staParam : pp.CStaParams
        站点参数对象，包含：
        - staId: 站点ID
        - staType: 站点类型（PV/WD）
        - dataset: 使用的数据集列表
        - timeLiness: 时间尺度列表 ["UST", "ST", "MT", "SS"]
        - algorithm: 算法配置字典
    pathParams : pp.CParamsPath
        路径参数对象，用于构建：
        - 输入/输出路径
        - 模型文件路径
        - 日志文件路径
    logger : logging.Logger
        日志记录器实例，用于记录：
        - 任务开始/结束状态
        - 处理进度和指标
        - 警告和错误信息
    messageQueueProducer : Cproducer
        消息队列生产者实例，用于：
        - 发送任务执行状态更新
        - 记录处理结果路径
        - 报告处理异常
        
    返回
    -------
    None
        该函数不直接返回值，处理结果包括：
        - 合并后的历史预测数据
        - 处理日志
        
    异常
    ------
    ValueError
        - 当日期参数无效时
        - 当预测结果文件读取失败时
    RuntimeError
        - 当时间尺度配置无效时（非UST/ST/MT/SS）
    Exception
        - 当发生其他未处理的异常时
        
    注意事项
    --------
    1. 该函数会先调用 taskSinglePostForecast 执行标准的后处理流程
    2. 对于每个时间尺度和算法版本，会合并指定日期范围内的所有预测结果
    3. 合并后的数据按时间索引排序
    4. 对于UST时间尺度，时间会按15分钟间隔对齐
    """
    # 首先执行标准的后处理流程
    taskSinglePostForecast(staTaskId, initParams, taskParams, staParam, pathParams, logger, messageQueueProducer)

    Y = None
    for timeliness in staParam.timeLiness:
        for algorithm, versions in staParam.algorithm.items():
            for version in versions:
                fcDataDict = dict()
                if taskParams.dateRange[0] and taskParams.dateRange[1]:
                    if timeliness == "UST":
                        taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                                     freq="15min")
                    elif timeliness == "ST":
                        taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                                     freq="D")
                    elif timeliness == "MT":
                        taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                                     freq="D")
                    elif timeliness == "SS":
                        taskDateList = pd.date_range(start=taskParams.dateRange[0], end=taskParams.dateRange[1],
                                                     freq="D")
                    else:
                        raise RuntimeError("Invalid timeLiness")
                else:
                    raise ValueError("日期参数传输错误")

                if timeliness == "UST":
                    timeLinessEnum = TimeLiness.UST
                    timeLinessEnumFcHour = TimeLinessFcHour.UST
                elif timeliness == "ST":
                    timeLinessEnum = TimeLiness.ST
                    timeLinessEnumFcHour = TimeLinessFcHour.ST
                elif timeliness == "MT":
                    timeLinessEnum = TimeLiness.MT
                    timeLinessEnumFcHour = TimeLinessFcHour.MT
                elif timeliness == "SS":
                    timeLinessEnum = TimeLiness.SS
                    timeLinessEnumFcHour = TimeLinessFcHour.SS
                else:
                    raise RuntimeError("Invalid timeLiness")

                for taskDate in taskDateList:

                    taskDate = taskDate.replace(minute=int(taskDate.minute / 15) * 15)

                    outputPath = pathParams.setOutputPath(staParam.staId, staParam.dataset, timeliness, taskDate,
                                                          algorithm + "_post", version)
                    inputPath = pathParams.setInputPath(staParam.staId, staParam.dataset, timeliness, taskDate,
                                                        algorithm, version)
                    outputPathPattern = pathParams.returnOutputPath()
                    inputPathPattern = pathParams.returnInputPath()

                    for powerPath in outputPath['power']:
                        try:
                            fcDataSingle = pd.read_csv(powerPath, index_col='time')
                            fcDataSingle.index = pd.to_datetime(fcDataSingle.index)
                            fcDataDict.update({taskDate: fcDataSingle['power']})
                            break
                        except Exception as e:
                            logger.warning(f"读取 {powerPath} 文件错误: {e}")
                            continue
                    if Y is None:
                        # TODO: 这里需要优化, 数据读取应当支持更宽泛的自定义
                        dataLoaderInstance = dataLoader.CDataLoader(
                            meotoCachePaths=outputPathPattern['meteo'],
                            meotoOriginalCsvPaths=inputPathPattern['meteo']['original'],
                            meotoBusinessCsvPaths=inputPathPattern['meteo']['business'],
                            logger=logger,
                            DataBase=initParams.database,
                            DataBaseURL=initParams.databaseURL,
                            DataBaseName=initParams.databaseName,
                            DataBasePort=initParams.databasePort,
                            DataBaseUser=initParams.databaseUser,
                            DataBasePassword=initParams.databasePassword
                        )
                        # 加载观测数据
                        Y = dataLoaderInstance.OBSLoadPoint(staParam.staId, staParam.staType, None, taskDateList[0],
                                                            taskDateList[-1] + pd.Timedelta(
                                                                hours=timeLinessEnumFcHour.value),
                                                            logger)

                staParamOne = staParam
                staParamOne.algorithm = {algorithm: [version]}
                staParamOne.timeLiness = [timeliness]

                outputPath = pathParams.setOutputPath(staParam.staId, staParam.dataset, timeliness, taskDate,
                                                      algorithm + "_post", version)
                pattern = postget(staParamOne, timeLinessEnum, 'post', 'PostProcess', logger=logger)
                patternLogger = lg.setTaskLogger(logFileFullPath=outputPath['log'], logLevel=initParams.logLevel)
                for path in outputPath['log']:
                    messageQueueProducer.send_log(
                        staTaskId,
                        timeliness,
                        path
                    )

                acc = pd.DataFrame()
                acc['acc'] = pd.Series()
                acc['score'] = pd.Series()
                for detailEnum in staParam.accuracy:
                    detail = detailEnum.name
                    accModule = accuracy.__getattr__(detail)
                    accExecutor = accModule.__dict__[detail](staParam, logger=patternLogger)
                    obs = Y[staParam.staId]['power']

                    if timeliness == "UST":
                        accDicts: dict[str, float] = accExecutor.ust_day(fcDataDict, obs, patternLogger)
                    elif timeliness == "ST":
                        accDicts: dict[str, float] = accExecutor.st_day(fcDataDict, obs, patternLogger)
                    else:
                        raise NotImplementedError(f"acc calculate for timeliness {timeliness} not implemented!")

                    for taskDate, accDict in accDicts.items():
                        if acc['acc'].empty:
                            accDf = pd.DataFrame([[detail, accDict["acc"], accDict["score"]]],
                                                 columns=["detail", "acc", "score"], index=[taskDate])
                            accDf.fillna(-999, inplace=True)
                            accDf['start_time'] = taskDate
                            accDf["end_time"] = taskDate
                            acc = accDf
                        else:
                            accDf = pd.DataFrame([[detail, accDict["acc"], accDict["score"]]],
                                                 columns=["detail", "acc", "score"], index=[taskDate])
                            accDf.fillna(-999, inplace=True)
                            accDf['start_time'] = taskDate
                            accDf["end_time"] = taskDate
                            acc = pd.concat([acc, accDf])

                        acc.index.name = 'Datetime'
                        acc['sta_id'] = staParam.staId
                        acc['sta_type'] = staParam.staType
                        acc['algorithm'] = algorithm
                        acc['version'] = version

                acc = acc[
                    ['sta_id', 'sta_type', 'start_time', 'end_time', 'algorithm', 'version', 'detail', 'acc', 'score']]
                taskDateList = acc['start_time'].unique()  # 根据逐日的时效设置taskDateList
                for taskDate in acc['start_time'].unique():
                    accPaths = \
                        pathParams.setOutputPath(staParam.staId, staParam.dataset, timeliness, taskDate, algorithm,
                                                 version)['acc']
                    if 'acc' not in locals():
                        raise ValueError("acc not calculated!")
                    else:
                        accSingle = acc[acc.index == taskDate]
                        for accPath in accPaths:
                            dataDump.accDump(staTaskId, accSingle, timeliness, accPath, logger, messageQueueProducer)

    accDict = dict()
    for timeliness in staParam.timeLiness:
        for algorithm, versions in staParam.algorithm.items():
            for version in versions:
                if version != "last":
                    raise NotImplementedError("version not last, not implemented! Now only support last!")
                accDf = pd.DataFrame()

                for taskDate in taskDateList:
                    accPaths = \
                        pathParams.setOutputPath(staParam.staId, staParam.dataset, timeliness, taskDate, algorithm,
                                                 version)['acc']
                    for accPath in accPaths:
                        try:
                            acc = pd.read_csv(accPath)

                            break
                        except Exception as e:
                            logger.error(f"读取文件失败: {accPath}, 错误信息: {e}")
                            continue
                    if accDf.empty:
                        accDf = acc
                    else:
                        accDf = pd.concat([accDf, acc])
                accDf.reset_index(drop=True, inplace=True)
                accDfGroup = accDf.groupby(["algorithm", "version", "detail"])
                for key, group in accDfGroup:
                    detail = key[2]
                    accMean = group['acc'].mean()
                    scoreMean = group['score'].mean()
                    # 确保timeliness存在
                    if timeliness not in accDict:
                        accDict[timeliness] = {}

                    # 确保algorithm存在
                    if algorithm not in accDict[timeliness]:
                        accDict[timeliness][algorithm] = {}

                    # 更新或添加version的数据
                    accDict[timeliness][algorithm] = {
                        'acc': accMean,
                        'score': scoreMean
                    }

    for timeliness in staParam.timeLiness:
        # 将算法按照acc值排序 TODO: 优化支持多版本排序
        sorted_algorithms = sorted(accDict[timeliness].items(), key=lambda x: x[1]["acc"], reverse=True)
        # 更新order值
        for order, (algorithm, _) in enumerate(sorted_algorithms):
            accDict[timeliness][algorithm]["order"] = order + 1
        messageQueueProducer.send_pick_best_algorithm(staTaskId, timeliness, accDict[timeliness])


def taskSinglePostTrain(staTaskId: str, checkpoint: str, initParams: pp.CParamsInit, taskParams: pp.CParamsTask, staParam: pp.CStaParams,
        pathParams: pp.CParamsPath, logger, messageQueueProducer: Cproducer):
    """执行单站点后处理模型的训练任务。
    
    该函数负责训练后处理模型，用于对预测结果进行后处理，主要功能包括：
    1. 加载观测数据和预测数据
    2. 初始化后处理模型
    3. 训练后处理模型
    4. 保存训练好的后处理模型
    
    支持的时间尺度：
    - UST (超短期): 15分钟间隔的超短期功率预测
    - ST (短期): 短期功率预测
    - MT (中期): 中期功率预测
    - SS (次季节预测): 次季节尺度功率预测
    
    参数
    ----------
    staTaskId : str
        站点任务ID，用于唯一标识当前训练任务
    checkpoint : str
        检查点标识，用于模型版本控制
    initParams : pp.CParamsInit
        初始化参数对象，包含：
        - database: 数据库连接信息
        - logLevel: 日志级别
        - 数据库认证信息（URL, 端口, 用户名, 密码等）
    taskParams : pp.CParamsTask
        任务参数对象，包含：
        - dateRange: 训练数据日期范围 [start_date, end_date]
        - 其他任务相关配置
    staParam : pp.CStaParams
        站点参数对象，包含：
        - staId: 站点ID
        - staType: 站点类型（PV/WD）
        - dataset: 使用的数据集列表
        - timeLiness: 时间尺度列表 ["UST", "ST", "MT", "SS"]
        - algorithm: 算法配置字典
    pathParams : pp.CParamsPath
        路径参数对象，用于构建：
        - 模型保存路径
        - 日志文件路径
        - 中间数据缓存路径
    logger : logging.Logger
        日志记录器实例，用于记录：
        - 任务开始/结束状态
        - 训练进度和指标
        - 警告和错误信息
    messageQueueProducer : Cproducer
        消息队列生产者实例，用于：
        - 发送任务执行状态更新
        - 记录模型保存路径
        - 报告训练异常
        
    异常
    ------
    ValueError
        - 当日期参数无效时
        - 当数据加载失败时
    RuntimeError
        - 当时间尺度配置无效时（非UST/ST/MT/SS）
    Exception
        - 当发生其他未处理的异常时
        
    注意事项
    --------
    1. 训练过程会从最新的检查点恢复（如果存在）
    2. 训练完成后会保存模型文件、哈希文件和密钥文件
    3. 训练日志会保存到指定路径
    """
    # 训练超短期无需每15分钟都训练
    if taskParams.dateRange[0] and taskParams.dateRange[1]:
        taskDateStart = taskParams.dateRange[0]
        taskDateEnd = taskParams.dateRange[1]
    else:
        raise ValueError("日期参数传输错误")

    for timeLiness in staParam.timeLiness:
        for algorithm, versions in staParam.algorithm.items():
            for version in versions:

                try:
                    logger.info(f"站点: {staParam.staId} 时效: {timeLiness} 算法: {algorithm} 版本: {version}")

                    # 生成输出路径, 其中日期无用，模型路径无需日期
                    outputPath = pathParams.setOutputPath(staParam.staId, staParam.dataset, timeLiness,
                                                          pd.Timestamp.utcnow(),
                                                          algorithm, version, checkpoint)

                    outputPathPattern = pathParams.returnOutputPath()
                    inputPathPattern  = pathParams.returnInputPath()
                    delopymentPattern = pathParams.returnDeploymentPath()

                    modelPath = outputPath['model']
                    hashPath = outputPath['hash']
                    keyPath = outputPath['key']

                    pklList = []
                    for modelPath in outputPath['model']:
                        modelDir = os.path.dirname(modelPath)
                        fileList = glob.glob(fr'{modelDir}/*.pkl')
                        for x in fileList:
                            if x.endswith('.pkl'):
                                pklList.append(os.path.basename(x))
                    pklList = sorted(pklList)
                    pklTimestampStr = pklList[-1].split('.')[0]
                    pklTimestamp = pd.to_datetime(pklTimestampStr, format='%Y%m%d%H%M%S', utc=True)

                    dataLoaderInstance = dataLoader.CDataLoader(
                        meotoCachePaths=outputPathPattern['meteo'],
                        meotoOriginalCsvPaths=inputPathPattern['meteo']['original'],
                        meotoBusinessCsvPaths=inputPathPattern['meteo']['business'],
                        powerOriginalCsvPaths=outputPathPattern['power'],
                        powerBusinessCsvPaths=delopymentPattern['power'],
                        logger=logger,
                        DataBase=initParams.database,
                        DataBaseURL=initParams.databaseURL,
                        DataBaseName=initParams.databaseName,
                        DataBasePort=initParams.databasePort,
                        DataBaseUser=initParams.databaseUser,
                        DataBasePassword=initParams.databasePassword
                    )

                    Y = dataLoaderInstance.OBSLoadPoint(staParam.staId, staParam.staType, "power", None, None, logger)
                    YDateStart = Y[staParam.staId]["power"].index[0]
                    YDateEnd = Y[staParam.staId]["power"].index[-1]

                    for _staId, _var in Y.items():
                        for _varName, _df in _var.items():
                            _df = _df[_df.index >= pklTimestamp]
                            Y[_staId][_varName] = _df

                    YDateStart = Y[staParam.staId]["power"].index[0].ceil("D").replace(hour=16)

                    taskMeteoTimeStart = YDateStart.replace(minute=0)
                    taskMeteoTimeEnd = YDateEnd.replace(minute=0)
                    taskMeteoTimeStart = taskMeteoTimeStart.tz_convert("Asia/Shanghai")
                    taskMeteoTimeEnd = taskMeteoTimeEnd.tz_convert("Asia/Shanghai")
                    X = dataLoaderInstance.FCLoadPoint(staId=staParam.staId,
                                                       staType=staParam.staType,
                                                       timelinessList=[timeLiness],
                                                       timestart=taskMeteoTimeStart,
                                                       timestop=taskMeteoTimeEnd,
                                                       businessFlag=True,
                                                       logger=logger,
                                                       algoName=algorithm,)

                    if timeLiness == "UST":
                        timeLinessEnum = TimeLiness.UST
                    elif timeLiness == "ST":
                        timeLinessEnum = TimeLiness.ST
                    elif timeLiness == "MT":
                        timeLinessEnum = TimeLiness.MT
                    elif timeLiness == "SS":
                        timeLinessEnum = TimeLiness.SS
                    else:
                        raise RuntimeError("Invalid timeLiness")

                    staParamOne = staParam
                    staParamOne.algorithm = {algorithm: [version]}
                    staParamOne.timeLiness = [timeLiness]
                    pattern = postget(staParamOne, timeLinessEnum, "post", 'PostProcess', logger=logger)
                    patternLogger = lg.setTaskLogger(logFileFullPath=outputPath['log'], logLevel=initParams.logLevel)
                    for path in outputPath['log']:
                        messageQueueProducer.send_log(
                            staTaskId,
                            timeLiness,
                            path
                        )

                    model = pattern.fit(X, Y, patternLogger)

                    # 生成输出路径, 其中日期无用，模型路径无需日期
                    outputPath = pathParams.setOutputPath(staParam.staId, staParam.dataset, timeLiness,
                                                          pd.Timestamp.utcnow(),
                                                          algorithm + "_post", version, checkpoint)
                    modelPath = outputPath['model']
                    hashPath = outputPath['hash']
                    keyPath = outputPath['key']

                    for i in range(len(modelPath)):
                        modelDump.modelDump(staTaskId, model, timeLiness, modelPath[i], hashPath[i], keyPath[i],
                                            logger, messageQueueProducer)

                except Exception as e:

                    logging.error(f"{e} {traceback.format_exc()}")

                    logger.info(f"站点: {staParam.staId} 时效: {timeLiness} 算法: {algorithm} 版本: {version}")

                    # 生成输出路径, 其中日期无用，模型路径无需日期
                    outputPath = pathParams.setOutputPath(staParam.staId, staParam.dataset, timeLiness,
                                                          pd.Timestamp.utcnow(),
                                                          algorithm, version, checkpoint)
                    patternLogger = lg.setTaskLogger(logFileFullPath=outputPath['log'], logLevel=initParams.logLevel)
                    staParamOne = staParam
                    staParamOne.algorithm = {algorithm: [version]}
                    staParamOne.timeLiness = [timeLiness]
                    if timeLiness == "UST":
                        timeLinessEnum = TimeLiness.UST
                    elif timeLiness == "ST":
                        timeLinessEnum = TimeLiness.ST
                    elif timeLiness == "MT":
                        timeLinessEnum = TimeLiness.MT
                    elif timeLiness == "SS":
                        timeLinessEnum = TimeLiness.SS
                    else:
                        raise RuntimeError("Invalid timeLiness")
                    pattern = postget(staParamOne, timeLinessEnum, "post", 'PostProcess', logger=logger)
                    model = pattern.fit(None, None, patternLogger)
                    # 生成输出路径, 其中日期无用，模型路径无需日期
                    outputPath = pathParams.setOutputPath(staParam.staId, staParam.dataset, timeLiness,
                                                          pd.Timestamp.utcnow(),
                                                          algorithm + "_post", version, checkpoint)
                    modelPath = outputPath['model']
                    hashPath = outputPath['hash']
                    keyPath = outputPath['key']

                    for i in range(len(modelPath)):
                        modelDump.modelDump(staTaskId, model, timeLiness, modelPath[i], hashPath[i], keyPath[i],
                                            logger, messageQueueProducer)


def taskDeal(params: pp.CParams, logger: logging.Logger, messageQueueProducer: Cproducer) -> Union[None, str]:
    """根据任务类型和参数分发并执行相应的任务。
    
    该函数是任务执行的主入口，负责根据任务类型和配置参数将任务分发给具体的处理函数执行。
    支持单站点任务（区域任务暂未实现）。根据配置决定是否使用Ray分布式计算框架。
    
    支持的任务类型：
    - FC: 普通预测任务
    - RFC: 实时预测任务
    - HFC: 历史预测任务
    - FT: 全量训练任务
    - UPT: 更新训练任务
    - PFC: 后处理预测任务
    - PT: 后处理训练任务
    - PHFC: 后处理历史预测任务

    参数
    ----------
    params : pp.CParams
        任务参数对象，包含以下主要属性：
        - task: 任务参数对象，包含：
            - taskType: 任务类型 (FC/RFC/HFC/FT/UPT/PFC/PT/PHFC)
            - staListType: 站点列表类型 (single/area)
        - init: 初始化参数对象，包含：
            - ray: 是否使用Ray分布式计算
            - logLevel: 日志级别
        - staParams: 站点参数字典，key为站点ID，value为站点参数对象
        - path: 路径参数对象，用于构建输入输出路径
    logger : logging.Logger
        日志记录器实例，用于记录：
        - 任务开始/结束状态
        - 执行过程中的关键信息
        - 警告和错误信息
    messageQueueProducer : Cproducer
        消息队列生产者实例，用于：
        - 发送任务执行状态更新
        - 记录任务执行结果
        - 报告任务异常

    返回
    -------
    Union[None, str]
        - 如果任务类型为训练任务(FT/UPT/PT)，返回检查点(checkpoint)字符串，格式为"YYYYMMDDHHMMSS"
        - 其他任务类型返回None

    异常
    ------
    ValueError
        - 当任务参数无效时
    NotImplementedError
        - 当尝试执行未实现的功能（如区域任务）时
    RuntimeError
        - 当任务执行过程中发生运行时错误时
    Exception
        - 当发生其他未处理的异常时

    注意事项
    --------
    1. 任务执行模式：
       - 单站点任务 (single): 支持，串行执行每个站点的任务
       - 区域任务 (area): 暂未实现
    
    2. 分布式计算：
       - 支持通过Ray框架进行分布式计算
       - 可通过init.ray配置项启用/禁用
       - 启用时，每个任务会提交到Ray集群异步执行
    
    3. 检查点机制：
       - 训练任务(FT/UPT/PT)会生成唯一的时间戳作为检查点
       - 检查点格式: YYYYMMDDHHMMSS
       - 用于模型版本控制和结果追踪
    
    4. 日志记录：
       - 记录任务开始/结束状态
       - 记录任务执行过程中的关键信息
       - 记录警告和错误信息
    
    5. 消息队列：
       - 用于任务状态更新和结果通知
       - 支持异步通知机制

    示例
    --------
    >>> from task import taskDeal
    >>> import logging
    >>> from message import Cproducer
    >>>
    >>> # 初始化参数
    >>> params = pp.CParams()  # 使用默认参数初始化
    >>> params.task.taskType = "FC"  # 设置任务类型为预测任务
    >>> params.task.staListType = "single"  # 设置站点列表类型为单站点
    >>> params.init.ray = True  # 启用Ray分布式计算
    >>>
    >>> # 初始化日志记录器
    >>> logger = logging.getLogger(__name__)
    >>> logger.setLevel(logging.INFO)
    >>>
    >>> # 初始化消息队列生产者
    >>> producer = Cproducer()
    >>>
    >>> # 执行任务
    >>> result = taskDeal(params, logger, producer)
    >>> if result is not None:
    ...     print(f"训练任务完成，检查点: {result}")
    ... else:
    ...     print("预测任务执行完成")
    """
    checkpoint = None

    # 根据任务列表类型执行相应的任务处理逻辑
    if params.task.staListType == "single":
        # 遍历每个站点参数，执行单个任务
        for staTaskId, staParam in params.staParams.items():
            # 根据任务类型执行相应的任务
            if params.task.taskType == TaskType.FC or params.task.taskType == TaskType.RFC:
                # 执行预测任务，根据是否使用Ray集群选择不同的执行方式
                if params.init.ray:
                    logger.info(f"执行 {TaskType(params.task.taskType).name} 预测任务: {staTaskId} 伴随 Ray 集群")
                    taskSingleForecastRemote.remote(staTaskId, params.init, params.task, staParam, params.path, logger,
                                                    messageQueueProducer).options(num_cpus=1)
                else:
                    logger.info(f"执行 {TaskType(params.task.taskType).name} 预测任务: {staTaskId} 不伴随 Ray 集群")
                    taskSingleForecast(staTaskId, params.init, params.task, staParam, params.path, logger,
                                       messageQueueProducer)
            elif params.task.taskType == TaskType.HFC:
                # 执行历史预测任务，根据是否使用Ray集群选择不同的执行方式
                if params.init.ray:
                    logger.info(f"执行 {TaskType(params.task.taskType).name} 预测任务: {staTaskId} 伴随 Ray 集群")
                    taskSingleHistryForecastRemote.remote(staTaskId, params.init, params.task, staParam, params.path,
                                                          logger, messageQueueProducer).options(num_cpus=1)
                else:
                    logger.info(f"执行 {TaskType(params.task.taskType).name} 预测任务: {staTaskId} 不伴随 Ray 集群")
                    taskSingleHistryForecast(staTaskId, params.init, params.task, staParam, params.path, logger,
                                             messageQueueProducer)
            elif params.task.taskType == TaskType.FT or params.task.taskType == TaskType.UPT:
                # 执行训练任务，生成检查点，根据是否使用Ray集群选择不同的执行方式
                checkpoint = pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
                if params.init.ray:
                    logger.info(f"执行 {TaskType(params.task.taskType).name} 训练任务: {staTaskId} 伴随 Ray 集群")
                    taskSingleTrainRemote.remote(staTaskId, checkpoint, params.init, params.task, staParam, params.path, logger,
                                                 messageQueueProducer).options(num_cpus=1)
                else:
                    logger.info(f"执行训练任务: {staTaskId} 不伴随 Ray 集群")
                    taskSingleTrain(staTaskId, checkpoint, params.init, params.task, staParam, params.path, logger,
                                    messageQueueProducer)
            elif params.task.taskType == TaskType.PFC:
                # 执行预测任务，根据是否使用Ray集群选择不同的执行方式
                if params.init.ray:
                    logger.info(f"执行 {TaskType(params.task.taskType).name} 回算预测任务: {staTaskId} 伴随 Ray 集群")
                    taskSinglePostForecast.remote(staTaskId, params.init, params.task, staParam, params.path, logger,
                                                    messageQueueProducer).options(num_cpus=1)
                else:
                    logger.info(f"执行 {TaskType(params.task.taskType).name} 回算预测任务: {staTaskId} 不伴随 Ray 集群")
                    taskSinglePostForecast(staTaskId, params.init, params.task, staParam, params.path, logger,
                                       messageQueueProducer)
            elif params.task.taskType == TaskType.PT:
                # 执行训练任务，生成检查点，根据是否使用Ray集群选择不同的执行方式
                checkpoint = pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
                if params.init.ray:
                    logger.info(f"执行 {TaskType(params.task.taskType).name} 训练任务: {staTaskId} 伴随 Ray 集群")
                    taskSinglePostTrain.remote(staTaskId, checkpoint, params.init, params.task, staParam, params.path, logger,
                                                 messageQueueProducer).options(num_cpus=1)
                else:
                    logger.info(f"执行训练任务: {staTaskId} 不伴随 Ray 集群")
                    taskSinglePostTrain(staTaskId, checkpoint, params.init, params.task, staParam, params.path, logger,
                                    messageQueueProducer)
            elif params.task.taskType == TaskType.PHFC:
                # 执行历史预测任务，根据是否使用Ray集群选择不同的执行方式
                if params.init.ray:
                    logger.info(f"执行 {TaskType(params.task.taskType).name} 预测任务: {staTaskId} 伴随 Ray 集群")
                    taskSinglePostHistoryForecast.remote(staTaskId, params.init, params.task, staParam, params.path,
                                                          logger, messageQueueProducer).options(num_cpus=1)
                else:
                    logger.info(f"执行 {TaskType(params.task.taskType).name} 预测任务: {staTaskId} 不伴随 Ray 集群")
                    taskSinglePostHistoryForecast(staTaskId, params.init, params.task, staParam, params.path, logger,
                                             messageQueueProducer)
            else:
                # 如果任务类型不匹配，抛出异常
                logger.error(f"不支持的任务类型: {params.task.taskType}")
                raise Exception("taskType error")

    elif params.task.staListType == "area":
        raise NotImplementedError("区域任务未实现")
    else:
        raise Exception("taskType error")

    # 返回检查点，如果任务类型是训练任务，则返回生成的检查点，否则返回None
    return checkpoint
