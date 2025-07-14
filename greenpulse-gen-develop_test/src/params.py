"""GreenPulse 参数管理模块。

该模块提供了完整的参数管理解决方案，用于处理 GreenPulse 系统中的各种配置参数。
支持从多种来源加载和解析参数，包括命令行参数、配置文件和数据库，并提供了类型安全
的参数访问接口。

主要功能
--------
- **多源参数加载**: 支持从命令行、配置文件和数据库加载参数，并按照优先级合并
- **类型安全**: 所有参数都进行类型检查和转换，确保类型安全
- **资源管理**: 管理CPU、GPU、内存等计算资源的分配和限制
- **任务配置**: 处理任务类型、日期范围、算法选择等任务相关参数
- **站点管理**: 支持从文件或数据库加载和管理站点特定参数
- **路径管理**: 提供灵活的文件系统路径模板管理，支持动态路径生成
- **数据库集成**: 支持从数据库加载配置和站点参数

核心类
------

   Arg
       命令行参数解析器，支持从命令行、配置文件和数据库加载参数
   TaskType
       任务类型枚举，定义系统支持的任务类型
   CParamsInit
       系统初始化参数类，管理日志、消息队列和数据库连接等配置
   CParamsResource
       计算资源配置类，管理CPU、GPU、内存等资源分配
   CParamsTask
       任务参数类，定义任务执行相关的所有参数
   CParamsPath
       路径参数类，管理所有文件系统路径
   CStaParams
       站点参数类，存储单个站点的配置信息
   CParams
       主参数类，整合所有参数类别，提供统一访问接口

快速开始
--------

```python

    from params import CParams, Arg, TaskType
    import logging

    # 配置日志
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # 创建参数解析器
    arg_parser = Arg(description="GreenPulse 参数解析器")

    # 添加自定义参数
    arg_parser.add_argument('--config', type=str, help='配置文件路径')

    # 解析命令行参数
    args = arg_parser.arg_parse()

    # 创建并初始化参数实例
    params = CParams()

    try:
        # 解析参数
        params.paramsParse(args, logger)

        # 使用参数
        logger.info(f"任务ID: {params.task.taskID}")
        logger.info(f"CPU核心数: {params.res.CPU}")
        logger.info(f"任务类型: {params.task.taskType}")

        # 处理站点参数
        if not params.staParams:
            logger.warning("未加载到任何站点参数")
        else:
            logger.info(f"成功加载 {len(params.staParams)} 个站点参数")

        # 设置任务类型
        params.task.taskType = TaskType.FORECAST

    except Exception as e:
        logger.critical(f"参数处理失败: {e}", exc_info=True)
        raise
    finally:
        # 清理资源
        params.clean(logger)

```

配置文件示例 (YAML 格式)
----------------------

```yaml

    # 系统初始化配置
    init:
      logLevel: "INFO"
      messageQueue: false

    # 资源配置
    resource:
      CPU: 4
      GPU: 1
      memory: 16

    # 任务配置
    task:
      taskID: "task_20230501_001"
      taskType: 1  # 1 表示预测任务
      dateRange: ["2023-01-01", "2023-01-31"]
      staListFile: "config/stations.yaml"
      timeLiness: ["UST", "ST"]
      algorithm:
        catboost: ["v1.0", "v1.1"]
        xgboost: ["v2.0"]

```

注意事项
--------
1. **参数优先级**: 命令行参数 > 配置文件 > 默认值
2. **必填参数**: 部分参数为必填项，如 `taskID` 和 `taskType`
3. **类型检查**: 所有参数都会进行类型检查，确保类型安全
4. **数据库连接**: 使用数据库功能前需要正确配置数据库连接参数
5. **日志记录**: 建议在应用启动时配置日志记录器，以便记录参数解析过程

API 参考
--------

### 模块级函数

#### `load_yaml(file_path: str) -> dict`
从YAML文件加载配置。

**参数**:
- `file_path` (str): YAML配置文件路径

**返回**:
- `dict`: 解析后的配置字典

**异常**:
- `FileNotFoundError`: 当配置文件不存在时引发
- `yaml.YAMLError`: 当YAML格式错误时引发

**示例**:
```python
config = load_yaml("config/settings.yaml")
```

### 类参考

#### `class Arg(argparse.ArgumentParser)`
命令行参数解析器，继承自`argparse.ArgumentParser`。

**方法**:
- `arg_parse(args_list: Optional[List[str]] = None) -> argparse.Namespace`
  解析命令行参数并返回解析结果。

**示例**:
```python
parser = Arg(description="参数解析器")
args = parser.arg_parse()
```

#### `class CParamsInit`
系统初始化参数类。

**属性**:
- `logLevel` (Union[str, int]): 日志级别
- `messageQueue` (bool): 是否启用消息队列
- `database` (bool): 是否启用数据库
- 其他系统初始化相关参数

**方法**:
- `__getitem__(item: str) -> Any`: 通过字典方式访问属性
- `__setitem__(item: str, value: Any) -> None`: 通过字典方式设置属性

#### `class CParamsResource`
计算资源配置参数类。

**属性**:
- `CPU` (int): CPU核心数
- `GPU` (int): GPU数量
- `CMEM` (int): CPU内存(MB)
- `GMEM` (int): GPU显存(MB)
- `Node` (int): 节点数

**方法**:
- `__getitem__(item: str) -> Any`: 通过字典方式访问属性
- `__setitem__(item: str, value: Any) -> None`: 通过字典方式设置属性

#### `class CParamsTask`
任务参数类。

**属性**:
- `taskID` (List[str]): 任务ID列表
- `taskType` (Union[int, TaskType]): 任务类型
- `dateRange` (List[Optional[str]]): 日期范围
- `staListFile` (Optional[str]): 站点列表文件
- `algorithm` (Dict[str, List[str]]): 算法配置
- 其他任务相关参数

**方法**:
- `__getitem__(item: str) -> Any`: 通过字典方式访问属性
- `__setitem__(item: str, value: Any) -> None`: 通过字典方式设置属性

#### `class CParamsPath`
路径参数类。

**属性**:
- `outPathRoot` (str): 输出根目录
- `deploymentRoot` (str): 部署根目录
- 其他路径相关参数

#### `class CStaParams`
站点参数类。

**属性**:
- `stationID` (str): 站点ID
- `stationName` (str): 站点名称
- `longitude` (float): 经度
- `latitude` (float): 纬度
- 其他站点相关参数

#### `class CParams`
主参数类，整合所有参数类别。

**属性**:
- `init` (CParamsInit): 初始化参数
- `res` (CParamsResource): 资源参数
- `task` (CParamsTask): 任务参数
- `path` (CParamsPath): 路径参数
- `staParams` (List[CStaParams]): 站点参数列表

**方法**:
- `clean(logger: logging.Logger) -> None`: 清理资源
- `paramsParse(args: argparse.Namespace, logger: logging.Logger) -> None`: 解析参数

### 类型定义

#### `class TaskType(IntEnum)`
任务类型枚举。

**值**:
- `FORECAST = 1`: 预测任务
- `HISTORY_FORECAST = 2`: 历史预测任务
- `TRAIN = 3`: 训练任务
- `UPDATE_TRAIN = 4`: 更新训练

#### `class TimeLinessFcHour(IntEnum)`
预测时效枚举。

**值**:
- `UST`: 超短期
- `ST`: 短期
- `MT`: 中期
- `SS`: 次季节

### 工具函数

#### `parse_date(date_str: str) -> datetime.date`
将日期字符串转换为日期对象。

**参数**:
- `date_str` (str): 日期字符串，格式为"YYYY-MM-DD"

**返回**:
- `datetime.date`: 日期对象

### 注意事项

1. 配置文件支持 YAML 格式
2. 数据库连接参数仅在启用数据库功能时使用
3. 使用完成后应调用 `clean()` 方法释放资源
4. 站点参数可以通过配置文件或数据库加载
"""
import os
import glob
import yaml
import logging
import argparse
import psycopg2
import pandas as pd
from math import ceil
from typing import Optional, Any, List, Dict, Union, Tuple
from .config.TypeDefine import TaskType, TimeLinessFcHour, AccRule


