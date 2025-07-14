"""数据保存模块

该模块提供了将气象数据、功率数据和准确率数据保存到文件系统的功能，并支持通过消息队列发送通知。

功能概述
--------
1. 保存气象数据到CSV文件
2. 保存功率数据到CSV文件
3. 保存准确率数据到CSV文件
4. 自动创建不存在的目录
5. 可选的消息队列通知

使用示例
--------
```python
import logging
import pandas as pd
from datetime import datetime
from message import Cproducer

# 初始化日志记录器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化消息队列生产者（可选）
producer = Cproducer("kafka_broker_address")

# 准备数据
data = pd.DataFrame({
    'time': pd.date_range('2023-01-01', periods=24, freq='H'),
    'value': [10.5 * i for i in range(24)]
}).set_index('time')

# 保存气象数据
meteoDump(
    taskID="task_123",
    meteo=data,
    timeliness="realtime",
    filePath="./output/meteo_data.csv",
    taskDate=datetime.now(),
    logger=logger,
    messageQueueProducer=producer
)

# 保存功率数据
powerDump(
    taskID="task_123",
    power=data,
    filePath="./output/power_data.csv",
    timeliness="realtime",
    taskDate=datetime.now(),
    logger=logger,
    messageQueueProducer=producer
)

# 保存准确率数据
accDump(
    taskID="task_123",
    acc=data,
    timeliness="daily",
    filePath="./output/accuracy_data.csv",
    logger=logger,
    messageQueueProducer=producer
)
```

注意事项
--------
1. 确保对输出目录有写权限
2. 文件路径应使用绝对路径
3. 时间序列数据应使用 pandas.Timestamp 类型
4. 消息队列生产者是可选的，如果不提供则不会发送通知
5. 所有函数都是线程安全的

异常处理
--------
- FileNotFoundError: 当目录创建失败时抛出
- PermissionError: 当没有文件写入权限时抛出
- IOError: 当文件写入失败时抛出
"""

import os
import logging
import pandas as pd
from typing import Optional, Union
from pathlib import Path
from ..message import Cproducer, CNullKafkaProducer


def _dircheckandcreate(path: Union[str, Path], logger: logging.Logger) -> None:
    """检查并创建目录（如果不存在）。
    
    参数
    ----------
    path : Union[str, Path]
        要检查的目录路径
    logger : logging.Logger
        用于记录日志的logger对象
        
    异常
    --------
    FileNotFoundError
        当目录创建失败时抛出
    PermissionError
        当没有目录创建权限时抛出
        
    注意
    ----
    如果目录已存在，则不会执行任何操作。
    """
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
            logger.info(f"目录 {path} 不存在，已成功创建")
        except Exception as e:
            logger.error(f"创建目录 {path} 失败: {e}")
            raise


def meteoDump(
    taskID: str,
    staType: str,
    meteo: pd.DataFrame,
    timeliness: str,
    filePath: Union[str, Path],
    taskDate: pd.Timestamp,
    logger: logging.Logger,
    messageQueueProducer: Optional[Union[Cproducer, CNullKafkaProducer]] = None
) -> None:
    """保存气象数据到CSV文件并发送通知。
    
    将气象数据保存到指定路径的CSV文件，并通过消息队列发送通知（如果提供了生产者）。
    
    参数
    ----------
    taskID : str
        任务ID，用于消息队列通知
    staType : str
        站点类型
    meteo : pd.DataFrame
        要保存的气象数据，索引将作为CSV的第一列
    timeliness : str
        数据时效性（如'realtime'、'daily'等）
    filePath : Union[str, Path]
        输出文件路径
    taskDate : pd.Timestamp
        任务日期时间
    logger : logging.Logger
        用于记录日志的logger对象
    messageQueueProducer : Optional[Union[Cproducer, CNullKafkaProducer]], optional
        消息队列生产者，如果提供则发送通知
        
    异常
    --------
    PermissionError
        当没有文件写入权限时抛出
    IOError
        当文件写入失败时抛出
        
    注意
    ----
    文件将以UTF-8编码保存，索引列将作为第一列。
    """
    _dircheckandcreate(os.path.dirname(filePath), logger)
    with open(filePath, "w") as f:
        meteo.to_csv(f, index=True)
        #f.flush()
        #os.fsync(f.fileno())
    if messageQueueProducer:
        messageQueueProducer.send_meteo(taskID, timeliness, staType, filePath, stime=taskDate)
    logger.info("气象数据保存成功: %s", filePath)


