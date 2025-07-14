"""
GreenPulse 新能源发电预测系统
---
本模块是 GreenPulse 新能源发电预测系统的核心包，提供了完整的预测、训练和部署功能。
系统支持风电和光伏发电预测，包含数据处理、模型训练、预测执行和结果部署等完整流程。

## 主要功能:

    1. 多源数据集成：支持多种数据源的接入和处理

    2. 预测模型训练：提供多种机器学习模型的训练接口

    3. 发电量预测：支持超短期、短期、中期和次季节预测

    4. 精度评估：提供多种评估指标和可视化工具

    5. 分布式计算：支持 Ray 分布式计算框架

    6. 灵活部署：支持本地部署和云原生部署

## 主要模块详细说明:
    - task: 核心任务处理模块
        * 单站点预测 (taskSingleForecast)
        * 历史预测 (taskSingleHistryForecast)
        * 模型训练 (taskSingleTrain)
        * 任务分发与调度
    
    - params: 参数配置模块
        * 命令行参数解析 (Arg)
        * 参数管理 (CParams, CParamsInit, CParamsTask 等)
        * 站点参数配置 (CStaParams)
        * 路径管理 (CParamsPath)
    
    - deploy: 部署模块
        * 气象数据部署 (deployMeteo)
        * 功率数据部署 (deployPower)
        * 模型部署 (deployModel)
        * 精度评估结果部署 (deployAcc)
    
    - datasets: 数据集处理模块
        * 数据加载与预处理
        * 特征工程
        * 数据标准化与归一化
    
    - modelset: 模型集合模块
        * 基础模型实现
        * 模型训练与评估
        * 模型保存与加载
    
    - accuracy: 精度评估模块
        * 多种评估指标计算
        * 精度分析报告生成
        * 预测结果可视化
    
    - config: 配置模块
        * 类型定义
        * 常量定义
        * 枚举类型
    
    - logger: 日志记录模块
        * 日志配置
        * 日志级别管理
        * 日志格式化
    
    - message: 消息队列模块
        * 消息生产者
        * 消息消费者
        * 消息序列化
    
    - repair: 数据修复模块
        * 异常值检测
        * 缺失值填充
        * 数据平滑
    
    - utils: 工具函数集合
        * 日期时间处理
        * 文件操作
        * 数学计算

## 使用示例:
    1. 基本使用:
    ```python
    from src import params, task, logger
    
    # 初始化日志记录器
    logger = logger.setup_logger('app')
    
    # 解析命令行参数
    args = params.Arg().parse_args()
    
    # 创建并初始化参数对象
    params = params.CParams()
    params.params_parse(args, logger)
    
    # 执行任务
    task.task_deal(params, logger, None)
    ```
    
    2. 高级用法 - 自定义任务:
    ```python
    from datetime import datetime
    import pandas as pd
    from src import params, task, logger, message
    
    # 初始化日志记录器
    logger = logger.setup_logger('custom_task')
    
    # 创建参数对象
    params = params.CParams()
    
    # 设置初始化参数
    params.init.logLevel = "INFO"
    params.init.ray = True  # 启用 Ray 分布式计算
    
    # 设置任务参数
    params.task.taskType = params.TaskType.FORECAST
    params.task.dateRange = ["2023-01-01", "2023-01-07"]
    params.task.timeLiness = ["short_term", "medium_term"]
    
    # 添加站点
    params.addStaFromConfig(
        staId="site_001",
        staTaskId="task_001",
        staType="PV",
        staName="光伏电站1号",
        staLon=116.3913,
        staLat=39.9042,
        staAlt=43.5,
        staCap=50.0,
        timeLiness=["short_term", "medium_term"],
        algorithm={"xgboost": ["1.0"], "lstm": ["1.0"]},
        dataset=["nwp", "observation"],
        accuracy=["mae", "rmse", "r2"],
        postProcess=["bias_correction"]
    )
    
    # 初始化消息队列生产者
    mq_producer = message.Cproducer(
        bootstrap_servers=['localhost:9092'],
        topic='greenpulse_tasks'
    )
    
    try:
        # 执行任务
        task.task_deal(params, logger, mq_producer)
    finally:
        # 清理资源
        mq_producer.close()
        params.clean(logger)
    ```

## 注意事项:
    1. 使用前请确保已安装所有依赖项
    2. 配置文件路径需要正确设置
    3. 分布式计算需要 Ray 集群支持
    4. 消息队列需要 Kafka 服务支持

---
作者: GreenPulse 团队
项目主页: https://github.com/GreenPulse/greenpulse-gen
文档: https://greenpulse.readthedocs.io
"""

from . import utils
from . import datasets
from . import modelset
from . import accuracy
from . import config

from . import params
from . import deploy
from . import logger
from . import message
from . import repair
from . import task

__all__ = [
    'utils', 'datasets', 'modelset', 'accuracy', 'config',
    'params', 'deploy', 'logger', 'message', 'repair', 'task'
]