class Arg(argparse.ArgumentParser):
    """命令行参数解析器，继承自 argparse.ArgumentParser。

    提供 GreenPulse 应用所需的命令行参数解析功能，支持从命令行、配置文件或环境变量中
    读取配置参数。支持参数包括系统初始化、任务配置、资源分配和文件路径等。

    Attributes
    ----------
    description : str
        解析器的描述信息，显示在帮助信息中。

    See Also
    --------
    argparse.ArgumentParser : 基类，提供基本的参数解析功能。

    Notes
    -----
    参数优先级: 命令行参数 > 配置文件参数 > 默认值

    支持的参数类别:
    - 配置文件: 指定配置文件路径
    - 日志配置: 日志级别等
    - 任务参数: 任务ID、类型、日期范围等
    - 资源分配: CPU/GPU核心数、内存等
    - 文件路径: 输入/输出路径、部署路径等

    Examples
    --------
    >>> # 创建参数解析器实例
    >>> parser = Arg(description="GreenPulse 参数解析器")
    >>>
    >>> # 解析命令行参数
    >>> args = parser.arg_parse()
    >>>
    >>> # 在脚本中使用参数
    >>> print(f"配置文件路径: {args.config}")
    >>> print(f"日志级别: {args.logLevel}")
    """

    def __init__(self, description=""):
        """初始化 Arg 参数解析器。

        设置所有命令行参数的默认值和帮助信息。

        Parameters
        ----------
        description : str, optional
            解析器的描述信息，将显示在帮助信息的顶部。

        Notes
        -----
        此方法会添加以下参数组:
        - 配置文件: 指定配置文件路径
        - 日志配置: 日志级别
        - 任务参数: 任务ID、类型、日期范围等
        - 资源分配: CPU/GPU核心数、内存等
        - 文件路径: 输入/输出路径、部署路径等
        """
        super().__init__(description=description)
        self.add_argument(
            "-c",
            "--config",
            default="config/GreenPulse.yaml",
            help="输入配置文件, 该文件保存了项目启动参数、中间文件路径、部署路径, 默认值为: config/GreenPulse.yaml",
        )
        self.add_argument(
            "-l",
            "--logLevel",
            help="日志等级，默认 INFO, 可选 NOTSET DEBUG INFO WARNING ERROR CRITICAL",
            choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            nargs=1,
            type=str,
        )
        # init
        self.add_argument("--retry", help="任务失败重试次数", nargs=1, type=int)
        self.add_argument("--retryInterval", help="任务失败重试间隔, 单位: 秒", nargs=1, type=int)
        self.add_argument("--runTimeMax", help="任务运行时长上限, 单位: 秒", nargs=1, type=int)
        self.add_argument("--messageQueue", help="是否启用消息队列, 默认为否", nargs=1, type=bool)
        self.add_argument("--messageQueueTopic", help="消息队列主题", nargs=1, type=bool)
        self.add_argument("--messageQueueURL", help="消息队列地址", nargs="*", type=str)
        self.add_argument("--database", help="是否启用数据库查询, 默认为否", nargs=1, type=bool)
        self.add_argument("--databaseURL", help="消息队列地址", nargs="*", type=str)
        self.add_argument("--databaseName", help="数据库名称", nargs=1, type=str)
        self.add_argument("--databaseUser", help="数据库用户", nargs=1, type=str)
        self.add_argument("--databasePassword", help="数据库密码", nargs=1, type=str)
        self.add_argument("--databasePort", help="数据库端口", nargs=1, type=str)
        # task
        self.add_argument("--taskID", help="任务 ID", nargs=1, type=str)
        self.add_argument(
            "-f",
            "--taskType",
            help="任务类型, 可选 fc/预测 hfc/历史预测（回算） ft/重新训练 upt/更新训练",
            nargs=1,
            type=str,
            choices=["fc", "hfc", "ft", "upt"],
        )
        self.add_argument("-dr", "--dateRange", help="指定日期范围", nargs=2)
        self.add_argument("--staListType", help="站点清单类型, 可选 single/单站点 area/区域", nargs=1, type=str,
                          choices=["single", "area"])
        self.add_argument("--staListFile", help="任务站点清单文件路径", nargs=1, type=str)
        self.add_argument(
            "--timeliness", help="预测时效, 可选 UST/超短期 ST/短期 MT/中期 SS/次季节", nargs="*", type=str,
            choices=["UST", "ST", "MT", "SS"]
        )
        self.add_argument("-d", "--dataSet", help="指定气象数据源, 默认值为 EC_IFS", nargs="*",
                          choices=["EC_IFS"], type=str)
        self.add_argument(
            "-a",
            "--algorithm",
            help="指定训练算法, 默认值为 catboost, 可选 catboost Baseline dnn LSTM tcn tide transformer",
            nargs="*",
            choices=["catboost", "baseline", "dnn", "LSTM", "tcn", "tide", "transformer"],
            type=str,
        )
        self.add_argument("--postProcess", help="后处理算法", nargs="*", type=str)
        self.add_argument("--accuracy", help="精度评估算法", nargs="*", type=str)
        # res
        self.add_argument("--cpu", help="CPU 使用数目", nargs=1, type=int)
        self.add_argument("--gpu", help="GPU 使用数目", nargs=1, type=int)
        self.add_argument("--cmem", help="CPU 使用内存容量(MB)", nargs=1, type=int)
        self.add_argument("--gmem", help="GPU 使用内存容量(MB)", nargs=1, type=int)
        self.add_argument("--node", help="使用节点数目", nargs=1, type=int)
        # path
        self.add_argument("--outPathRoot", help="中间文件输出路径", nargs="*", type=str)
        self.add_argument("--deployment", help="是否部署", nargs=1, type=bool)
        self.add_argument("--deploymentRoot", help="部署输出路径", nargs="*", type=str)

    def arg_parse(self, args_list: Optional[List[str]] = None) -> argparse.Namespace:
        """解析命令行参数并返回解析结果。

        解析命令行参数，支持从参数列表或系统参数中读取。

        Parameters
        ----------
        args_list : list of str, optional
            要解析的参数列表。如果为 None，则从 sys.argv 中获取。

        Returns
        -------
        argparse.Namespace
            包含解析后参数的对象，可以通过属性方式访问各个参数。

        Raises
        ------
        SystemExit
            当传入 -h 或 --help 参数时，显示帮助信息并退出。

        Notes
        -----
        返回的 Namespace 对象包含以下主要属性:
        - config: 配置文件路径
        - logLevel: 日志级别
        - taskID: 任务ID列表
        - taskType: 任务类型
        - dateRange: 日期范围
        - 其他通过 add_argument 添加的参数

        Examples
        --------
        >>> # 从命令行参数解析
        >>> args = parser.arg_parse()
        >>>
        >>> # 从参数列表解析
        >>> custom_args = ["--config", "my_config.yaml", "--logLevel", "DEBUG"]
        >>> args = parser.arg_parse(custom_args)
        >>>
        >>> # 使用解析后的参数
        >>> if args.logLevel:
        ...     import logging
        ...     logging.basicConfig(level=args.logLevel[0])
        >>>
        >>> # 访问其他参数
        >>> print(f"任务ID: {args.taskID}" if args.taskID else "未指定任务ID")
        """
        args = self.parse_args(args_list)
        return args


class CParamsInit:
    """系统初始化参数类

    存储和管理系统初始化相关的配置参数，包括日志级别、消息队列和数据库连接设置。

    Attributes:
        logLevel (Union[str, int]): 日志级别，默认为 "INFO"。
        messageQueue (bool): 是否启用消息队列，默认为 False。
        messageQueueTopic (str): 消息队列主题名称。
        messageQueueURL (List[str]): 消息队列服务器URL列表。
        ray (bool): 是否启用Ray分布式计算，默认为 False。
        retry (int): 任务重试次数，默认为0。
        retryInterval (int): 任务重试间隔（秒），默认为0。
        runTimeMax (int): 最大运行时间（秒），0表示无限制，默认为0。
        database (bool): 是否启用数据库连接，默认为 False。
        databaseURL (str): 数据库服务器URL。
        databaseName (str): 数据库名称。
        databaseUser (str): 数据库用户名。
        databasePassword (str): 数据库密码。
        databasePort (str): 数据库端口。
        dbcursor (Optional[psycopg2.extensions.cursor]): 数据库游标对象。
        dbconn (Optional[psycopg2.extensions.connection]): 数据库连接对象。

    Example:
        ```python
        # 创建初始化参数实例
        init_params = CParamsInit()

        # 配置参数
        init_params.logLevel = "DEBUG"
        init_params.messageQueue = True
        init_params.messageQueueURL = ["kafka1:9092", "kafka2:9092"]

        # 通过字典方式访问属性
        print(init_params["logLevel"])  # 输出: DEBUG
        ```

    Note:
        - 当 database 为 True 时，必须设置有效的数据库连接参数
        - 当 messageQueue 为 True 时，必须设置有效的消息队列URL
    """

    def __getitem__(self, item: str) -> Any:
        """允许通过字典方式访问属性。

        Args:
            item (str): 属性名称

        Returns:
            Any: 属性值

        Raises:
            KeyError: 当属性不存在时引发
        """
        return self.__dict__[item]

    def __init__(self):
        """初始化所有参数为默认值。"""
        self.logLevel: Union[str, int] = "INFO"
        self.messageQueue: bool = False
        self.messageQueueTopic: str = ""
        self.messageQueueURL: List[str] = []
        self.ray: bool = False
        self.retry: int = 0
        self.retryInterval: int = 0
        self.runTimeMax: int = 0
        self.database: bool = False
        self.databaseURL: str = ""
        self.databaseName: str = ""
        self.databaseUser: str = ""
        self.databasePassword: str = ""
        self.databasePort: str = ""
        self.dbcursor: Optional[psycopg2.extensions.cursor] = None
        self.dbconn: Optional[psycopg2.extensions.connection] = None


class CParamsResource:
    """计算资源配置参数类

    存储和管理计算资源的配置参数，用于任务调度和资源分配。

    Attributes:
        CPU (int): 分配的CPU核心数，0表示自动分配。
        CMEM (int): 分配的CPU内存(MB)，0表示自动分配。
        GPU (int): 分配的GPU数量，0表示不使用GPU。
        GMEM (int): 分配的GPU显存(MB)，0表示自动分配。
        Node (int): 分配的节点数，用于分布式计算。

    Example:
        ```python
        # 创建资源配置实例
        res = CParamsResource()

        # 配置资源
        res.CPU = 8
        res.CMEM = 16384  # 16GB
        res.GPU = 1
        res.GMEM = 8192   # 8GB

        # 通过字典方式访问属性
        print(f"CPU核心数: {res['CPU']}")
        ```

    Note:
        - 实际分配的资源可能受系统资源限制
        - 设置为0表示使用系统默认值或自动分配
    """

    def __getitem__(self, item: str) -> Any:
        """允许通过字典方式访问属性。

        Args:
            item (str): 属性名称

        Returns:
            Any: 属性值

        Raises:
            KeyError: 当属性不存在时引发
        """
        return self.__dict__[item]

    def __init__(self):
        """初始化所有资源参数为默认值。"""
        self.CPU: int = 0
        self.CMEM: int = 0
        self.GPU: int = 0
        self.GMEM: int = 0
        self.Node: int = 0


class CParamsTask:
    """任务参数类

    存储和管理任务执行相关的配置参数，包括任务类型、日期范围、站点列表和算法选择等。

    Attributes:
        taskID (Optional[List[str]]): 任务ID列表，用于唯一标识任务。
        taskType (Union[int, TaskType]): 任务类型，0表示未设置，使用 TaskType 枚举表示具体类型。
        dateRange (List[Optional[str]]): 日期范围 [开始日期, 结束日期] 闭区间。
            - 对于训练任务：表示训练集的日期范围。
            - 对于预测任务：表示预测的起报日期范围。
        staListFile (Optional[str]): 站点列表文件路径，包含要处理的站点信息。
        staListType (str): 站点清单类型，可选 "single"(单站点) 或 "area"(区域)。
        timeLiness (List[str]): 预测时效列表，如 ["UST", "ST", "MT"]。
        algorithm (Dict[str, List[str]]): 算法配置字典，格式为 {"算法名": ["版本1", "版本2", ...]}。
        dataset (List[str]): 数据集名称列表，指定要使用的数据源。
        accuracy (List[str]): 精度评估算法名称列表，用于评估模型性能。
        postProcess (List[str]): 后处理算法名称列表，用于对预测结果进行后处理。

    Example:
        ```python
        # 创建任务参数实例
        task = CParamsTask()

        # 配置任务参数
        task.taskID = ["task_20230501_001"]
        task.taskType = TaskType.FORECAST  # 预测任务
        task.dateRange = ["2023-01-01", "2023-01-31"]
        task.staListFile = "config/stations.csv"
        task.staListType = "area"
        task.timeLiness = ["UST", "ST"]
        task.algorithm = {"catboost": ["v1.0", "v1.1"], "xgboost": ["v2.0"]}
        task.dataset = ["EC_IFS"]
        task.accuracy = ["mae", "rmse"]
        task.postProcess = ["smoothing"]

        # 通过字典方式访问属性
        print(f"任务类型: {task['taskType']}")
        ```

    Note:
        - dateRange 的日期格式应为 "YYYY-MM-DD"
        - algorithm 字典的键为算法名称，值为该算法的版本列表
        - 当 staListType 为 "single" 时，staListFile 应只包含一个站点
    """

    def __getitem__(self, item: str) -> Any:
        """允许通过字典方式访问属性。

        Args:
            item (str): 属性名称

        Returns:
            Any: 属性值

        Raises:
            KeyError: 当属性不存在时引发
        """
        return self.__dict__[item]

    def __init__(self):
        """初始化所有任务参数为默认值。"""
        self.taskID: Optional[List[str]] = None
        self.taskType: Union[int, TaskType] = 0
        self.dateRange: List[Optional[str]] = [None, None]  # [start, end] 闭区间
        self.staListFile: Optional[str] = None
        self.staListType: str = ""  # 站点清单类型, 可选 single/单站点 area/区域
        self.timeLiness: List[str] = []  # 预测时效列表
        self.algorithm: Dict[str, List[str]] = dict()  # 算法列表 {算法名: [版本1, 版本2]}
        self.dataset: List[str] = list()  # 数据集名称列表
        self.accuracy: List[str] = list()  # 精度评估算法名称列表
        self.postProcess: List[str] = list()  # 后处理算法名称列表


