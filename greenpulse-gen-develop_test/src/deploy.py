"""部署模块

本模块负责将预测结果、模型和评估指标部署到指定位置。支持多种部署目标，包括文件系统、数据库和消息队列。

主要功能
--------
- 气象数据部署 (deployMeteo): 处理气象数据的格式转换和部署
- 功率数据部署 (deployPower): 处理功率预测数据的格式转换和部署
- 精度评估结果部署 (deployAcc): 处理模型评估结果的部署
- 模型部署 (deployModel): 处理模型文件和哈希校验的部署
- 统一部署接口 (deploy): 提供统一的部署入口，支持断点续传

模块函数
--------
deployMeteo(staTaskId, staType, timeliness, outputPaths, deployPaths, logger, messageQueueProducer)
   部署气象数据到指定位置，支持 PV 和 WD 两种站点类型。

deployPower(staTaskId, staType, taskDate, timeliness, outputPaths, deployPaths, logger, messageQueueProducer)
   部署功率预测数据到指定位置，支持多种时间尺度。

deployAcc(staTaskId, taskDate, timeliness, outputPaths, deployPaths, logger, messageQueueProducer)
   部署精度评估结果到指定位置。

deployModel(staTaskId, taskDate, timeliness, outputPaths, deployPaths, logger, messageQueueProducer)
   部署模型文件到指定位置，包含模型文件和哈希校验。

deploy(params, checkpoint, logger, messageQueueProducer)
   统一部署入口函数，根据参数配置调度不同类型的部署任务。

时间尺度定义
------------
- UST: 超短期预测 (Ultra Short Term)
- ST: 短期预测 (Short Term)
- MT: 中期预测 (Medium Term)
- SS: 次季节预测 (Sub-Seasonal)

站点类型
--------
- PV: 光伏电站
- WD: 风力电站

示例
----
基本用法:

```python
from src import params, deploy, logger
from src.message import CNullKafkaProducer
import pandas as pd

# 初始化日志和消息队列
logger = logger.setup_logger('deploy')
producer = CNullKafkaProducer()

# 加载配置文件
config_path = 'config.yaml'
params = params.CParams(config_path)

# 执行部署
deploy.deploy(
    params=params,
    checkpoint=None,  # 断点续传时间戳
    logger=logger,
    messageQueueProducer=producer
)
```

注意事项
--------
1. 所有时间戳均使用 UTC 时区
2. 部署前会自动创建必要的目录结构
3. 支持断点续传功能，通过 checkpoint 参数控制
4. 部署结果会通过消息队列发送状态更新

"""

from operator import index
import os
import logging
import traceback
import pandas as pd
import numpy as np
from typing import Union, Optional, Dict, List

from . import params as pp
from . import message as mq
from .config import TypeDefine
from .datasets import dataDump

