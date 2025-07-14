"""数据集处理模块

该模块提供了数据加载、保存、模型加密解密等功能，是 GreenPulse 项目中的数据管理核心组件。

子模块说明
-----------
1. dataLoader: 数据加载器，负责从各种数据源加载气象和功率数据
2. dataDump: 数据保存器，负责将数据保存到文件系统
3. modelLoad: 模型加载器，负责加载和验证加密的模型文件
4. modelDump: 模型保存器，负责将模型加密后保存到文件系统

功能概述
-------
- 支持从多种数据源加载数据（CSV, NetCDF, 数据库等）
- 提供数据验证和转换功能
- 支持模型的安全存储和加载
- 实现数据完整性校验
- 提供消息队列集成

使用示例
-------
```python
import logging
import pandas as pd
from datasets import dataLoader, dataDump
from message import Cproducer

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 1. 加载数据
data_loader = dataLoader.CDataLoader(
    meotoOriginalCsvPaths=["path/to/data.csv"],
    meotoBusinessCsvPaths=[],
    logger=logger
)
data = data_loader.load()

# 2. 保存数据
producer = Cproducer("kafka_broker")
dataDump.powerDump(
    taskID="task_123",
    power=pd.DataFrame(...),
    filePath="./output/power.csv",
    timeliness="realtime",
    taskDate=pd.Timestamp.now(),
    logger=logger,
    messageQueueProducer=producer
)

# 3. 加载模型
from datasets import modelLoad, modelDump
model = modelLoad.modelLoad(
    modelPath="./models/model.enc",
    hashPath="./models/model.sha256",
    keyPath="./models/secret.key",
    logger=logger
)

# 4. 保存模型
modelDump.modelDump(
    taskId="task_123",
    model=model,
    timeliness="daily",
    modelPath="./models/model.enc",
    hashPath="./models/model.sha256",
    keyPath="./models/secret.key",
    logger=logger,
    messageQueueProducer=producer
)
```

注意事项
-------
1. 数据加载时需确保数据源路径有效且格式正确
2. 模型加解密需要正确的密钥文件
3. 文件操作需要适当的读写权限
4. 消息队列生产者需要正确配置
5. 时间序列数据应使用 pandas.Timestamp 类型
6. 所有路径都应使用绝对路径，以避免潜在问题

异常处理
-------
- FileNotFoundError: 当文件或目录不存在时抛出
- ValueError: 当参数无效或数据格式错误时抛出
- IOError: 当发生I/O错误时抛出
- RuntimeError: 当发生运行时错误时抛出
"""

from . import dataLoader
from . import dataDump
from . import modelLoad
from . import modelDump

__all__ = ["dataLoader", "dataDump", "modelLoad", "modelDump"]