class CParamsPath:
    """文件系统路径管理类。

    负责管理 GreenPulse 应用中的文件系统路径，包括输入数据路径、中间输出路径
    和最终部署路径的配置和生成。支持动态路径模板和变量替换。

    Attributes
    ----------
    inPath : Dict[str, Any]
        输入文件路径模板字典，用于构建输入数据的完整路径。
        键为路径标识符，值为路径模板字符串或嵌套字典。

        .. note::
            路径模板支持以下变量：
            - `{date}`: 任务日期
            - `{timeliness}`: 预测时效，如 "UST"、"ST" 等
            - `{algorithm}`: 算法名称
            - `{version}`: 算法版本
            - `{staId}`: 站点ID
            - `{dataSet}`: 数据集名称
            - `{dataType}`: 数据类型，如 "SURF"、"UPAR"

    outPath : Dict[str, Any]
        中间文件输出路径模板字典，用于构建临时输出文件的路径。
        键为路径标识符，值为路径模板字符串或嵌套字典。

    deployment : Dict[str, Any]
        部署路径模板字典，用于构建最终部署文件的路径。
        键为路径标识符，值为路径模板字符串或嵌套字典。

    See Also
    --------
    CParams : 主参数类，包含路径配置的完整上下文

    Notes
    -----
    - 路径模板使用 Python 的字符串格式化语法，支持所有标准格式说明符
    - 日期格式化使用 `strftime` 语法，如 `{date:%Y%m%d}`
    - 路径分隔符会自动转换为当前操作系统的标准分隔符
    - 所有路径都会自动规范化，处理 `.` 和 `..` 等相对路径标记

    Examples
    --------
    >>> # 创建并配置路径参数
    >>> path = CParamsPath()
    >>>
    >>> # 配置输入路径模板
    >>> path.inPath = {
    ...     "root": ["/data/input"],
    ...     "meteo": {
    ...         "business": "{dataSet}/{dataType}/business/{date}/{timeliness}_{staId}.nc",
    ...         "original": "{dataSet}/{dataType}/original/{date}/{timeliness}_{staId}.nc"
    ...     },
    ...     "obs": "obs/{date}/{timeliness}_{staId}.csv"
    ... }
    >>>
    >>> # 配置输出路径模板
    >>> path.outPath = {
    ...     "root": "/data/output",
    ...     "model": "models/{algorithm}/{version}/{date}_{staId}.pkl",
    ...     "result": "results/{date}/{timeliness}_{algorithm}_{version}_{staId}.csv"
    ... }
    >>>
    >>> # 配置部署路径模板
    >>> path.deployment = {
    ...     "root": "/deploy",
    ...     "daily": "daily/{date:%Y%m%d}/forecast_{timeliness}_{staId}.csv",
    ...     "monthly": "monthly/{date:%Y%m}/forecast_{staId}.csv"
    ... }
    >>>
    >>> # 使用路径模板生成实际路径
    >>> from datetime import datetime
    >>> task_date = datetime(2023, 5, 15)
    >>> input_paths = path.setInputPath(
    ...     staId="S001",
    ...     dataSets=["EC_IFS"],
    ...     timeliness="ST",
    ...     taskDate=task_date,
    ...     algorithm="catboost",
    ...     version="v1.0"
    ... )
    >>> print(input_paths['meteo']['business'][0])
    /data/input/EC_IFS/SURF/business/20230515/ST_S001.nc
    """

    def __getitem__(self, item: str) -> Any:
        """允许通过字典方式访问属性。

        Args:
            item (str): 属性名称，可以是 'inPath'、'outPath' 或 'deployment'

        Returns:
            Any: 对应的路径模板字典

        Raises:
            KeyError: 当属性不存在时引发
        """
        return self.__dict__[item]

    def __init__(self):
        """初始化所有路径参数为默认的空字典。"""
        self.inPath: Dict[str, Any] = dict()  # 输入文件路径模板
        self.outPath: Dict[str, Any] = dict()  # 中间文件输出路径模板
        self.deployment: Dict[str, Any] = dict()  # 部署路径模板

    def setInputPath(self, staId: str, dataSets: list[str], timeliness: str, taskDate: pd.Timestamp, algorithm: str,
                     version: str, checkpoint: Optional[str] = None) -> dict[str, list[str]]:
        """生成输入文件的完整路径。

        根据配置的路径模板和提供的参数，生成气象数据、观测数据等输入文件的完整路径。
        支持多数据源、多数据类型的路径生成。

        Parameters
        ----------
        staId : str
            站点唯一标识符。
        dataSets : list of str
            数据集名称列表，如 ["EC_IFS", "GFS"]。
        timeliness : str
            预测时效标识，如 "UST"、"ST"、"MT" 等。
        taskDate : pandas.Timestamp
            任务对应的日期时间，用于构建时间相关的路径。
        algorithm : str
            使用的算法名称，如 "catboost"、"xgboost" 等。
        version : str
            算法版本号，如 "v1.0"、"v2.1" 等。
        checkpoint : str, optional
            模型检查点标识，主要用于模型相关文件。如果为 None，则使用最新检查点。

        Returns
        -------
        dict
            包含各类输入文件路径的字典，结构为：
            {
                'meteo': {
                    'business': [业务气象数据路径1, 业务气象数据路径2, ...],
                    'original': [原始气象数据路径1, 原始气象数据路径2, ...]
                },
                'obs': [观测数据路径1, 观测数据路径2, ...]
            }

        Raises
        ------
        ValueError
            如果必要的参数缺失或无效。

        Notes
        -----
        - 返回的路径已去重
        - 路径中的日期会自动格式化为 "YYYYMMDDHH" 格式
        - 支持多数据源和多数据类型的路径生成

        Examples
        --------
        >>> from datetime import datetime
        >>> import pandas as pd
        >>>
        >>> # 创建并配置路径参数
        >>> path = CParamsPath()
        >>> path.inPath = {
        ...     "root": ["/data/input"],
        ...     "meteo": {
        ...         "business": "{dataSet}/{dataType}/business/{date}/{timeliness}_{staId}.nc",
        ...         "original": "{dataSet}/{dataType}/original/{date}/{timeless}_{staId}.nc"
        ...     },
        ...     "obs": "obs/{date}/{timeliness}_{staId}.csv"
        ... }
        >>>
        >>> # 生成输入路径
        >>> task_date = pd.Timestamp('2023-05-15 12:00:00')
        >>> input_paths = path.setInputPath(
        ...     staId="S001",
        ...     dataSets=["EC_IFS"],
        ...     timeliness="ST",
        ...     taskDate=task_date,
        ...     algorithm="catboost",
        ...     version="v1.0"
        ... )
        >>> print(input_paths['meteo']['business'][0])
        /data/input/EC_IFS/SURF/business/2023051512/ST_S001.nc
        """

        DataTypes = ["SURF", "UPAR"]

        inputPath = dict()
        inputPath.update({
            "meteo": {
                "business": list(),
                "original": list(),
            },
            "obs": list(),
        })
        for root in self.inPath['root']:
            for dataSet in dataSets:
                for dataType in DataTypes:
                    businessPath = os.path.join(
                        root,
                        self.inPath['meteo']['business'].format(
                            staId=staId,
                            timeliness=timeliness,
                            date=taskDate.strftime("%Y%m%d%H"),
                            dataSet=dataSet,
                            dataType=dataType
                        )
                    )
                    originalPath = os.path.join(
                        root,
                        self.inPath['meteo']['original'].format(
                            staId=staId,
                            timeliness=timeliness,
                            date=taskDate.strftime("%Y%m%d%H"),
                            dataSet=dataSet,
                            dataType=dataType
                        )
                    )
                    obsPath = os.path.join(
                        root,
                        self.inPath['obs'].format(
                            staId=staId,
                            timeliness=timeliness,
                            date=taskDate.strftime("%Y%m%d%H"),
                            dataSet=dataSet,
                            dataType=dataType
                        )
                    )
                    inputPath['meteo']['business'].append(businessPath)
                    inputPath['meteo']['original'].append(originalPath)
                    inputPath['obs'].append(obsPath)

        inputPathUnique = dict()
        inputPathUnique.update({
            "meteo": {
                "business": list(),
                "original": list(),
            },
            "obs": list(),
        })

        [inputPathUnique['meteo']['business'].append(path) for path in inputPath['meteo']['business'] if path not in inputPathUnique['meteo']['business']]
        [inputPathUnique['meteo']['original'].append(path) for path in inputPath['meteo']['original'] if path not in inputPathUnique['meteo']['original']]
        [inputPathUnique['obs'].append(path) for path in inputPath['obs'] if path not in inputPathUnique['obs']]

        return inputPathUnique

    def setOutputPath(self, staId: str, dataSets: list[str], timeliness: str, taskDate: pd.Timestamp, algorithm: str,
                      version: str, checkpoint: Optional[str] = None) -> dict[str, list[str]]:
        """
        生成中间输出文件的完整路径。

        根据配置的输出路径模板和提供的参数，生成包括气象数据、功率数据、精度评估结果、
        日志文件、模型文件、哈希文件和密钥文件等中间文件的完整路径。

        Parameters
        ----------
        staId : str
            站点唯一标识符。
        dataSets : list of str
            数据集名称列表，如 ["EC_IFS", "GFS"]。
        timeliness : str
            预测时效标识，如 "UST"、"ST"、"MT" 等。
        taskDate : pandas.Timestamp
            任务对应的日期时间，用于构建时间相关的路径。
        algorithm : str
            使用的算法名称，如 "catboost"、"xgboost" 等。
        version : str
            算法版本号，如 "v1.0"、"v2.1" 等。
        checkpoint : str, optional
            模型检查点标识，主要用于模型相关文件。如果为 None，则使用最新检查点。

        Returns
        -------
        dict
            包含各类中间文件路径的字典，结构为：
            {
                'meteo': [气象数据路径1, 气象数据路径2, ...],
                'power': [功率数据路径1, 功率数据路径2, ...],
                'acc': [精度评估结果路径1, 精度评估结果路径2, ...],
                'log': [日志文件路径1, 日志文件路径2, ...],
                'model': [模型文件路径1, 模型文件路径2, ...],
                'hash': [哈希文件路径1, 哈希文件路径2, ...],
                'key': [密钥文件路径1, 密钥文件路径2, ...]
            }

            - 'meteo': list
                气象数据输出路径列表，格式为 NetCDF 或 GRIB 文件
            - 'power': list
                功率数据输出路径列表，格式为 CSV 或 Parquet 文件
            - 'acc': list
                精度评估结果路径列表，格式为 JSON 或 CSV 文件
            - 'log': list
                日志文件路径列表，格式为 .log 文件
            - 'model': list
                模型文件路径列表，格式为 .pkl 或 .h5 文件
            - 'hash': list
                哈希文件路径列表，用于校验文件完整性

        Raises
        ------
        ValueError
            如果必要的参数缺失或无效。

        See Also
        --------
        returnOutputPath : 获取所有输出文件路径（去重后）

        Examples
        --------
        >>> from datetime import datetime
        >>> import pandas as pd
        >>>
        >>> # 创建路径参数实例并配置
        >>> path = CParamsPath()
        >>> path.outPath = {
        ...     'root': ['/data/output1', '/data/output2'],
        ...     'meteo': 'meteo/{staID}/{year:04d}{month:02d}{day:02d}_{hour:02d}',
        ...     'power': 'power/{staID}/{algorithm}/{version}/{year:04d}{month:02d}{day:02d}_{hour:02d}.csv',
        ...     'acc': 'accuracy/{staID}/{algorithm}/{version}/{year:04d}{month:02d}{day:02d}_{hour:02d}.csv',
        ...     'log': 'logs/{staID}/{algorithm}/{version}/{year:04d}{month:02d}{day:02d}_{hour:02d}.log',
        ...     'model': 'models/{staID}/{algorithm}/{version}/{checkpoint}.pkl',
        ...     'hash': 'hashes/{staID}/{algorithm}/{version}/{checkpoint}.hash',
        ...     'key': 'keys/{staID}/{algorithm}/{version}/{checkpoint}.key'
        ... }
        >>>
        >>> # 生成输出路径
        >>> task_date = pd.Timestamp('2023-05-15 12:00:00')
        >>> output_paths = path.setOutputPath(
        ...     staId='ST001',
        ...     dataSets=['ECMWF', 'GFS'],
        ...     timeliness='ST',
        ...     taskDate=task_date,
        ...     algorithm='xgboost',
        ...     version='v1.0',
        ...     checkpoint='checkpoint_100'
        ... )
        >>>
        >>> # 查看模型文件路径
        >>> print(output_paths['model'])
        ['/data/output1/models/ST001/xgboost/v1.0/checkpoint_100.pkl',
         '/data/output2/models/ST001/xgboost/v1.0/checkpoint_100.pkl']

        Notes
        -----
        - 返回的路径已去重
        - 路径中的日期会自动格式化为 "YYYYMMDDHH" 格式
        - 支持多数据源和多数据类型的路径生成
        - 路径按配置的根目录顺序排列
        - 如果某个路径在多个根目录下存在，会返回所有实例
        - 当 checkpoint 为 None 时，会自动查找最新的检查点文件
        """
        outputPath = dict()
        outputPath.update({
            "meteo": list(),
            "power": list(),
            "acc": list(),
            "log": list(),
            "model": list(),
            "hash": list(),
            "key": list()
        })
        for root in self.outPath['root']:
            for dataSet in dataSets:
                meteoPath = os.path.join(
                    root,
                    self.outPath['meteo'].format(
                        staID=staId,
                        timeliness=timeliness,
                        year=taskDate.year,
                        month=taskDate.month,
                        day=taskDate.day,
                        hour=taskDate.hour,
                        dataSet=dataSet
                    )
                )
                powerPath = os.path.join(
                    root,
                    self.outPath['power'].format(
                        staID=staId,
                        timeliness=timeliness,
                        year=taskDate.year,
                        month=taskDate.month,
                        day=taskDate.day,
                        hour=taskDate.hour,
                        minute=taskDate.minute,
                        algorithm=algorithm,
                        version=version,
                    )
                )
                accPath = os.path.join(
                    root,
                    self.outPath['acc'].format(
                        staID=staId,
                        timeliness=timeliness,
                        year=taskDate.year,
                        month=taskDate.month,
                        day=taskDate.day,
                        hour=taskDate.hour,
                        minute=taskDate.minute,
                        algorithm=algorithm,
                        version=version
                    )
                )
                logPath = os.path.join(
                    root,
                    self.outPath['log'].format(
                        staID=staId,
                        timeliness=timeliness,
                        year=taskDate.year,
                        month=taskDate.month,
                        day=taskDate.day,
                        hour=taskDate.hour,
                        algorithm=algorithm,
                        version=version
                    )
                )
                if checkpoint is not None:
                    modelPath = os.path.join(
                        root,
                        self.outPath['model'].format(
                            staID=staId,
                            timeliness=timeliness,
                            algorithm=algorithm,
                            version=version,
                            checkpoint=checkpoint
                        )
                    )
                    hashPath = os.path.join(
                        root,
                        self.outPath['hash'].format(
                            staID=staId,
                            timeliness=timeliness,
                            algorithm=algorithm,
                            version=version,
                            checkpoint=checkpoint
                        )
                    )
                    keyPath = os.path.join(
                        root,
                        self.outPath['key'].format(
                            staID=staId,
                            timeliness=timeliness,
                            algorithm=algorithm,
                            version=version,
                            checkpoint=checkpoint
                        )
                    )
                else:
                    tempPath = os.path.join(
                        root,
                        self.outPath['model'].format(
                            staID=staId,
                            timeliness=timeliness,
                            algorithm=algorithm,
                            version=version,
                            checkpoint=None
                        )
                    )

                    tempDir = os.path.dirname(tempPath)
                    pklList = sorted(glob.glob(os.path.join(tempDir, "*.pkl")))

                    if len(pklList) > 0:
                        pklLast = pklList[-1]
                    else:
                        raise ValueError("No model found!")
                    checkpoint = os.path.splitext(os.path.basename(pklLast))[0]

                    modelPath = os.path.join(
                        root,
                        self.outPath['model'].format(
                            staID=staId,
                            timeliness=timeliness,
                            algorithm=algorithm,
                            version=version,
                            checkpoint=checkpoint
                        )
                    )
                    hashPath = os.path.join(
                        root,
                        self.outPath['hash'].format(
                            staID=staId,
                            timeliness=timeliness,
                            algorithm=algorithm,
                            version=version,
                            checkpoint=checkpoint
                        )
                    )
                    keyPath = os.path.join(
                        root,
                        self.outPath['key'].format(
                            staID=staId,
                            timeliness=timeliness,
                            algorithm=algorithm,
                            version=version,
                            checkpoint=checkpoint
                        )
                    )
                outputPath['meteo'].append(meteoPath)
                outputPath['power'].append(powerPath)
                outputPath['acc'].append(accPath)
                outputPath['log'].append(logPath)
                outputPath['model'].append(modelPath)
                outputPath['hash'].append(hashPath)
                outputPath['key'].append(keyPath)

        outputPathUnique = dict()
        outputPathUnique.update({
            "meteo": list(),
            "power": list(),
            "acc": list(),
            "log": list(),
            "model": list(),
            "hash": list(),
            "key": list()
        })

        [outputPathUnique['meteo'].append(path) for path in outputPath['meteo'] if
         path not in outputPathUnique['meteo']]
        [outputPathUnique['power'].append(path) for path in outputPath['power'] if
         path not in outputPathUnique['power']]
        [outputPathUnique['acc'].append(path) for path in outputPath['acc'] if path not in outputPathUnique['acc']]
        [outputPathUnique['log'].append(path) for path in outputPath['log'] if path not in outputPathUnique['log']]
        [outputPathUnique['model'].append(path) for path in outputPath['model'] if
         path not in outputPathUnique['model']]
        [outputPathUnique['hash'].append(path) for path in outputPath['hash'] if path not in outputPathUnique['hash']]
        [outputPathUnique['key'].append(path) for path in outputPath['key'] if path not in outputPathUnique['key']]

        return outputPathUnique

    def setDeploymentPath(self, staId: str, staType: str, taskDateStart: pd.Timestamp, taskDateEnd: pd.Timestamp) -> \
    dict[str, list[str]]:
        """根据参数生成各类部署文件的路径。

        根据配置的部署路径模板，生成包括气象数据、功率数据、日精度评估结果和月精度评估结果等
        部署文件的完整路径。

        Parameters
        ----------
        staId : str
            站点ID，用于标识特定的站点。
        staType : str
            站点类型，如 "WD"（风电）或 "PV"（光伏）。
        taskDateStart : pandas.Timestamp
            部署数据的开始时间。
        taskDateEnd : pandas.Timestamp
            部署数据的结束时间。

        Returns
        -------
        dict
            包含各类部署文件路径的字典，结构为：
            {
                'meteo': [气象数据部署路径1, 气象数据部署路径2, ...],
                'power': [功率数据部署路径1, 功率数据部署路径2, ...],
                'accDay': [日精度评估结果路径1, 日精度评估结果路径2, ...],
                'accMonth': [月精度评估结果路径1, 月精度评估结果路径2, ...]
            }

            - 'meteo': list
                气象数据部署路径列表
            - 'power': list
                功率数据部署路径列表
            - 'accDay': list
                日精度评估结果部署路径列表
            - 'accMonth': list
                月精度评估结果部署路径列表

        See Also
        --------
        returnDeploymentPath : 获取所有部署文件路径（去重后）

        Examples
        --------
        >>> from datetime import datetime
        >>> import pandas as pd
        >>>
        >>> # 创建路径参数实例并配置
        >>> path = CParamsPath()
        >>> path.deployment = {
        ...     'deployRoot': ['/deploy/path1', '/deploy/path2'],
        ...     'meteo': {
        ...         'PATH': 'meteo/{staID}/{year:04d}{month:02d}',
        ...         'FILENAME': 'meteo_{staID}_{year:04d}{month:02d}{day:02d}_{hour:02d}.csv'
        ...     },
        ...     'power': {
        ...         'PATH': 'power/{staType}/{year:04d}{month:02d}',
        ...         'FILENAME': 'power_{staID}_{year:04d}{month:02d}{day:02d}_{hour:02d}.csv'
        ...     },
        ...     'acc': {
        ...         'DAY': {
        ...             'PATH': 'accuracy/daily/{year:04d}{month:02d}',
        ...             'FILENAME': 'acc_day_{staID}_{year:04d}{month:02d}{day:02d}.csv'
        ...         },
        ...         'MONTH': {
        ...             'PATH': 'accuracy/monthly/{year:04d}',
        ...             'FILENAME': 'acc_month_{staID}_{year:04d}{month:02d}.csv'
        ...         }
        ...     }
        ... }
        >>>
        >>> # 生成部署路径
        >>> start_date = pd.Timestamp('2023-05-15 00:00:00')
        >>> end_date = pd.Timestamp('2023-05-16 00:00:00')
        >>> deploy_paths = path.setDeploymentPath(
        ...     staId='ST001',
        ...     staType='WD',
        ...     taskDateStart=start_date,
        ...     taskDateEnd=end_date
        ... )
        >>>
        >>> # 查看功率数据部署路径
        >>> print(deploy_paths['power'])
        ['/deploy/path1/power/WD/202305/power_ST001_20230515_0000.csv',
         '/deploy/path2/power/WD/202305/power_ST001_20230515_0000.csv']

        Notes
        -----
        - 返回的路径已去重
        - 路径按配置的部署根目录顺序排列
        - 部署路径通常用于最终结果的发布和共享
        - 如果某个路径在多个部署根目录下存在，会返回所有实例
        - 部署文件的命名和目录结构遵循配置的模板
        """
        deploymentPath = dict()
        deploymentPath.update({
            "meteo": [],
            "power": [],
            "accDay": [],
            "accMonth": []
        })
        for root in self.deployment['deployRoot']:
            meteoPath = os.path.join(
                root,
                self.deployment['meteo']['PATH'].format(
                    staID=staId,
                    year=taskDateStart.year,
                    month=taskDateStart.month,
                ),
                self.deployment['meteo']['FILENAME'].format(
                    duration=240, #ceil((taskDateEnd - taskDateStart).total_seconds() / 3600),
                    yearS=taskDateStart.year,
                    monthS=taskDateStart.month,
                    dayS=taskDateStart.day,
                    hourS=taskDateStart.hour,
                    minuteS=taskDateStart.minute,
                    yearE=(taskDateStart + pd.Timedelta(hours=240) - pd.Timedelta(minutes=15)).year,
                    monthE=(taskDateStart + pd.Timedelta(hours=240) - pd.Timedelta(minutes=15)).month,
                    dayE=(taskDateStart + pd.Timedelta(hours=240) - pd.Timedelta(minutes=15)).day,
                    hourE=(taskDateStart + pd.Timedelta(hours=240) - pd.Timedelta(minutes=15)).hour,
                    minuteE=(taskDateStart + pd.Timedelta(hours=240) - pd.Timedelta(minutes=15)).minute,
                )
            )
            powerPath = os.path.join(
                root,
                self.deployment['power']['PATH'].format(
                    staID=staId,
                    staType=staType,
                    year=taskDateStart.year,
                    month=taskDateStart.month,
                ),
                self.deployment['power']['FILENAME'].format(
                    staType=staType,
                    duration=ceil((taskDateEnd - taskDateStart).total_seconds() / 3600),
                    yearS=taskDateStart.year,
                    monthS=taskDateStart.month,
                    dayS=taskDateStart.day,
                    hourS=taskDateStart.hour,
                    minuteS=taskDateStart.minute,
                    yearE=taskDateEnd.year,
                    monthE=taskDateEnd.month,
                    dayE=taskDateEnd.day,
                    hourE=taskDateEnd.hour,
                    minuteE=taskDateEnd.minute,
                )
            )
            accDayPath = os.path.join(
                root,
                self.deployment['acc']['DAY']['PATH'].format(
                    staID=staId,
                    staType=staType,
                    year=taskDateStart.year,
                    month=taskDateStart.month,
                ),
                self.deployment['acc']['DAY']['FILENAME'].format(
                    staType=staType,
                    duration=ceil((taskDateEnd - taskDateStart).total_seconds() / 3600),
                    yearS=taskDateStart.year,
                    monthS=taskDateStart.month,
                    dayS=taskDateStart.day,
                    yearE=taskDateEnd.year,
                    monthE=taskDateEnd.month,
                    dayE=taskDateEnd.day,
                )
            )
            accMonthPath = os.path.join(
                root,
                self.deployment['acc']['MONTH']['PATH'].format(
                    staID=staId,
                    staType=staType,
                    year=taskDateStart.year,
                    month=taskDateStart.month,
                ),
                self.deployment['acc']['MONTH']['FILENAME'].format(
                    staType=staType,
                    duration=ceil((taskDateEnd - taskDateStart).total_seconds() / 3600),
                    yearS=taskDateStart.year,
                    monthS=taskDateStart.month,
                    yearE=taskDateEnd.year,
                    monthE=taskDateEnd.month,
                )
            )

            deploymentPath['meteo'].append(meteoPath)
            deploymentPath['power'].append(powerPath)
            deploymentPath['accDay'].append(accDayPath)
            deploymentPath['accMonth'].append(accMonthPath)

        deploymentPathUnique = dict()
        deploymentPathUnique.update({
            "meteo": list(),
            "power": list(),
            "accDay": list(),
            "accMonth": list(),
        })

        [deploymentPathUnique['meteo'].append(path) for path in deploymentPath['meteo'] if
         path not in deploymentPathUnique['meteo']]
        [deploymentPathUnique['power'].append(path) for path in deploymentPath['power'] if
         path not in deploymentPathUnique['power']]
        [deploymentPathUnique['accDay'].append(path) for path in deploymentPath['accDay'] if
         path not in deploymentPathUnique['accDay']]
        [deploymentPathUnique['accMonth'].append(path) for path in deploymentPath['accMonth'] if
         path not in deploymentPathUnique['accMonth']]

        return deploymentPathUnique

    def returnInputPath(self) -> Dict[str, Union[Dict[str, List[str]], List[str]]]:
        """获取所有输入文件路径。

        根据配置的输入路径模板，生成所有输入文件的完整路径，并去除重复项。

        Returns
        -------
        dict
            包含输入文件路径的字典，结构为：
            {
                'meteo': {
                    'business': [业务数据路径1, 业务数据路径2, ...],
                    'original': [原始数据路径1, 原始数据路径2, ...]
                },
                'obs': [观测数据路径1, 观测数据路径2, ...]
            }

            - 'meteo': dict
                气象数据相关路径，包含 'business' 和 'original' 两个子键
            - 'obs': list
                观测数据路径列表

        See Also
        --------
        setInputPath : 设置输入路径模板

        Examples
        --------
        >>> path = CParamsPath()
        >>> path.inPath = {
        ...     'root': ['/data/input1', '/data/input2'],
        ...     'meteo': {
        ...         'business': 'meteo/business',
        ...         'original': 'meteo/original'
        ...     },
        ...     'obs': 'obs'
        ... }
        >>> input_paths = path.returnInputPath()
        >>> print(input_paths['meteo']['business'])
        ['/data/input1/meteo/business', '/data/input2/meteo/business']

        Notes
        -----
        - 返回的路径已去重
        - 路径按配置的根目录顺序排列
        - 如果某个路径在多个根目录下存在，会返回所有实例
        """
        inputPath = dict()
        inputPath.update({
            "meteo": {
                "business": list(),
                "original": list(),
            },
            "obs": list(),
        })
        for root in self.inPath['root']:
            businessPath = os.path.join(
                root,
                self.inPath['meteo']['business']
            )
            originalPath = os.path.join(
                root,
                self.inPath['meteo']['original']
            )
            obsPath = os.path.join(
                root,
                self.inPath['obs']
            )
            inputPath['meteo']['business'].append(businessPath)
            inputPath['meteo']['original'].append(originalPath)
            inputPath['obs'].append(obsPath)

        inputPathUnique = dict()
        inputPathUnique.update({
            "meteo": {
                "business": list(),
                "original": list(),
            },
            "obs": list(),
        })

        [inputPathUnique['meteo']['business'].append(path) for path in inputPath['meteo']['business'] if
         path not in inputPathUnique['meteo']['business']]
        [inputPathUnique['meteo']['original'].append(path) for path in inputPath['meteo']['original'] if
         path not in inputPathUnique['meteo']['original']]
        [inputPathUnique['obs'].append(path) for path in inputPath['obs'] if path not in inputPathUnique['obs']]

        return inputPathUnique

    def returnOutputPath(self) -> Dict[str, List[str]]:
        """获取所有输出文件路径。

        根据配置的输出路径模板，生成所有输出文件的完整路径，并去除重复项。

        Returns
        -------
        dict
            包含输出文件路径的字典，键为路径类型，值为路径列表。

            - 'meteo': list
                气象数据输出路径列表
            - 'power': list
                功率数据输出路径列表
            - 'acc': list
                精度评估结果路径列表
            - 'log': list
                日志文件路径列表
            - 'model': list
                模型文件路径列表
            - 'hash': list
                哈希文件路径列表
            - 'key': list
                密钥文件路径列表

        See Also
        --------
        setOutputPath : 设置输出路径模板

        Examples
        --------
        >>> path = CParamsPath()
        >>> path.outPath = {
        ...     'root': ['/data/output1', '/data/output2'],
        ...     'meteo': 'meteo',
        ...     'power': 'power',
        ...     'acc': 'accuracy',
        ...     'log': 'logs',
        ...     'model': 'models',
        ...     'hash': 'hashes',
        ...     'key': 'keys'
        ... }
        >>> output_paths = path.returnOutputPath()
        >>> print(output_paths['model'])
        ['/data/output1/models', '/data/output2/models']

        Notes
        -----
        - 返回的路径已去重
        - 路径按配置的根目录顺序排列
        - 如果某个路径在多个根目录下存在，会返回所有实例
        """
        outputPath = dict()
        outputPath.update({
            "meteo": list(),
            "power": list(),
            "acc": list(),
            "log": list(),
            "model": list(),
            "hash": list(),
            "key": list()
        })
        for root in self.outPath['root']:
            meteoPath = os.path.join(
                root,
                self.outPath['meteo']
            )
            powerPath = os.path.join(
                root,
                self.outPath['power']
            )
            accPath = os.path.join(
                root,
                self.outPath['acc']
            )
            logPath = os.path.join(
                root,
                self.outPath['log']
            )
            modelPath = os.path.join(
                root,
                self.outPath['model']
            )
            hashPath = os.path.join(
                root,
                self.outPath['hash']
            )
            keyPath = os.path.join(
                root,
                self.outPath['key']
            )
            outputPath['meteo'].append(meteoPath)
            outputPath['power'].append(powerPath)
            outputPath['acc'].append(accPath)
            outputPath['log'].append(logPath)
            outputPath['model'].append(modelPath)
            outputPath['hash'].append(hashPath)
            outputPath['key'].append(keyPath)

        outputPathUnique = dict()
        outputPathUnique.update({
            "meteo": list(),
            "power": list(),
            "acc": list(),
            "log": list(),
            "model": list(),
            "hash": list(),
            "key": list()
        })

        [outputPathUnique['meteo'].append(path) for path in outputPath['meteo'] if
         path not in outputPathUnique['meteo']]
        [outputPathUnique['power'].append(path) for path in outputPath['power'] if
         path not in outputPathUnique['power']]
        [outputPathUnique['acc'].append(path) for path in outputPath['acc'] if path not in outputPathUnique['acc']]
        [outputPathUnique['log'].append(path) for path in outputPath['log'] if path not in outputPathUnique['log']]
        [outputPathUnique['model'].append(path) for path in outputPath['model'] if
         path not in outputPathUnique['model']]
        [outputPathUnique['hash'].append(path) for path in outputPath['hash'] if path not in outputPathUnique['hash']]
        [outputPathUnique['key'].append(path) for path in outputPath['key'] if path not in outputPathUnique['key']]

        return outputPathUnique

    def returnDeploymentPath(self) -> Dict[str, List[str]]:
        """获取所有部署文件路径。

        根据配置的部署路径模板，生成所有部署文件的完整路径，并去除重复项。
        部署路径通常用于最终结果的发布和共享。

        Returns
        -------
        dict
            包含部署文件路径的字典，键为路径类型，值为路径列表。

            - 'meteo': list
                气象数据部署路径列表
            - 'power': list
                功率数据部署路径列表
            - 'accDay': list
                日精度评估结果部署路径列表
            - 'accMonth': list
                月精度评估结果部署路径列表

        See Also
        --------
        setDeploymentPath : 设置部署路径模板

        Examples
        --------
        ```python
        >>> path = CParamsPath()
        >>> path.deployment = {
        ...     'deployRoot': ['/deploy/path1', '/deploy/path2'],
        ...     'meteo': {
        ...         'PATH': 'meteo',
        ...         'FILENAME': 'output_meteo.csv'
        ...     },
        ...     'power': {
        ...         'PATH': 'power',
        ...         'FILENAME': 'output_power.csv'
        ...     },
        ...     'acc': {
        ...         'DAY': {
        ...             'PATH': 'accuracy/day',
        ...             'FILENAME': 'acc_day.csv'
        ...         },
        ...         'MONTH': {
        ...             'PATH': 'accuracy/month',
        ...             'FILENAME': 'acc_month.csv'
        ...         }
        ...     }
        ... }
        >>> deploy_paths = path.returnDeploymentPath()
        >>> print(deploy_paths['meteo'])
        ['/deploy/path1/meteo/output_meteo.csv', '/deploy/path2/meteo/output_meteo.csv']
        ```

        Notes
        -----
        - 返回的路径已去重
        - 路径按配置的部署根目录顺序排列
        - 部署路径通常用于最终结果的发布和共享
        - 如果某个路径在多个部署根目录下存在，会返回所有实例
        """
        deploymentPath = dict()
        deploymentPath.update({
            "meteo": [],
            "power": [],
            "accDay": [],
            "accMonth": []
        })
        for root in self.deployment['deployRoot']:
            meteoPath = os.path.join(
                root,
                self.deployment['meteo']['PATH'],
                self.deployment['meteo']['FILENAME']
            )
            powerPath = os.path.join(
                root,
                self.deployment['power']['PATH'],
                self.deployment['power']['FILENAME']
            )
            accDayPath = os.path.join(
                root,
                self.deployment['acc']['DAY']['PATH'],
                self.deployment['acc']['DAY']['FILENAME']
            )
            accMonthPath = os.path.join(
                root,
                self.deployment['acc']['MONTH']['PATH'],
                self.deployment['acc']['MONTH']['FILENAME']
            )

            deploymentPath['meteo'].append(meteoPath)
            deploymentPath['power'].append(powerPath)
            deploymentPath['accDay'].append(accDayPath)
            deploymentPath['accMonth'].append(accMonthPath)

        deploymentPathUnique = dict()
        deploymentPathUnique.update({
            "meteo": list(),
            "power": list(),
            "accDay": list(),
            "accMonth": list(),
        })

        [deploymentPathUnique['meteo'].append(path) for path in deploymentPath['meteo'] if
         path not in deploymentPathUnique['meteo']]
        [deploymentPathUnique['power'].append(path) for path in deploymentPath['power'] if
         path not in deploymentPathUnique['power']]
        [deploymentPathUnique['accDay'].append(path) for path in deploymentPath['accDay'] if
         path not in deploymentPathUnique['accDay']]
        [deploymentPathUnique['accMonth'].append(path) for path in deploymentPath['accMonth'] if
         path not in deploymentPathUnique['accMonth']]

        return deploymentPathUnique