def deployMeteo(
    staTaskId: str,
    staType: str,
    timeliness: str,
    outputPaths: Dict[str, List[str]],
    deployPaths: Dict[str, List[str]],
    logger: logging.Logger,
    messageQueueProducer: Union[mq.Cproducer, mq.CNullKafkaProducer]
) -> None:
    """部署气象数据到指定位置，支持 PV 和 WD 两种站点类型。

    将气象预测数据从输出路径复制到部署路径，并进行必要的格式转换。支持的数据处理包括：
    - 时间列处理：自动识别并转换时间列为 UTC+8 时区
    - 数据重采样：将数据重采样为 15 分钟间隔
    - 气象要素重命名：将标准气象要素名称映射为系统内部名称
    - 站点特定处理：根据站点类型(PV/WD)进行特定处理

    Parameters
    ----------
    staTaskId : str
        站点任务ID，用于标识当前部署任务
    staType : str
        站点类型，支持以下值：
        - 'PV': 光伏电站
        - 'WD': 风力电站
    timeliness : str
        预测时效，支持以下值：
        - 'UST': 超短期预测
        - 'ST': 短期预测
        - 'MT': 中期预测
        - 'SS': 次季节预测
    outputPaths : Dict[str, List[str]]
        包含输出文件路径的字典，必须包含 'meteo' 键，值为气象数据文件路径列表
    deployPaths : Dict[str, List[str]]
        包含部署路径的字典，必须包含 'meteo' 键，值为目标文件路径列表
    logger : logging.Logger
        日志记录器，用于记录处理过程中的信息
    messageQueueProducer : Union[mq.Cproducer, mq.CNullKafkaProducer]
        消息队列生产者，用于发送部署状态和结果

    Raises
    ------
    FileNotFoundError
        当输入的气象数据文件不存在时抛出
    ValueError
        当数据格式不正确或缺少必要列时抛出
    KeyError
        当输入参数中缺少必要的键时抛出

    Notes
    -----
    1. 输入数据要求：
       - 必须包含 'time' 列或索引
       - 时间列应为 UTC 时间
       - 必须包含标准气象要素列

    2. 输出数据格式：
       - 时间索引为 UTC+8 时区
       - 时间分辨率为 15 分钟
       - 气象要素名称已转换为系统内部标准名称

    3. 对于风力电站(WD)，会自动扩展以下高度层的气象要素：
       - 风速(wind_spd)和风向(wind_dir): 10m, 20m, 30m, 50m, 70m, 80m, 100m, 120m, 150m
       - 温度(tem): 10m, 20m, 30m, 50m, 70m, 80m, 100m, 120m, 150m
       - 湿度(hum): 10m, 20m, 30m, 50m, 70m, 80m, 100m, 120m, 150m
       - 气压(pressure): 10m, 20m, 30m, 50m, 70m, 80m, 100m, 120m, 150m

    Examples
    --------
    >>> from src import logger, message
    >>> import os
    >>>
    >>> # 初始化日志和消息队列
    >>> logger = logger.setup_logger('deploy_meteo')
    >>> producer = message.CNullKafkaProducer()
    >>>
    >>> # 配置输入输出路径
    >>> output_paths = {
    ...     'meteo': ['/data/output/1000000000000001/meteo_202305010000.csv']
    ... }
    >>> deploy_paths = {
    ...     'meteo': ['/deploy/1000000000000001/meteo_202305010000.csv']
    ... }
    >>>
    >>> # 执行部署
    >>> deployMeteo(
    ...     staTaskId='1000000000000001',
    ...     staType='PV',
    ...     timeliness='UST',
    ...     outputPaths=output_paths,
    ...     deployPaths=deploy_paths,
    ...     logger=logger,
    ...     messageQueueProducer=producer
    ... )

    See Also
    --------
    dataDump.meteoDump : 实际执行气象数据转储的函数
    """
    fileFlag = False
    for outputPath in outputPaths['meteo']:
        try:
            dataMeteo = pd.read_csv(outputPath, index_col='time')
            fileFlag = True
        except Exception as e:
            logger.warning(f"读取文件失败: {outputPath}")
            logger.warning(e)
            continue
    if not fileFlag:
        raise FileNotFoundError(f"部署气象文件不存在")

    for deployPath in deployPaths['meteo']:
        try:
            # 将时间转换为 UTC 时间
            if "time" in dataMeteo.columns:
                dataMeteo['time'] = pd.to_datetime(dataMeteo['time'])
                # 本地预测时
                dataMeteo['time'] = dataMeteo['time'].dt.tz_convert('Asia/Shanghai')
                dataMeteo['time'] = dataMeteo['time'].dt.tz_localize(None)
            elif dataMeteo.index.name == "time":
                dataMeteo.index = pd.to_datetime(dataMeteo.index)
                # 本地预测时
                dataMeteo.index = dataMeteo.index.tz_convert('Asia/Shanghai')
                dataMeteo.index = dataMeteo.index.tz_localize(None)
            else:
                logger.warning(f"列名: {dataMeteo.columns}")
                logger.warning(f"索引: {dataMeteo.index.name}")
                raise ValueError("时间列名错误")

            # 气象要素插值到 15 分钟
            dataMeteo = dataMeteo.resample('15min').interpolate(method='time')
            dataMeteo = dataMeteo.drop(index=dataMeteo.index[-1])
            # 截取本地预测时效
            fileName = deployPath.split('/')[-1].split('.')[0]
            localTimeStart = fileName.split('_')[-2]
            localTimeStart = pd.to_datetime(localTimeStart)
            dataMeteo = dataMeteo[dataMeteo.index >= localTimeStart]

            # 读取起报时间并遗弃起报时间列
            departureTime = pd.to_datetime(dataMeteo['departureTime'].iloc[0])
            dataMeteo = dataMeteo.drop(columns="departureTime")

            # TODO: 需要改为自定义项
            dataMeteo = dataMeteo.rename(columns={"sp": "pressure", "tcc": "cloud", "win10_spd": "wind_spd_10", "win10_dir": "wind_dir_10", "rhu": "hum", "t2": "tem", "tp": "pre", "ghi": "radi", "dni": "dni", "dhi": "dhi"})
            dataMeteo = dataMeteo.loc[:, ["cloud","pre","wind_spd_10","wind_dir_10","hum","pressure","tem","radi","dni","dhi"]]

            # TODO: 后续不同数据云量范围不同，需要修改
            dataMeteo["cloud"] = dataMeteo["cloud"] * 100
            dataMeteo["layer"] = 0

            dataMeteoAtLev0 = dataMeteo.copy()

            if staType == "WD":

                def compute_friction_velocity(u10, z0=0.02, d=0.0, z_ref=10.0, kappa=0.4):
                    """
                    根据10米风速、粗糙长度计算摩擦速度 u*
                    """
                    return kappa * u10 / np.log((z_ref - d) / z0)
                def wind_profile(z, u10, z0=0.02, d=0.0, kappa=0.4):
                    """
                    根据对数风速剖面计算任意高度 z 的风速 u(z)
                    """
                    u_star = compute_friction_velocity(u10, z0, d, kappa=kappa)
                    return (u_star / kappa) * np.log((z - d) / z0)
                def ekman_spiral_direction(z, theta10_deg, theta_max=25, hs=175):
                    """
                    Ekman螺旋经验模型：返回z高度处的风向（度）

                    参数：
                        z : float or np.array
                            高度（m）
                        theta10_deg : float
                            10米风向（度，来自方向，如180为南风）
                        theta_max : float
                            最大偏转角（通常取20-30°）
                        hs : float
                            Ekman 层特征厚度（通常为150–200m）

                    返回：
                        theta(z)：z处的风向（度）
                    """
                    delta_theta = theta_max * (1 - np.exp(-z / hs))
                    return theta10_deg + delta_theta

                for layer in range(10, 151, 10):
                    # TODO 该处需要适配真实物理约束
                    _dataMeteo = dataMeteoAtLev0.copy()
                    _dataMeteo["layer"] = layer
                    _dataMeteo["wind_spd_10"] = wind_profile(layer, dataMeteo.loc[dataMeteo["layer"] == 0, ["wind_spd_10"]])
                    _dataMeteo["wind_dir_10"] = ekman_spiral_direction(layer, dataMeteo.loc[dataMeteo["layer"] == 0, ["wind_dir_10"]])
                    _dataMeteo["hum"] = dataMeteo.loc[dataMeteo["layer"] == 0, ["hum"]]
                    _dataMeteo["pressure"] = dataMeteo.loc[dataMeteo["layer"] == 0, ["pressure"]]
                    _dataMeteo.loc[:, ["cloud","pre","radi","dni","dhi"]] = -999
                    dataMeteo = pd.concat([dataMeteo, _dataMeteo])


            dataDump.meteoDump(staTaskId, staType, dataMeteo, timeliness, deployPath, departureTime, logger, messageQueueProducer)
        except Exception as e:
            logger.warning(f"部署文件发生意外: {deployPath} {e}")
            logger.warning(traceback.format_exc())
            continue