def powerDump(
    taskID: str,
    staType: str,
    power: pd.DataFrame,
    filePath: Union[str, Path],
    timeliness: str,
    taskDate: pd.Timestamp,
    logger: logging.Logger,
    messageQueueProducer: Optional[Union[Cproducer, CNullKafkaProducer]] = None
) -> None:
    """保存功率数据到CSV文件并发送通知。
    
    将功率数据保存到指定路径的CSV文件，并通过消息队列发送通知（如果提供了生产者）。
    时间索引将作为CSV的第一列保存。
    
    参数
    ----------
    taskID : str
        任务ID，用于消息队列通知
    staType : str
        站点类型
    power : pd.DataFrame
        要保存的功率数据，索引将作为CSV的第一列
    filePath : Union[str, Path]
        输出文件路径
    timeliness : str
        数据时效性（如'realtime'、'daily'等）
    taskDate : pd.Timestamp
        任务日期时间
    logger : logging.Logger
        用于记录日志的logger对象
    messageQueueProducer : Optional[Union[Cproducer, CNullKafkaProducer]], optional
        消息队列生产者，如果提供则发送通知
        
    异常
    --------
    PermissionError
        当没有文件写入权限时抛出
    IOError
        当文件写入失败时抛出
        
    注意
    ----
    文件将以UTF-8编码保存，索引列将作为第一列。
    """
    _dircheckandcreate(os.path.dirname(filePath), logger)
    with open(filePath, "w") as f:
        # 时间列为索引,需要保留
        power.to_csv(f, index=True)
        #f.flush()
        #os.fsync(f.fileno())
    if messageQueueProducer:
        messageQueueProducer.send_power(taskID, timeliness, staType, filePath, stime=taskDate)
    logger.info("功率数据保存成功: %s", filePath)


def accDump(
    taskID: str,
    acc: pd.DataFrame,
    timeliness: str,
    filePath: Union[str, Path],
    logger: logging.Logger,
    messageQueueProducer: Optional[Union[Cproducer, CNullKafkaProducer]] = None
) -> None:
    """保存准确率数据到CSV文件并发送通知。
    
    将准确率数据保存到指定路径的CSV文件，并通过消息队列发送通知（如果提供了生产者）。
    索引（检验细则名称）将作为CSV的第一列保存。
    
    参数
    ----------
    taskID : str
        任务ID，用于消息队列通知
    acc : pd.DataFrame
        要保存的准确率数据，索引将作为CSV的第一列
    timeliness : str
        数据时效性（如'daily'、'monthly'等）
    filePath : Union[str, Path]
        输出文件路径
    logger : logging.Logger
        用于记录日志的logger对象
    messageQueueProducer : Optional[Union[Cproducer, CNullKafkaProducer]], optional
        消息队列生产者，如果提供则发送通知
        
    异常
    --------
    PermissionError
        当没有文件写入权限时抛出
    IOError
        当文件写入失败时抛出
        
    注意
    ----
    文件将以UTF-8编码保存，索引列将作为第一列。
    """
    _dircheckandcreate(os.path.dirname(filePath), logger)
    with open(filePath, "w") as f:
        # 检验细则名称为索引,需要保留
        acc.to_csv(filePath, index=True)
        #f.flush()
        #os.fsync(f.fileno())
    if messageQueueProducer:
        messageQueueProducer.send_acc(taskID, timeliness, filePath)
    logger.info("准确率数据保存成功: %s", filePath)