class CStaParams:
    """站点参数类

    存储和管理单个站点的特定参数，包括站点元数据、预测时效和算法配置等。

    Attributes:
        staId (str): 站点唯一标识符。
        staName (str): 站点名称。
        staLon (float): 站点经度，单位：度。
        staLat (float): 站点纬度，单位：度。
        staAlt (float): 站点海拔高度，单位：米。
        staCap (float): 站点装机容量，单位：千瓦(kW)。
        staType (str): 站点类型，如 "PV"、"WD" 等。
        timeLiness (List[str]): 预测时效列表，如 ["UST", "ST", "MT"]。
        timeLinessFcHour (List[int]): 预测时效对应的小时数列表，与 timeLiness 一一对应。
        algorithm (Dict[str, List[str]]): 算法配置字典，格式为 {"算法名": ["版本1", "版本2", ...]}。
        dataset (List[str]): 数据集名称列表，指定该站点使用的数据源。
        accuracy (List[str]): 精度评估算法名称列表，用于评估该站点的模型性能。
        postProcess (List[str]): 后处理算法名称列表，用于对该站点的预测结果进行后处理。

    Example:
        ```python
        # 创建站点参数实例
        station = CStaParams()

        # 配置站点参数
        station.staId = "S001"
        station.staName = "北京太阳能电站"
        station.staLon = 116.4
        station.staLat = 39.9
        station.staAlt = 43.5
        station.staCap = 5000.0  # 5MW
        station.staType = "PV"
        station.timeLiness = ["UST", "ST"]
        station.timeLinessFcHour = [6, 72]  # UST: 6小时, ST: 72小时
        station.algorithm = {"catboost": ["v1.0"], "xgboost": ["v2.0"]}
        station.dataset = ["EC_IFS"]
        station.accuracy = ["mae", "rmse"]
        station.postProcess = ["smoothing", "calibration"]

        # 通过字典方式访问属性
        print(f"站点ID: {station['staId']}")
        print(f"经度: {station['staLon']}, 纬度: {station['staLat']}")
        ```

    Note:
        - timeLiness 和 timeLinessFcHour 必须一一对应
        - 站点坐标使用 WGS84 坐标系
        - 容量单位统一为千瓦(kW)
    """

    def __getitem__(self, item: str) -> Any:
        """允许通过字典方式访问属性。

        Args:
            item (str): 属性名称

        Returns:
            Any: 属性值

        Raises:
            KeyError: 当属性不存在时引发
        """
        return self.__dict__[item]

    def __init__(self):
        """初始化所有站点参数为默认值。"""
        self.staId: str = ""
        # 站点 ID
        self.staName: str = ""
        # 站点名称
        self.staLon: float = 0.0
        # 站点经度
        self.staLat: float = 0.0
        # 站点纬度
        self.staAlt: float = 0.0
        # 站点海拔
        self.staCap: float = 0.0
        # 站点容量
        self.staType: str = ""
        # 站点类型
        self.timeLiness: List[str] = list()
        # 预测时效列表
        self.timeLinessFcHour: List[int] = list()
        # 预测时效预测时长列表，该列表需要与预测时效列表（self.timeLiness）一一对应

        self.algorithm: Dict[str, List[str]] = dict()
        # 算法列表 {算法名: [版本1, 版本2]}
        self.dataset: List[str] = list()
        # 数据集名称列表
        self.accuracy: List[str] = list()
        # 精度评估算法名称列表
        self.postProcess: List[str] = list()
        # 后处理算法名称列表