def deployPower(
    staTaskId: str,
    staType: str,
    taskDate: pd.Timestamp,
    timeliness: str,
    outputPaths: Dict[str, List[str]],
    deployPaths: Dict[str, List[str]],
    logger: logging.Logger,
    messageQueueProducer: Union[mq.Cproducer, mq.CNullKafkaProducer],
    algorithm: Union[str, None] = None
) -> None:
    """部署功率预测数据到指定位置，支持 PV 和 WD 两种站点类型。

    将功率预测数据从输出路径复制到部署路径，并进行必要的格式转换。主要功能包括：
    - 读取并验证输入功率数据文件
    - 处理时间列，确保时区正确性
    - 重采样数据到 15 分钟间隔
    - 根据站点类型进行特定处理
    - 通过消息队列发送部署状态

    Parameters
    ----------
    staTaskId : str
        站点任务ID，用于标识当前部署任务
    staType : str
        站点类型，支持以下值：
        - 'PV': 光伏电站
        - 'WD': 风力电站
    taskDate : pd.Timestamp
        任务日期，用于数据验证和处理
    timeliness : str
        预测时效，支持以下值：
        - 'UST': 超短期预测
        - 'ST': 短期预测
        - 'MT': 中期预测
        - 'SS': 次季节预测
    outputPaths : Dict[str, List[str]]
        包含输出文件路径的字典，必须包含 'power' 键，值为功率数据文件路径列表
    deployPaths : Dict[str, List[str]]
        包含部署路径的字典，必须包含 'power' 键，值为目标文件路径列表
    logger : logging.Logger
        日志记录器，用于记录处理过程中的信息
    messageQueueProducer : Union[mq.Cproducer, mq.CNullKafkaProducer]
        消息队列生产者，用于发送部署状态和结果

    Raises
    ------
    FileNotFoundError
        当输入的功率数据文件不存在时抛出
    ValueError
        当数据格式不正确或缺少必要列时抛出
    KeyError
        当输入参数中缺少必要的键时抛出

    Notes
    -----
    1. 输入数据要求：
       - 必须包含 'time' 列或索引
       - 时间列应为 UTC 时间
       - 必须包含功率预测数据列

    2. 输出数据格式：
       - 时间索引为 UTC+8 时区
       - 时间分辨率为 15 分钟
       - 功率单位统一为 kW

    3. 特殊处理：
       - 对于光伏电站(PV)，会进行辐照度到功率的转换
       - 对于风力电站(WD)，会进行风速到功率的转换

    Examples
    --------
    >>> from src import logger, message
    >>> import pandas as pd
    >>>
    >>> # 初始化日志和消息队列
    >>> logger = logger.setup_logger('deploy_power')
    >>> producer = message.CNullKafkaProducer()
    >>>
    >>> # 配置输入输出路径
    >>> output_paths = {
    ...     'power': ['/data/output/1000000000000001/power_202305010000.csv']
    ... }
    >>> deploy_paths = {
    ...     'power': ['/deploy/1000000000000001/power_202305010000.csv']
    ... }
    >>>
    >>> # 执行部署
    >>> deployPower(
    ...     staTaskId='1000000000000001',
    ...     staType='PV',
    ...     taskDate=pd.Timestamp('2023-05-01 00:00:00'),
    ...     timeliness='ST',
    ...     outputPaths=output_paths,
    ...     deployPaths=deploy_paths,
    ...     logger=logger,
    ...     messageQueueProducer=producer
    ... )

    See Also
    --------
    dataDump.powerDump : 实际执行功率数据转储的函数
    """
    fileFlag = False
    for outputPath in outputPaths['power']:
        try:
            dataPower = pd.read_csv(outputPath, index_col='time')
            fileFlag = True
        except Exception as e:
            logger.warning(f"读取文件失败: {outputPath}")
            logger.warning(e)
            continue
    if not fileFlag:
        raise FileNotFoundError(f"部署功率文件不存在")

    for deployPath in deployPaths['power']:
        try:
            # 将时间转换为 UTC 时间
            if "time" in dataPower.columns:
                dataPower['time'] = pd.to_datetime(dataPower['time'])
                dataPower['time'] = dataPower['time'].dt.tz_convert("Asia/Shanghai").tz_localize(None)
            elif dataPower.index.name == "time":
                dataPower.index = pd.to_datetime(dataPower.index)
                dataPower.index = dataPower.index.tz_convert("Asia/Shanghai").tz_localize(None)
            else:
                logger.warning(f"列名: {dataPower.columns}")
                logger.warning(f"索引: {dataPower.index.name}")
                raise ValueError("时间列名错误")
            if algorithm is not None:
                deployPath = deployPath.rstrip("csv") + algorithm + ".csv"
            dataDump.powerDump(staTaskId, staType, dataPower, deployPath, timeliness, taskDate, logger, messageQueueProducer)
        except Exception as e:
            logger.warning(f"部署文件发生意外: {deployPath} {e}")
            logger.warning(traceback.format_exc())
            continue


def deployAcc(
    staTaskId: str,
    taskDate: pd.Timestamp,
    timeliness: str,
    outputPaths: Dict[str, List[str]],
    deployPaths: Dict[str, List[str]],
    logger: logging.Logger,
    messageQueueProducer: Union[mq.Cproducer, mq.CNullKafkaProducer]
) -> None:
    """部署精度评估结果到指定位置

    将精度评估结果从输出路径复制到部署路径。

    Args:

        - staTaskId: 站点任务ID
        - taskDate: 任务日期
        - timeliness: 预测时效
        - outputPaths: 包含输出文件路径的字典
        - deployPaths: 包含部署路径的字典
        - logger: 日志记录器
        - messageQueueProducer: 消息队列生产者

    Note:

        当前为预留接口，具体实现待完成

    Example:

        ```python
        # 初始化日志和消息队列
        from src import logger, message
        import pandas as pd

        logger = logger.setup_logger('deploy_acc')
        producer = message.CNullKafkaProducer()

        # 配置输入输出路径
        output_paths = {
            'accuracy': ['/data/output/1000000000000001/acc_202305010000.csv']
        }
        deploy_paths = {
            'accuracy': ['/deploy/1000000000000001/acc_202305010000.csv']
        }

        # 执行部署
        deployAcc(
            staTaskId='1000000000000001',
            taskDate=pd.Timestamp('2023-05-01 00:00:00'),
            timeliness='ST',
            outputPaths=output_paths,
            deployPaths=deploy_paths,
            logger=logger,
            messageQueueProducer=producer
        )
        ```

    Returns:
        None: 无返回值，部署结果会通过消息队列发送
    """
    pass