class CParams:
    """GreenPulse 应用主参数管理类。

    聚合所有参数配置，提供统一的参数管理接口，包括参数解析、验证和站点参数管理。
    支持从命令行参数、配置文件和数据库加载配置，并按照优先级合并参数。

    Attributes
    ----------
    init : CParamsInit
        系统初始化参数实例，包含日志级别、数据库连接等配置。
    res : CParamsResource
        计算资源配置参数实例，包含CPU、GPU、内存等资源配置。
    task : CParamsTask
        任务执行参数实例，包含任务ID、类型、日期范围等任务相关配置。
    path : CParamsPath
        文件路径配置实例，管理输入、输出和部署路径。
    staParams : Dict[str, CStaParams]
        站点参数字典，键为站点任务ID或站点ID，值为站点参数实例。

    See Also
    --------
    CParamsInit : 系统初始化参数类
    CParamsResource : 计算资源配置参数类
    CParamsTask : 任务参数类
    CParamsPath : 路径参数类
    CStaParams : 站点参数类

    Notes
    -----
    参数解析优先级: 命令行参数 > 配置文件 > 默认值

    - 使用前需要先调用 `paramsParse` 方法解析参数
    - 站点参数可以通过 `addStaFromDB` 或 `addStaFromConfig` 方法添加
    - 使用完成后应调用 `clean` 方法释放资源

    Examples
    --------
    >>> from params import CParams, Arg
    >>> import logging
    >>>
    >>> # 初始化日志记录器
    >>> logging.basicConfig(level=logging.INFO)
    >>> logger = logging.getLogger(__name__)
    >>>
    >>> # 创建参数实例
    >>> params = CParams()
    >>>
    >>> # 创建并配置参数解析器
    >>> arg_parser = Arg(description="GreenPulse 参数解析器")
    >>>
    >>> # 解析命令行参数
    >>> args = arg_parser.arg_parse()
    >>>
    >>> try:
    ...     # 解析参数
    ...     params.paramsParse(args, logger)
    ...
    ...     # 使用参数
    ...     logger.info(f"任务ID: {params.task.taskID}")
    ...     logger.info(f"CPU核心数: {params.res.CPU}")
    ...
    ...     # 添加站点参数
    ...     if params.init.database:
    ...         params.addStaFromDB(logger)
    ...
    ...     # 处理站点参数
    ...     for sta_id, sta_param in params.staParams.items():
    ...         logger.info(f"站点 {sta_id} 名称: {sta_param.staName}")
    ...
    ... except Exception as e:
    ...     logger.critical(f"参数处理失败: {e}", exc_info=True)
    ...     raise
    ... finally:
    ...     # 清理资源
    ...     params.clean(logger)
    """

    def __getitem__(self, item: str) -> Any:
        """允许通过字典方式访问属性。

        Args:
            item (str): 属性名称，可以是 'init'、'res'、'task'、'path' 或 'staParams'

        Returns:
            Any: 对应的属性值

        Raises:
            KeyError: 当属性不存在时引发
        """
        return self.__dict__[item]

    def __init__(self):
        """初始化 CParams 实例及其所有子参数类。

        创建并初始化所有参数子类的实例，包括系统初始化参数、计算资源参数、
        任务参数、路径参数和站点参数字典。

        Notes
        -----
        初始化后的参数对象包含以下属性：
        - init: CParamsInit 实例，包含系统初始化参数
        - res: CParamsResource 实例，包含计算资源配置
        - task: CParamsTask 实例，包含任务参数
        - path: CParamsPath 实例，包含路径配置
        - staParams: 空字典，用于存储站点参数
        """
        self.init: CParamsInit = CParamsInit()
        self.res: CParamsResource = CParamsResource()
        self.task: CParamsTask = CParamsTask()
        self.path: CParamsPath = CParamsPath()
        self.staParams: Dict[str, CStaParams] = dict()  # 存储站点参数，键为站点任务 ID 或 站点 ID

    def addStaFromConfig(
            self,
            taskId: str,
            staId: str,
            staType: str,
            staName: str,
            staLon: float,
            staLat: float,
            staAlt: float,
            staCap: float,
            timeLiness: List[str],
            algorithm: Dict[str, List[str]],
            dataset: List[str],
            accuracy: List[str],
            postProcess: List[str]
    ):
        """从配置文件添加站点参数。

        根据提供的参数创建并添加一个站点参数实例到 staParams 字典中。

        Parameters
        ----------
        taskId : str
            任务 ID。
        staId : str
            站点唯一标识符。
        staType : str
            站点类型，如 "PV"、"WD" 等。
        staName : str
            站点名称。
        staLon : float
            站点经度，单位：度。
        staLat : float
            站点纬度，单位：度。
        staAlt : float
            站点海拔高度，单位：米。
        staCap : float
            站点装机容量，单位：千瓦(kW)。
        timeLiness : List[str]
            预测时效列表，如 ["UST", "ST", "MT"]。
        algorithm : Dict[str, List[str]]
            算法配置字典，格式为 {"算法名": ["版本1", "版本2", ...]}。
        dataset : List[str]
            数据集名称列表。
        accuracy : List[str]
            精度评估算法名称列表。
        postProcess : List[str]
            后处理算法名称列表。

        Examples
        --------
        >>> params = CParams()
        >>> params.addStaFromConfig(
        ...     staId="S001",
        ...     staType="PV",
        ...     staName="北京太阳能电站",
        ...     staLon=116.4,
        ...     staLat=39.9,
        ...     staAlt=43.5,
        ...     staCap=5000.0,
        ...     timeLiness=["UST", "ST"],
        ...     algorithm={"catboost": ["v1.0"], "xgboost": ["v2.0"]},
        ...     dataset=["EC_IFS"],
        ...     accuracy=["mae", "rmse"],
        ...     postProcess=["smoothing"]
        ... )
        >>> print(f"已添加站点: {params.staParams['TASK001_S001'].staName}")

        Notes
        -----
        - 所有参数都会经过类型检查，但不会验证其有效性
        - 站点坐标应使用 WGS84 坐标系
        """
        newNode = CStaParams()
        newNode.staId = staId
        newNode.staType = staType
        newNode.staName = staName
        newNode.staLon = staLon
        newNode.staLat = staLat
        newNode.staAlt = staAlt
        newNode.staCap = staCap
        newNode.timeLiness = timeLiness
        newNode.algorithm = algorithm
        newNode.dataset = dataset
        for acc in accuracy:
            newNode.accuracy.append(AccRule[acc])
        newNode.postProcess = postProcess

        self.staParams.update({taskId: newNode})

    def addStaFromDB(self, logger: logging.Logger):
        """从数据库加载站点参数。

        根据当前任务ID从数据库查询站点信息，并添加到 staParams 字典中。
        需要先初始化数据库连接并设置 task.taskID。

        Parameters
        ----------
        logger : logging.Logger
            日志记录器，用于记录信息、警告和错误。

        Raises
        ------
        ValueError
            如果数据库连接未初始化或 taskID 未设置。

        Examples
        --------
        >>> params = CParams()
        >>> # 必须先初始化数据库连接和任务ID
        >>> params.init.database = True
        >>> params.init.databaseURL = "localhost"
        >>> params.init.databaseName = "greenpulse"
        >>> params.init.databaseUser = "user"
        >>> params.init.databasePassword = "password"
        >>> params.init.databasePort = "5432"
        >>> params.task.taskID = ["TASK001"]
        >>>
        >>> # 添加站点参数
        >>> try:
        ...     params.addStaFromDB(logger)
        ...     for sta_id, sta_param in params.staParams.items():
        ...         print(f"站点 {sta_id}: {sta_param.staName}")
        ... except Exception as e:
        ...     logger.error(f"添加站点参数失败: {e}")

        Notes
        -----
        - 需要先调用 paramsParse 方法解析参数并初始化数据库连接
        - 会从数据库查询任务状态和站点信息
        - 如果任务ID不存在或站点信息不完整，会记录错误但不会中断程序
        - 从数据库加载的站点参数会继承任务的算法、数据集等配置
        """
        if self.init.dbcursor is None:
            logger.critical("数据库连接未初始化")
            raise ValueError("数据库连接未初始化")
        if self.task.taskID is None:
            logger.critical("从数据库添加站点时 taskID 不能为空")
            raise ValueError("从数据库添加站点时 taskID 不能为空")

        for taskId in self.task.taskID:
            try:
                self.init.dbcursor.execute(
                    "SELECT station_ids, power_type, algo_name, data_type FROM task_status WHERE id = %s;", (taskId,))
                taskInfo = self.init.dbcursor.fetchone()
                if taskInfo is None:
                    logger.error(f"数据库查询错误: 任务 ID {taskId} 未找到")
                    continue  # 或者可以考虑抛出异常，但是异常会中断任务，需要考虑

                newNode = CStaParams()
                newNode.staId = taskInfo[0]

                if taskInfo[1] == 1:
                    newNode.staType = "WD"
                elif taskInfo[1] == 2:
                    newNode.staType = "PV"
                else:
                    logger.error(f"数据库查询错误: 任务 {taskId} 的未知电站类型 {taskInfo[1]}")
                    continue  # 或者可以考虑抛出异常，但是异常会中断任务，需要考虑

                if newNode.staType == "PV" or newNode.staType == "WD":
                    self.init.dbcursor.execute(
                        "SELECT name, lon, lat, type, cape, ass_rule FROM solar_station WHERE id = %s;",
                        (newNode.staId,))
                # 数据库中风光同一个站点表
                # elif newNode.staType == "WD":
                #    self.init.dbcursor.execute(
                #        "SELECT name, lon, lat, type, cape, ass_rule FROM wind_station WHERE id = %s;",
                #        (newNode.staId,))
                else:
                    logger.error(f"数据库查询错误: 任务 {taskId} 的未知电站类型 {taskInfo[1]}")
                    continue  # 或者可以考虑抛出异常，但是异常会中断任务，需要考虑

                staInfo = self.init.dbcursor.fetchone()
                if staInfo is None:
                    logger.error(f"数据库查询错误: 站点 ID {newNode.staId} 未找到")
                    continue  # 或者可以考虑抛出异常，但是异常会中断任务，需要考虑
                for staInfoOne in staInfo:
                    if staInfoOne is None:
                        logger.error(f"数据库查询错误: 站点 ID {newNode.staId} {staInfoOne} 未找到")
                        raise ValueError(f"数据库查询错误: 站点 ID {newNode.staId} {staInfoOne} 未找到")

                newNode.staName = staInfo[0]
                newNode.staLon = staInfo[1]
                newNode.staLat = staInfo[2]
                newNode.staAlt = 0  # 数据库中没有海拔信息，暂时设为0
                newNode.staCap = staInfo[4]
                algo_name = taskInfo[2] if taskInfo[2] else "baseline"  # 处理 algo_name 可能为 None 的情况

                if algo_name.endswith("_post"):
                    algo_name = algo_name[:-5]
                    if self.task.taskType == TaskType.FC:
                        self.task.taskType = TaskType.PFC
                    elif self.task.taskType == TaskType.HFC:
                        self.task.taskType = TaskType.PHFC
                    elif self.task.taskType == TaskType.FT or self.task.taskType == TaskType.UPT:
                        self.task.taskType = TaskType.PT

                newNode.algorithm = {algo_name: ["last"]}  # 默认使用最新版本

                if taskInfo[3] == 1:
                    timeLiness = ["UST"]
                    timeLinessFcHour = [TimeLinessFcHour.UST.value]
                elif taskInfo[3] == 2:
                    timeLiness = ["ST"]
                    timeLinessFcHour = [TimeLinessFcHour.ST.value]
                elif taskInfo[3] == 3:
                    timeLiness = ["MT"]
                    timeLinessFcHour = [TimeLinessFcHour.MT.value]
                elif taskInfo[3] == 4:
                    timeLiness = ["SS"]
                    timeLinessFcHour = [TimeLinessFcHour.SS.value]
                else:
                    raise ValueError(f"数据库查询错误: 任务 {taskId} 的未知数据类型 {taskInfo[3]}")
                newNode.timeLiness = timeLiness
                newNode.timeLinessFcHour = timeLinessFcHour

                # 从 task 参数继承数据集、精度和后处理算法列表
                newNode.dataset = self.task.dataset
                newNode.accuracy = [AccRule(staInfo[5])]
                newNode.postProcess = self.task.postProcess

                self.staParams.update({taskId: newNode})  # 使用站点 ID 作为键
            except psycopg2.Error as e:
                task_id = taskInfo[0] if taskInfo is not None else 'N/A'
                logger.error(f"数据库查询任务 {taskId} 或站点 {task_id} 时出错: {e}")
                continue  # 或者可以考虑抛出异常，但是异常会中断任务，需要考虑

    def paramsParse(self, args: argparse.Namespace, logger: logging.Logger):
        """解析命令行参数和配置文件，初始化参数配置。

        按照以下优先级解析参数：
        1. 从配置文件加载默认参数
        2. 使用命令行参数覆盖配置文件中的参数
        3. 初始化数据库连接（如果启用）
        4. 验证必要的参数

        Parameters
        ----------
        args : argparse.Namespace
            由 `Arg.arg_parse()` 返回的命令行参数对象。
        logger : logging.Logger
            日志记录器，用于记录解析过程和错误信息。

        Raises
        ------
        FileNotFoundError
            如果配置文件不存在。
        yaml.YAMLError
            如果配置文件格式错误。
        ValueError
            如果必要参数缺失或无效。

        Examples
        --------
        >>> from params import CParams, Arg
        >>> import logging
        >>>
        >>> # 配置日志
        >>> logging.basicConfig(level=logging.INFO)
        >>> logger = logging.getLogger(__name__)
        >>>
        >>> # 创建参数实例
        >>> params = CParams()
        >>>
        >>> # 创建并配置参数解析器
        >>> arg_parser = Arg(description="GreenPulse 参数解析器")
        >>>
        >>> # 解析命令行参数
        >>> args = arg_parser.arg_parse(["--config", "config/GreenPulse.yaml"])
        >>>
        >>> # 解析参数
        >>> try:
        ...     params.paramsParse(args, logger)
        ...     logger.info("参数解析成功")
        ... except Exception as e:
        ...     logger.critical(f"参数解析失败: {e}")
        ...     raise

        Notes
        -----
        - 配置文件格式应为 YAML
        - 命令行参数会覆盖配置文件中的同名参数
        - 如果启用了数据库连接，会尝试初始化数据库连接
        - 会验证必要的参数是否已设置
        """
        # 读取参数
        # 配置文件必须存在，如果有命令行参数，优先使用命令行参数
        logger.info(f"读取配置文件: {args.config}")
        if args.config and os.path.exists(args.config):
            try:
                with open(args.config, "r", encoding="utf-8") as yaml_file:
                    yamlParams = yaml.safe_load_all(yaml_file)
                    for yamlParam in yamlParams:
                        if yamlParams:  # 确保文件不是空的
                            logger.debug(yamlParam)
                            for Ckey, Cvalue in yamlParam.items():
                                if Ckey in self.__dict__ and isinstance(Cvalue, dict):
                                    for key, value in Cvalue.items():
                                        # 检查属性是否存在于对应的参数类中
                                        if hasattr(self.__dict__[Ckey], key):
                                            self.__dict__[Ckey].__dict__[key] = value
                                        else:
                                            logger.warning(f"配置文件中发现未知参数 {Ckey}.{key}，已忽略。")
                                elif Ckey in self.__dict__:
                                    logger.warning(f"配置文件中发现未知参数类别 {Ckey}，已忽略。")
            except yaml.YAMLError as e:
                logger.critical(f"读取或解析配置文件 {args.config} 失败: {e}")
                raise yaml.YAMLError(f"读取或解析配置文件 {args.config} 失败: {e}") from e
            except Exception as e:
                logger.critical(f"处理配置文件 {args.config} 时发生意外错误: {e}")
                raise Exception(f"处理配置文件 {args.config} 时发生意外错误: {e}") from e

            logger.info("读取配置文件成功")
            logger.info("读取命令行参数并覆盖配置")
            logger.debug(f"命令行参数: {args}")
            for key, value in args.__dict__.items():
                for keyParamClass, valueParamClass in self.__dict__.items():
                    if keyParamClass != "staParams" and key in valueParamClass.__dict__ and value:
                        self.__dict__[keyParamClass].__dict__[key] = value
            logger.info("读取命令行参数成功")
        else:
            logger.critical(f"配置文件 {args.config} 不存在")
            raise FileNotFoundError(f"配置文件 {args.config} 不存在")

        # 设置日志级别
        log_levels = {
            'NOTSET': logging.NOTSET,
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        # self.init.logLevel 可能已经被命令行参数覆盖
        if isinstance(self.init.logLevel, str):
            log_level_str = self.init.logLevel.upper()
        elif isinstance(self.init.logLevel, list):
            log_level_str = self.init.logLevel[0]
        else:
            logger.warning(f"无效的日志级别: {self.init.logLevel}，将使用 INFO 级别。")
            log_level_str = "INFO"
        log_level = log_levels.get(log_level_str, logging.INFO)  # 确保有默认值
        self.init.logLevel = log_level

        logger.info(f"设置日志级别为: {self.init.logLevel}")
        logger.setLevel(self.init.logLevel)

        # 校验日期参数
        if self.task.dateRange[0] is None or self.task.dateRange[1] is None:
            logger.critical("日期参数传输错误: 日期范围必须同时指定")
            raise ValueError("日期参数传输错误: 日期范围必须同时指定")

        # 初始化数据库连接（如果启用）
        if self.init.database:
            logger.info("初始化数据库连接")
            try:
                self.init.dbconn = psycopg2.connect(
                    dbname=self.init.databaseName,
                    user=self.init.databaseUser,
                    password=self.init.databasePassword,
                    host=self.init.databaseURL,
                    port=self.init.databasePort,
                )
                self.init.dbcursor = self.init.dbconn.cursor()
                logger.info("数据库连接初始化完成")
            except psycopg2.Error as e:
                logger.critical(f"数据库连接失败: {e}")
                # 根据需要决定是退出还是继续（禁用数据库功能）
                self.init.database = False
                self.init.dbconn = None
                self.init.dbcursor = None
                # TODO: 服务降级，添加数据库失败备用方案
                # raise ConnectionError(f"数据库连接失败: {e}") from e # 或者抛出异常

        if self.init.database and self.init.dbcursor and self.init.dbconn:
            # 获取任务类型
            taskTypeList = list()
            for taskId in self.task.taskID:
                self.init.dbcursor.execute("SELECT type FROM task_status WHERE id = %s;", (taskId,))
                taskType = self.init.dbcursor.fetchone()
                logger.info(f"数据库查询结果: {taskType}")
                if taskType is None:
                    logger.critical(f"数据库查询错误: 任务 ID {taskId} 未找到任务类型")
                    raise ValueError(f"数据库查询错误: 任务 ID {taskId} 未找到任务类型")
                taskType = TaskType(taskType[0])
                if taskType not in TaskType.__members__.values():
                    logger.critical(f"数据库查询错误: 任务 ID {taskId} 未找到支持的任务类型")
                    raise ValueError(f"数据库查询错误: 任务 ID {taskId} 未找到支持的任务类型")
                taskTypeList.append(taskType)

            taskTypeList = list(set(taskTypeList))
            if len(taskTypeList) > 1:
                logger.critical(f"任务类型不一致: {taskTypeList}")
                raise ValueError(f"任务类型不一致: {taskTypeList}")
            logger.info(f"任务类型: {taskTypeList}")
            self.task.taskType = TaskType(taskTypeList[0])

            # 获取任务时间
            taskDateRangeStart = list()
            taskDateRangeEnd = list()
            if self.task.taskType == TaskType.HFC or self.task.taskType == TaskType.PHFC:
                logger.info(f"获取 {TaskType(self.task.taskType).name} 任务时间: {self.task.taskID}")
                for taskId in self.task.taskID:
                    self.init.dbcursor.execute("SELECT realgo_stime, realgo_etime FROM task_status WHERE id = %s;",
                                               (taskId,))
                    taskTime = self.init.dbcursor.fetchone()
                    if taskTime is None:
                        logger.critical(f"数据库查询错误: 任务 ID {taskId} 未找到任务时间")
                        raise ValueError(f"数据库查询错误: 任务 ID {taskId} 未找到任务时间")
                    taskDateRangeStart.append(taskTime[0])
                    taskDateRangeEnd.append(taskTime[1])
                    logger.info(f"从数据库获取任务时间范围: {taskDateRangeStart} {taskDateRangeEnd}")
            else:
                logger.info(f"获取 {TaskType(self.task.taskType).name} 任务时间: {self.task.taskID}")
                for taskId in self.task.taskID:
                    self.init.dbcursor.execute("SELECT start_time FROM task_status WHERE id = %s;", (taskId,))
                    taskTime = self.init.dbcursor.fetchone()
                    if taskTime is None:
                        logger.critical(f"数据库查询错误: 任务 ID {taskId} 未找到任务时间")
                        raise ValueError(f"数据库查询错误: 任务 ID {taskId} 未找到任务时间")
                    taskDateRangeStart.append(taskTime[0])
                    taskDateRangeEnd.append(taskTime[0])
                    logger.info(f"从数据库获取任务时间: {taskDateRangeStart} {taskDateRangeEnd}")

            if len(taskDateRangeStart) > 0 and len(taskDateRangeEnd) > 0:
                taskDateRangeStart = list(set(taskDateRangeStart))
                taskDateRangeEnd = list(set(taskDateRangeEnd))
                if len(taskDateRangeStart) > 1 or len(taskDateRangeEnd) > 1:
                    logger.critical(f"任务时间不一致: {taskDateRangeStart} {taskDateRangeEnd}")
                    raise ValueError(f"任务时间不一致: {taskDateRangeStart} {taskDateRangeEnd}")
                ###################################################################
                ################## 数据库提取时间为北京时间，该时间为约定 ###############
                ###################################################################
                _taskDateRangeStart = pd.Timestamp(taskDateRangeStart[0], tz="Asia/Shanghai").tz_convert('UTC')
                _taskDateRangeEnd   = pd.Timestamp(taskDateRangeEnd[0], tz="Asia/Shanghai").tz_convert('UTC')
                _taskDateRangeStart = _taskDateRangeStart.replace(second=0, microsecond=0, nanosecond=0)
                _taskDateRangeEnd = _taskDateRangeEnd.replace(second=0, microsecond=0, nanosecond=0)
                # 任务时间统一转换为 UTC 时间
                self.task.dateRange = [_taskDateRangeStart, _taskDateRangeEnd]
            else:
                logger.critical("任务时间参数传输错误")
                raise ValueError("任务时间参数传输错误")

        if TaskType(self.task.taskType) not in TaskType.__members__.values():
            logger.critical(f"任务类型 {self.task.taskType} 错误, 可选的软仵类型为 {TaskType.__members__.values()}")
            raise ValueError(f"任务类型 {self.task.taskType} 错误, 可选的软仵类型为 {TaskType.__members__.values()}")

    def setStaParams(self, logger: logging.Logger):
        """设置站点参数。

        根据任务配置设置各个站点的具体参数，包括预测时效、算法配置等。
        如果启用了数据库连接，会从数据库加载站点信息。

        Parameters
        ----------
        logger : logging.Logger
            日志记录器，用于记录信息、警告和错误。

        Notes
        -----
        - 如果启用了数据库连接，会调用 addStaFromDB 方法从数据库加载站点信息
        - 否则，会使用配置文件中的站点参数
        - 会设置站点的预测时效、算法、数据集等参数
        - 如果站点参数不完整或无效，会记录警告信息
        """
        # 解析 task 级别的算法参数字符串为字典格式
        if isinstance(self.task.algorithm, list) and len(self.task.algorithm) > 0:  # 命令行传入的是 list
            algorithm = dict()
            for item in self.task.algorithm:
                items = item.split(":")
                method = None
                version = None
                if len(items) == 2:
                    method = items[0]
                    version = items[1]
                elif len(items) == 1:
                    method = items[0]
                    version = "last"
                else:
                    logger.critical(f"任务级算法参数解析错误: {item}")
                    raise ValueError(f"任务级算法参数解析错误: {item}")
                if method:
                    if method in algorithm:
                        algorithm[method].append(version)
                    else:
                        algorithm[method] = [version]
            self.task.algorithm = algorithm  # 更新 task 的 algorithm 为字典格式
            logger.debug(f"解析后的任务级算法参数: {self.task.algorithm}")
        elif not isinstance(self.task.algorithm, dict):
            raise ValueError(f"任务级算法参数解析错误: {self.task.algorithm}")

        logger.info("配置站点")
        if self.task.staListFile and os.path.exists(
                self.task.staListFile) and self.init.database is False and (self.task.taskID is None or len(self.task.taskID) == 0):
            logger.info(f"读取站点清单文件: {self.task.staListFile}")
            try:
                with open(self.task.staListFile, "r", encoding="utf-8") as yaml_file:
                    yamlParams = yaml.safe_load_all(yaml_file)
                    for yamlParam in yamlParams:
                        logger.debug(yamlParam)
                        for key, value in yamlParam.items():
                            logger.debug("key: %s, value: %s" % (key, value))
                            # 时效解析
                            if len(self.task.timeLiness) > 0:
                                timeLinessSta = self.task.timeLiness
                            else:
                                timeLinessSta = value["timeLiness"]
                            # 算法解析
                            if "algorithm" in locals():
                                algorithmSta = algorithm
                            else:
                                algorithmSta = value["algorithm"]
                            # 数据集解析
                            if len(self.task.dataset) > 0:
                                datasetSta = self.task.dataset
                            else:
                                datasetSta = value["dataset"]
                            # 精度评估算法解析
                            if len(self.task.accuracy) > 0:
                                accuracySta = self.task.accuracy
                            else:
                                accuracySta = value["accuracy"]
                            # 后处理算法解析
                            if len(self.task.postProcess) > 0:
                                postProcessSta = self.task.postProcess
                            else:
                                postProcessSta = value["postProcess"]
                            self.addStaFromConfig(
                                taskId=self.task.taskID,
                                staId=value["staId"],
                                staType=value["staType"],
                                staName=value["staName"],
                                staLon=value["staLon"],
                                staLat=value["staLat"],
                                staAlt=value["staAlt"],
                                staCap=value["staCap"],
                                timeLiness=timeLinessSta,
                                algorithm=algorithmSta,
                                dataset=datasetSta,
                                accuracy=accuracySta,
                                postProcess=postProcessSta,
                            )
            except yaml.YAMLError as e:
                logger.critical(f"读取或解析站点清单文件 {self.task.staListFile} 失败: {e}")
                raise yaml.YAMLError(f"读取或解析站点清单文件 {self.task.staListFile} 失败: {e}") from e
            except Exception as e:
                logger.critical(f"处理站点清单文件 {self.task.staListFile} 时发生意外错误: {e}")
                raise Exception(f"处理站点清单文件 {self.task.staListFile} 时发生意外错误: {e}") from e

        elif self.init.database and self.task.taskID:
            logger.info(f"从数据库读取站点参数")
            self.addStaFromDB(logger)
            logger.debug(f"从数据库读取的站点参数:")
            for staId, staParam in self.staParams.items():
                logger.debug(f"站点 {staId} 的参数:")
                for key, value in staParam.__dict__.items():
                    logger.debug(f"{key}: {value}")
        else:
            # 数据库和站点文件都未配置或无效
            if not self.init.database and self.task.staListFile and not os.path.exists(self.task.staListFile):
                logger.critical(f"站点配置失败: 站点清单文件 {self.task.staListFile} 不存在，且未启用数据库。")
                raise FileNotFoundError(f"站点清单文件 {self.task.staListFile} 不存在")
            elif not self.init.database and not self.task.staListFile:
                logger.critical("站点配置失败: 未提供站点清单文件，且未启用数据库。")
                raise ValueError("站点配置失败: 必须提供站点清单文件或启用数据库并提供 taskID。")
            elif self.init.database and self.task.taskID is None:
                logger.critical("站点配置失败: 已启用数据库，但未提供 taskID。")
                raise ValueError("站点配置失败: 已启用数据库，但未提供 taskID。")

        if not self.staParams:
            logger.debug(self.staParams)
            logger.critical("站点参数配置完成，但未成功加载任何站点信息。请检查配置。")
            # 可能需要根据业务逻辑决定是否抛出异常
            # raise ValueError("未成功加载任何站点信息。")
        else:
            logger.info(f"站点参数配置成功，共加载 {len(self.staParams)} 个站点。")

    def clean(self, logger: Optional[logging.Logger] = None):
        """清理资源，释放数据库连接等。

        关闭数据库连接并清理相关资源。如果提供了日志记录器，
        会记录清理过程。

        Parameters
        ----------
        logger : logging.Logger, optional
            日志记录器，如果提供则记录清理过程。

        Notes
        -----
        - 会关闭数据库连接（如果已建立）
        - 会清理所有站点参数
        - 可以安全地多次调用此方法
        """
        if self.init.dbcursor:
            try:
                self.init.dbcursor.close()
                self.init.dbcursor = None
            except Exception as e:
                if logger:
                    logger.error(f"关闭数据库游标时出错: {e}")
                else:
                    print(f"Error closing DB cursor: {e}")
        if self.init.dbconn:
            try:
                self.init.dbconn.close()
                self.init.dbconn = None
            except Exception as e:
                if logger:
                    logger.error(f"关闭数据库连接时出错: {e}")
                else:
                    print(f"Error closing DB connection: {e}")