def deployModel(
    staTaskId: str,
    taskDate: pd.Timestamp,
    timeliness: str,
    outputPaths: Dict[str, List[str]],
    deployPaths: Dict[str, List[str]],
    logger: logging.Logger,
    messageQueueProducer: Union[mq.Cproducer, mq.CNullKafkaProducer]
) -> None:
    """部署模型文件到指定位置，包括模型文件、哈希校验文件和密钥文件。

    将训练好的模型文件及其相关文件从输出路径复制到部署路径，并进行必要的验证。
    主要功能包括：
    - 验证输入文件的存在性和完整性
    - 执行模型文件的哈希校验
    - 处理密钥文件的部署
    - 通过消息队列发送部署状态

    Parameters
    ----------
    staTaskId : str
        站点任务ID，用于标识当前部署任务
    taskDate : pd.Timestamp
        任务日期，用于模型版本控制
    timeliness : str
        预测时效，支持以下值：
        - 'UST': 超短期预测
        - 'ST': 短期预测
        - 'MT': 中期预测
        - 'SS': 次季节预测
    outputPaths : Dict[str, List[str]]
        包含输出文件路径的字典，必须包含以下键：
        - 'model': 模型文件路径列表
        - 'hash': 哈希校验文件路径列表
        - 'key': 密钥文件路径列表
    deployPaths : Dict[str, List[str]]
        包含部署路径的字典，必须包含以下键：
        - 'model': 目标模型文件路径列表
        - 'hash': 目标哈希文件路径列表
        - 'key': 目标密钥文件路径列表
    logger : logging.Logger
        日志记录器，用于记录处理过程中的信息
    messageQueueProducer : Union[mq.Cproducer, mq.CNullKafkaProducer]
        消息队列生产者，用于发送部署状态和结果

    Raises
    ------
    FileNotFoundError
        当输入的模型文件、哈希文件或密钥文件不存在时抛出
    ValueError
        当模型文件校验失败或文件格式不正确时抛出
    KeyError
        当输入参数字典中缺少必要的键时抛出

    Notes
    -----
    1. 文件要求：
       - 模型文件(.pkl): 模型权重文件
       - 哈希文件(.hash): 包含模型文件的 MD5 校验和
       - 密钥文件(.key): 用于模型解密的密钥文件

    2. 文件命名约定：
       - 模型文件: `timeStamp.pkl`
       - 哈希文件: `timeStamp.hash`
       - 密钥文件: `timeStamp.key`

    3. 部署流程：
       1. 检查所有输入文件是否存在
       2. 验证模型文件的哈希值
       3. 创建目标目录（如果不存在）
       4. 复制文件到目标位置
       5. 发送部署成功消息

    Examples
    --------
    >>> from src import logger, message
    >>> import pandas as pd
    >>>
    >>> # 初始化日志和消息队列
    >>> logger = logger.setup_logger('deploy_model')
    >>> producer = message.CNullKafkaProducer()
    >>>
    >>> # 配置输入输出路径
    >>> output_paths = {
    ...     'model': ['/data/output/1000000000000001/202305010000.pkl'],
    ...     'hash': ['/data/output/1000000000000001/202305010000.hash'],
    ...     'key': ['/data/output/1000000000000001/202305010000.key']
    ... }
    >>> deploy_paths = {
    ...     'model': ['/deploy/1000000000000001/202305010000.pkl'],
    ...     'hash': ['/deploy/1000000000000001/202305010000.hash'],
    ...     'key': ['/deploy/1000000000000001/202305010000.key']
    ... }
    >>>
    >>> # 执行部署
    >>> deployModel(
    ...     staTaskId='1000000000000001',
    ...     taskDate=pd.Timestamp('2023-05-01 00:00:00'),
    ...     timeliness='ST',
    ...     outputPaths=output_paths,
    ...     deployPaths=deploy_paths,
    ...     logger=logger,
    ...     messageQueueProducer=producer
    ... )

    See Also
    --------
    dataDump.modelDump : 实际执行模型文件转储的函数
    """
    fileFlag = False
    for outputPath in outputPaths['model']:
        try:
            if os.path.exists(outputPath):
                fileFlag = True
        except Exception as e:
            logger.warning(f"读取文件失败: {outputPath}")
            logger.warning(e)
            continue
    if not fileFlag:
        logger.error(f"部署模型文件不存在: {outputPaths['model']}")
        raise FileNotFoundError("部署模型文件不存在")

    fileFlag = False
    for outputPath in outputPaths['hash']:
        try:
            if os.path.exists(outputPath):
                fileFlag = True
        except Exception as e:
            logger.warning(f"读取文件失败: {outputPath}")
            logger.warning(e)
            continue
    if not fileFlag:
        raise FileNotFoundError("部署hash文件不存在")

    fileFlag = False
    for outputPath in outputPaths['key']:
        try:
            if os.path.exists(outputPath):
                fileFlag = True
        except Exception as e:
            logger.warning(f"读取文件失败: {outputPath}")
            logger.warning(e)
            continue
    if not fileFlag:
        raise FileNotFoundError("部署密钥文件不存在")


def deploy(
    params: pp.CParams,
    checkpoint: Optional[pd.Timestamp],
    logger: logging.Logger,
    messageQueueProducer: Union[mq.Cproducer, mq.CNullKafkaProducer]
) -> None:
    """统一部署入口函数，用于调度和部署不同类型的数据和模型。

    根据参数配置自动处理不同时效(UST/ST/MT/SS)的部署任务。

    Parameters
    ----------
    params : pp.CParams
        参数配置对象，包含任务和站点信息。
        - task: 任务配置，包含日期范围等参数
        - staParams: 站点参数字典，key为站点任务ID，value为站点参数
        - 每个站点参数包含:
            - staId: 站点ID
            - timeLiness: 时效列表，如['UST', 'ST', 'MT', 'SS']
            - algorithm: 算法配置字典
    checkpoint : Optional[pd.Timestamp]
        检查点时间戳，如果提供，则从该时间点继续执行部署。
    logger : logging.Logger
        日志记录器，用于记录部署过程中的信息。
    messageQueueProducer : Union[mq.Cproducer, mq.CNullKafkaProducer]
        消息队列生产者，用于发送部署状态和结果。

    Notes
    -----
    1. 支持以下时效类型:
       - UST: 超短期，每15分钟一个任务
       - ST: 短期，每天一个任务
       - MT: 中期，每天一个任务
       - SS: 短时，每天一个任务

    2. 对于UST时效，任务时间会向下取整到15分钟整点。

    3. 任务执行时会自动处理时区转换，统一使用'Asia/Shanghai'时区。

    Examples
    --------
    >>> from src import logger, message, params
    >>> import pandas as pd
    >>>
    >>> # 设置日志
    >>> logger = logger.setup_logger('deploy_main')
    >>> producer = message.CNullKafkaProducer()
    >>>
    >>> # 加载配置文件
    >>> config_path = '/path/to/config.yaml'
    >>> params = params.CParams(config_path)
    >>>
    >>> # 设置检查点（可选，用于断点续传）
    >>> checkpoint = None  # 或者指定一个时间戳，如：pd.Timestamp('2023-05-01 00:00:00')
    >>>
    >>> # 执行部署
    >>> deploy(
    ...     params=params,
    ...     checkpoint=checkpoint,
    ...     logger=logger,
    ...     messageQueueProducer=producer
    ... )

    Returns
    -------
    None
        无返回值，部署结果会通过日志和消息队列输出。
    """
    logger.info("部署开始")

    for staTaskId, staParam in params.staParams.items():
        logger.info(f"部署站点: {staParam.staId}")
        for timeliness in staParam.timeLiness:

            if timeliness == "UST":
                taskDateList = pd.date_range(start=params.task.dateRange[0], end=params.task.dateRange[1],
                                             freq="15min")
            elif timeliness == "ST":
                taskDateList = pd.date_range(start=params.task.dateRange[0], end=params.task.dateRange[1],
                                             freq="D")
            elif timeliness == "MT":
                taskDateList = pd.date_range(start=params.task.dateRange[0], end=params.task.dateRange[1],
                                             freq="D")
            elif timeliness == "SS":
                taskDateList = pd.date_range(start=params.task.dateRange[0], end=params.task.dateRange[1],
                                             freq="D")
            else:
                raise RuntimeError("Invalid timeLiness")

            for algorithm, versions in staParam.algorithm.items():
                for version in versions:
                    for taskDate in taskDateList:
                        taskDate = taskDate.replace(minute = int(taskDate.minute / 15) * 15)
                        # TODO 改用真实起报时间
                        taskFcMeteoDate = taskDate.replace(minute=0, second=0, microsecond=0, nanosecond=0)
                        while taskFcMeteoDate.hour != 12:
                            taskFcMeteoDate = taskFcMeteoDate - pd.Timedelta(hours=1)
                        logger.info(
                            f"部署站点: {staParam.staId} 时效: {timeliness} 算法: {algorithm} 版本: {version} 日期: {taskDate}")
                        if timeliness == "UST":
                            taskDateStart = taskDate.tz_convert('Asia/Shanghai')
                            # 将分钟数向下取整到 15 分钟
                            # 例如:
                            # 2023-10-01 12:07:00 -> 2023-10-01 12:00:00
                            # 2023-10-01 12:22:00 -> 2023-10-01 12:15:00
                            # 2023-10-01 12:37:00 -> 2023-10-01 12:30:00
                            # 2023-10-01 12:52:00 -> 2023-10-01 12:45:00
                            minute = int(taskDate.minute / 15) * 15
                            taskDateStart = taskDateStart.replace(minute=minute, second=0, microsecond=0) + pd.Timedelta(minutes=45)
                        elif timeliness == "ST":
                            taskDateStart = taskDate.tz_convert('Asia/Shanghai') + pd.Timedelta(days=1)
                            taskDateStart = taskDateStart.replace(hour=0, minute=0, second=0, microsecond=0)
                        elif timeliness == "MT":
                            taskDateStart = taskDate.tz_convert('Asia/Shanghai') + pd.Timedelta(days=1)
                            taskDateStart = taskDateStart.replace(hour=0, minute=0, second=0, microsecond=0)
                        elif timeliness == "SS":
                            taskDateStart = taskDate.tz_convert('Asia/Shanghai') + pd.Timedelta(days=1)
                            taskDateStart = taskDateStart.replace(hour=0, minute=0, second=0, microsecond=0)
                        else:
                            raise ValueError(f"时效: {timeliness} 不支持")
                        if timeliness == "UST":
                            taskDateEnd = taskDateStart + pd.Timedelta(hours=4) - pd.Timedelta(minutes=15)
                        elif timeliness == "ST":
                            taskDateEnd = taskDateStart + pd.Timedelta(hours=72) - pd.Timedelta(minutes=15)
                        elif timeliness == "MT":
                            taskDateEnd = taskDateStart + pd.Timedelta(hours=240) - pd.Timedelta(minutes=15)
                        elif timeliness == "SS":
                            taskDateEnd = taskDateStart + pd.Timedelta(hours=1080) - pd.Timedelta(minutes=15)
                        else:
                            raise ValueError(f"时效: {timeliness} 不支持")
                        outputPaths = params.path.setOutputPath(staParam.staId, staParam.dataset, timeliness, taskDate,
                                                                algorithm, version, checkpoint)
                        deployPaths = params.path.setDeploymentPath(staParam.staId, staParam.staType, taskDateStart,
                                                                    taskDateEnd)

                        logger.info(f"输出路径: {outputPaths} 部署路径: {deployPaths}")

                        if params.task.taskType == TypeDefine.TaskType.FT or params.task.taskType == TypeDefine.TaskType.UPT:
                            deployModel(staTaskId, taskDate, timeliness, outputPaths, deployPaths, logger,
                                        messageQueueProducer)
                        elif params.task.taskType == TypeDefine.TaskType.HFC:
                            deployPower(staTaskId, staParam.staType, taskFcMeteoDate, timeliness, outputPaths, deployPaths, logger,
                                        messageQueueProducer, algorithm)
                        elif params.task.taskType == TypeDefine.TaskType.PT:
                            outputPaths = params.path.setOutputPath(staParam.staId, staParam.dataset, timeliness,
                                                                    taskDate,
                                                                    algorithm + "_post", version, checkpoint)
                            deployModel(staTaskId, taskDate, timeliness, outputPaths, deployPaths, logger,
                                        messageQueueProducer)
                        elif params.task.taskType == TypeDefine.TaskType.PHFC or params.task.taskType == TypeDefine.TaskType.PFC:
                            outputPaths = params.path.setOutputPath(staParam.staId, staParam.dataset, timeliness,
                                                                    taskDate,
                                                                    algorithm + "_post", version, checkpoint)
                            deployPower(staTaskId, staParam.staType, taskFcMeteoDate, timeliness, outputPaths,
                                        deployPaths, logger,
                                        messageQueueProducer)
                        else:
                            if timeliness == "ST":
                                deployMeteo(staTaskId, staParam.staType, timeliness, outputPaths, deployPaths, logger, messageQueueProducer)
                            deployPower(staTaskId, staParam.staType, taskFcMeteoDate, timeliness, outputPaths, deployPaths, logger,
                                        messageQueueProducer)

    logger.info("部署结束")
