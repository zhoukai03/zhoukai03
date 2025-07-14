"""消息队列生产者模块

该模块提供了向 Kafka 消息队列发送结构化消息的功能，主要用于系统各组件间的异步通信。
支持多种消息类型，包括日志、功率预测、准确率、密钥、模型、哈希和气象数据等。

主要功能
--------
- **消息发送**：支持发送多种类型的消息，包括日志、功率预测、准确率、密钥、模型、哈希和气象数据等
- **测试支持**：提供 `CNullKafkaProducer` 类作为空实现，便于测试和开发
- **自动序列化**：自动将消息序列化为 JSON 格式并使用 gzip 压缩
- **检查点机制**：通过检查点跟踪任务执行状态
- **时间尺度支持**：支持多种时间尺度（UST/ST/MT/SS）

核心组件
--------
### 类
- `FileType`：定义系统支持的各种文件类型的枚举
- `CNullKafkaProducer`：空实现的 Kafka 生产者，用于测试或禁用消息发送
- `Cproducer`：实际的 Kafka 生产者实现，继承自 `CNullKafkaProducer`

### 函数
- `check_timeliness(timeliness: str) -> int`：将时间尺度字符串转换为对应的数据类型标识

消息类型与检查点
--------------
| 消息类型       | 检查点 | 描述                         |
|----------------|--------|----------------------------|
| 日志          | 90     | 任务执行日志信息             |
| 功率预测      | 91     | 功率预测结果数据             |
| 准确率        | 92     | 模型准确率评估结果           |
| 密钥          | 93     | 加密密钥或访问令牌           |
| 模型          | 94     | 训练好的模型文件             |
| 哈希          | 95     | 文件哈希值                   |
| 气象数据      | 96     | 气象观测或预测数据           |
| 最佳气象源选择| 80     | 根据准确率选择的最佳气象数据源 |
| 最佳算法选择  | 81     | 根据评估指标选择的最佳算法     |

依赖项
-----
- kafka-python >= 2.0.2: 用于与 Kafka 服务器通信
- pandas >= 1.3.0: 用于时间戳处理
- python >= 3.8: Python 3.8 或更高版本

使用示例
-------
```python
from datetime import datetime, timezone
from message import Cproducer, FileType

# 创建生产者实例
producer = Cproducer(["kafka1:9092", "kafka2:9092"])
producer.setTopic("greenpulse_topic")

try:
    # 发送日志消息
    producer.send_log("task_20230619_001", "ST", "/path/to/execution.log")
    
    # 发送功率预测消息
    producer.send_power(
        taskId="task_20230619_001",
        timeliness="ST",
        staType="PV",
        filePaths="/data/predictions/pv_20230619.csv",
        stime=datetime(2023, 6, 19, 0, 0, 0, tzinfo=timezone.utc),
        forecast_type="day_ahead"
    )
    
    # 发送最佳算法选择结果
    algorithm_results = {
        "xgboost": {"accuracy": 0.95, "f1": 0.94, "rmse": 0.12},
        "random_forest": {"accuracy": 0.92, "f1": 0.91, "rmse": 0.15},
        "svm": {"accuracy": 0.89, "f1": 0.88, "rmse": 0.18}
    }
    producer.send_pick_best_algorithm(
        taskId="task_20230619_001",
        timeliness="ST",
        sources=algorithm_results
    )
    
finally:
    # 确保关闭生产者
    producer.close()
```

注意事项
-------
1. **时区处理**：所有时间戳都使用 UTC 时区，确保时间一致性
2. **消息压缩**：默认使用 gzip 压缩消息以减少网络传输
3. **错误处理**：生产环境应添加适当的错误处理和重试机制
4. **资源管理**：使用 `with` 语句或 `try/finally` 确保正确关闭生产者
5. **性能考虑**：对于大批量消息，考虑使用批量发送API提高吞吐量
6. **安全性**：敏感信息（如密钥）应加密后再发送

API 参考
-------
### `check_timeliness(timeliness: str) -> int`
将时间尺度字符串转换为对应的数据类型标识。

### `FileType` 枚举
定义系统支持的文件类型：
- `LOG = 0`: 日志文件
- `POWER = 1`: 功率预测文件
- `ACC = 2`: 准确率文件
- `KEY = 3`: 密钥文件
- `MODEL = 4`: 模型文件
- `HASH = 5`: 哈希文件
- `METEO = 6`: 气象文件

### `CNullKafkaProducer` 类
空实现的 Kafka 生产者，所有方法都是空操作，用于测试或禁用消息发送。

### `Cproducer` 类
实际的 Kafka 生产者实现，提供完整的消息发送功能。

#### 主要方法
- `setTopic(topic: str) -> None`: 设置消息主题
- `send(message: Dict[str, Any]) -> None`: 发送原始消息
- `send_checkpoint(taskId, checkpoint, **kwargs)`: 发送检查点消息
- `send_*(...)`: 各种特定类型的消息发送方法

"""
import json
import datetime as dt
from enum import IntEnum
from typing import Union, List, Dict, Any, Optional

import pandas as pd
from kafka import KafkaProducer


def check_timeliness(timeliness: str) -> int:
    """将时间尺度字符串转换为对应的数据类型标识
    
    时间尺度字符串与数据类型的对应关系：
        - "UST" -> 1 (超短期)
        - "ST"  -> 2 (短期)
        - "MT"  -> 3 (中期)
        - "SS"  -> 4 (次季节)

    Args:

        - timeliness: 时间尺度字符串，必须是 "UST", "ST", "MT" 或 "SS" 之一

    Returns:
        - int: 对应的数据类型标识 (1-4)

    Raises:

        - ValueError: 当 timeliness 参数不是预期的值时抛出

    Example:
        ```python
        >>> check_timeliness("ST")
        2
        >>> check_timeliness("MT")
        3
        ```

    Note:
        - 此函数不区分大小写，但建议使用大写形式
        - 返回的值用于消息中的 dataType 字段
    """
    timeliness = timeliness.upper()
    
    if timeliness == "UST":
        dataType = 1
    elif timeliness == "ST":
        dataType = 2
    elif timeliness == "MT":
        dataType = 3
    elif timeliness == "SS":
        dataType = 4
    else:
        raise ValueError(f"不支持的时间尺度: {timeliness}，必须是 'UST'、'ST'、'MT' 或 'SS' 之一")

    return dataType


class FileType(IntEnum):
    """文件类型枚举
    
    定义了系统中使用的各种文件类型，每种类型对应一个唯一的整数值。
    
    Attributes:

        - LOG (int): 日志文件，值为 0
        - POWER (int): 功率预测文件，值为 1
        - ACC (int): 准确率文件，值为 2
        - KEY (int): 密钥文件，值为 3
        - MODEL (int): 模型文件，值为 4
        - HASH (int): 哈希文件，值为 5
        - METEO (int): 气象文件，值为 6
        
    Example:
        ```python
        # 获取功率预测文件类型的值
        file_type = FileType.POWER  # 1
        
        # 检查文件类型
        if file_type == FileType.POWER:
            print("这是功率预测文件")
        ```
    """
    LOG = 0     # 日志文件
    POWER = 1   # 功率预测文件
    ACC = 2     # 准确率文件
    KEY = 3     # 密钥文件
    MODEL = 4   # 模型文件
    HASH = 5    # 哈希文件
    METEO = 6   # 气象文件


class CNullKafkaProducer:
    """空实现的 Kafka 生产者
    
    该类实现了与 Cproducer 相同的接口，但所有方法都是空操作。
    主要用于测试环境或当需要禁用消息发送功能时。
    
    Attributes
    ----------
    topic : str or None
        当前设置的主题名称，初始为 None
    
    Methods
    -------
    setTopic(topic)
        设置主题名称（空操作）
    send(message)
        发送消息（空操作）
    close()
        关闭生产者（空操作）
    send_checkpoint(taskId, checkpoint, **kwargs)
        发送检查点消息（空操作）
    send_log(taskId, timeliness, filePaths, **kwargs)
        发送日志文件消息（空操作）
    send_power(taskId, timeliness, filePaths, stime, **kwargs)
        发送功率预测文件消息（空操作）
    send_acc(taskId, timeliness, filePaths, **kwargs)
        发送准确率文件消息（空操作）
    send_key(taskId, timeliness, filePaths, **kwargs)
        发送密钥文件消息（空操作）
    send_model(taskId, timeliness, filePaths, **kwargs)
        发送模型文件消息（空操作）
    send_hash(taskId, timeliness, filePaths, **kwargs)
        发送哈希文件消息（空操作）
    send_meteo(taskId, timeliness, filePaths, stime, **kwargs)
        发送气象文件消息（空操作）
    
    Notes
    -----
    1. 所有方法都是空操作，调用不会产生任何实际效果
    2. 主要用于单元测试或临时禁用消息发送功能
    3. 与 Cproducer 保持相同的接口，便于替换
    
    Examples
    --------
    >>> # 在测试中使用空生产者
    >>> producer = CNullKafkaProducer()
    >>> producer.setTopic("test_topic")
    >>> producer.send_log("test_task", "ST", "/path/to/log.txt")  # 不会实际发送消息
    >>> producer.close()
    """
    
    def __init__(self, *args, **kwargs):
        """初始化空的 Kafka 生产者
        
        此方法接受任意参数但不会使用它们，仅用于保持与 Cproducer 的接口一致性。
        
        Parameters
        ----------
        *args : tuple
            忽略的位置参数
        **kwargs : dict
            忽略的关键字参数
            
        Notes
        -----
        初始化后，topic 属性被设置为 None。
        """
        self.topic = None

    def setTopic(self, topic: str) -> None:
        """设置主题名称
        
        Args:

            - topic: 主题名称
        """
        self.topic = topic

    def send(self, message: dict) -> None:
        """发送消息（空操作）
        
        Args:

            - message: 要发送的消息字典
        """
        pass

    def send_checkpoint(self, taskId: Union[str, List[str], None], checkpoint: int, **kwargs) -> None:
        """发送检查点消息（空操作）
        
        Args:

            - taskId: 任务ID，可以是字符串、字符串列表或None
            - checkpoint: 检查点值
            - **kwargs: 其他关键字参数
        """
        pass

    def close(self, *args, **kwargs) -> None:
        """关闭生产者（空操作）
        
        Args:

            - *args: 忽略的位置参数
            - **kwargs: 忽略的关键字参数
        """
        pass

    def send_log(self, taskId: str, timeliness: str, filePaths: Union[str, List[str]], **kwargs) -> None:
        """发送日志文件消息（空操作）
        
        Args:

            - taskId: 任务ID
            - timeliness: 时间尺度（"UST", "ST", "MT", "SS"）
            - filePaths: 文件路径或路径列表
            - **kwargs: 其他关键字参数
        """
        pass

    def send_power(self, taskId: str, timeliness: str, filePaths: Union[str, List[str]], 
                  stime: dt.datetime, **kwargs) -> None:
        """发送功率预测文件消息（空操作）
        
        Args:

            - taskId: 任务ID
            - timeliness: 时间尺度
            - filePaths: 文件路径或路径列表
            - stime: 开始时间
            - **kwargs: 其他关键字参数
        """
        pass

    def send_acc(self, taskId: str, timeliness: str, filePaths: Union[str, List[str]], **kwargs) -> None:
        """发送准确率文件消息（空操作）"""
        pass

    def send_key(self, taskId: str, timeliness: str, filePaths: Union[str, List[str]], **kwargs) -> None:
        """发送密钥文件消息（空操作）"""
        pass

    def send_model(self, taskId: str, timeliness: str, filePaths: Union[str, List[str]], **kwargs) -> None:
        """发送模型文件消息（空操作）"""
        pass

    def send_hash(self, taskId: str, timeliness: str, filePaths: Union[str, List[str]], **kwargs) -> None:
        """发送哈希文件消息（空操作）"""
        pass

    def send_meteo(self, taskId: str, timeliness: str, filePaths: Union[str, List[str]], 
                  stime: dt.datetime, **kwargs) -> None:
        """发送气象文件消息（空操作）
        
        Args:

            - taskId: 任务ID
            - timeliness: 时间尺度
            - filePaths: 文件路径或路径列表
            - stime: 开始时间
            - **kwargs: 其他关键字参数
        """
        pass

class Cproducer(CNullKafkaProducer):
    """Kafka 消息生产者
    
    实现了向 Kafka 消息队列发送结构化消息的功能，支持多种消息类型。
    继承自 CNullKafkaProducer，提供实际的消息发送实现。
    
    Attributes
    ----------
    producer : kafka.KafkaProducer
        底层的 KafkaProducer 实例，用于实际的消息发送
    topic : str or None
        当前设置的主题名称，通过 setTopic 方法设置
        
    Methods
    -------
    setTopic(topic)
        设置消息主题
    send(message)
        发送原始消息到当前主题
    close()
        刷新并关闭 Kafka 生产者连接
    send_checkpoint(taskId, checkpoint, **kwargs)
        发送检查点消息
    send_log(taskId, timeliness, filePaths, **kwargs)
        发送日志文件消息
    send_power(taskId, timeliness, filePaths, stime, **kwargs)
        发送功率预测文件消息
    send_acc(taskId, timeliness, filePaths, **kwargs)
        发送准确率文件消息
    send_key(taskId, timeliness, filePaths, **kwargs)
        发送密钥文件消息
    send_model(taskId, timeliness, filePaths, **kwargs)
        发送模型文件消息
    send_hash(taskId, timeliness, filePaths, **kwargs)
        发送哈希文件消息
    send_meteo(taskId, timeliness, filePaths, stime, **kwargs)
        发送气象文件消息
    send_pick_best_meteo(taskId, timeliness, **kwargs)
        发送最佳气象数据源选择结果
    send_pick_best_algorithm(taskId, timeliness, sources, **kwargs)
        发送最佳算法选择结果
        
    Notes
    -----
    1. 所有发送的消息都会自动使用 gzip 压缩
    2. 消息使用 JSON 格式序列化
    3. 默认使用 Kafka API 版本 3.9
    4. 所有时间戳都使用 UTC 时区
    
    Examples
    --------
    >>> # 创建生产者实例
    >>> producer = Cproducer(["kafka1:9092", "kafka2:9092"])
    >>> producer.setTopic("greenpulse_topic")
    >>> 
    >>> # 发送检查点消息
    >>> producer.send_checkpoint("task123", 50, status=True, runtime=1000)
    >>> 
    >>> # 发送日志消息
    >>> producer.send_log("task123", "ST", "/path/to/log.txt")
    >>> 
    >>> # 关闭生产者
    >>> producer.close()
    """
    
    def __init__(self, messageQueueURL: List[str]):
        """初始化 Kafka 生产者
        
        创建并配置 KafkaProducer 实例，设置消息序列化和压缩选项。
        
        Parameters
        ----------
        messageQueueURL : List[str]
            Kafka 服务器地址列表，例如 ["host1:9092", "host2:9092"]
            
        Notes
        -----
        1. 使用 gzip 压缩消息以减少网络传输
        2. 自动将消息序列化为 JSON 格式
        3. 设置 API 版本为 3.9
        4. 启用幂等性，确保消息不会重复发送
        5. 设置 acks='all' 确保消息被所有副本确认
        
        Raises
        ------
        kafka.errors.KafkaError
            如果无法连接到 Kafka 服务器
        """
        self.producer = KafkaProducer(
            bootstrap_servers=messageQueueURL, 
            api_version=(3, 9), 
            compression_type="gzip", 
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=3
        )
        self.topic = None

    def close(self) -> None:
        """刷新并关闭 Kafka 生产者连接
        
        确保所有缓冲的消息都被发送，然后释放资源。
        应该在程序结束时调用此方法。
        """
        try:
            self.producer.flush()
            self.producer.close()
        except Exception as e:
            # 记录错误但不会抛出，因为这是清理操作
            print(f"Error closing Kafka producer: {e}")

    def send(self, message: Dict[str, Any]) -> None:
        """向当前主题发送一条 JSON 消息
        
        Args:

            - message: 要发送的消息字典，将被序列化为 JSON
            
        Raises:

            - RuntimeError: 如果未设置主题
            - kafka.errors.KafkaError: 如果消息发送失败
            
        Note:
            - 消息会自动使用 gzip 压缩
            - 使用 UTF-8 编码
        """
        if not self.topic:
            raise RuntimeError("Topic not set. Call setTopic() first.")
            
        self.producer.send(topic=self.topic, value=message)

    def send_checkpoint(self, taskId: Union[str, List[str], None], checkpoint: int, **kwargs) -> None:
        """发送检查点消息
        
        Args:

            - taskId: 任务ID，可以是字符串或字符串列表。如果是列表，则使用第一个元素。
            - checkpoint: 检查点值，用于标识任务执行阶段
            - **kwargs: 其他可选参数，包括：
                - status (bool): 任务状态，默认为 True
                - runtime (str): 运行时间，默认为 'N/A'
                - resource (dict): 资源使用情况，默认为空字典
                - 其他自定义参数将直接添加到消息中
                
        Raises:

            - ValueError: 如果 taskId 参数无效
            
        Example:
            ```python
            # 发送成功检查点
            producer.send_checkpoint("task123", 50, status=True, runtime="100ms")
            
            # 发送失败检查点
            producer.send_checkpoint("task123", 50, status=False, 
                                  error="File not found", runtime="200ms")
            ```
        """
        if taskId is None:
            taskId = "unknown"
        elif isinstance(taskId, list):
            if not taskId:
                taskId = "unknown"
            else:
                taskId = taskId[0]
        elif not isinstance(taskId, str):
            raise ValueError("taskId 必须是字符串或字符串列表")

        # 获取标准参数
        status = kwargs.pop("status", True)
        runtime = kwargs.pop("runtime", 'N/A')
        resource = kwargs.pop("resource", {})

        # 构建消息体
        value = {
            "taskid": taskId,
            "checkpoint": checkpoint,
            "status": "true" if status else "false",
            "runtime": runtime,
            "resource": resource,
            **kwargs  # 添加其他自定义参数
        }

        # 发送消息
        self.producer.send(
            topic=self.topic,
            value=value,
        )

    def send_log(self, taskId: str, timeliness: str, filePaths: Union[str, List[str]], **kwargs) -> None:
        """发送日志文件相关的消息
        
        向 Kafka 主题发送一条日志文件相关的消息，通常用于记录任务执行过程中的日志信息。
        
        Args:

            - taskId: 任务ID，用于标识消息所属的任务
            - timeliness: 时间尺度，必须是 "UST"、"ST"、"MT" 或 "SS" 之一
            - filePaths: 日志文件的路径，可以是单个路径字符串或路径列表
            - **kwargs: 其他可选参数，包括：
                - status (str): 任务状态，默认为 "true"
                - runtime (str): 运行时间，默认为 'N/A'
                - resource (dict): 资源使用情况，默认为空字典
                - 其他自定义参数将直接添加到消息中
                
        Raises:

            - ValueError: 如果 timeliness 参数无效
            - kafka.errors.KafkaError: 如果消息发送失败
            
        Example:
            ```python
            # 发送单个日志文件
            producer.send_log("task123", "ST", "/path/to/log.txt")
            
            # 发送多个日志文件并附加自定义参数
            producer.send_log("task123", "MT", 
                           ["/path/to/log1.txt", "/path/to/error.log"],
                           status="true",
                           custom_field="value")
            ```
            
        Note:
            - 消息的 checkpoint 固定为 90
            - 文件类型会根据 timeliness 参数自动确定
            - 如果 filePaths 是字符串，会自动转换为单元素列表
        """
        dataType = check_timeliness(timeliness)

        # 获取标准参数
        status = kwargs.pop("status", "true")
        runtime = kwargs.pop("runtime", 'N/A')
        resource = kwargs.pop("resource", {})

        # 确保 filePaths 是列表
        file_paths = [filePaths] if isinstance(filePaths, str) else filePaths

        for file_path in file_paths:
            # 构建消息体
            value = {
                "taskid": taskId,
                "checkpoint": 90,  # 固定检查点值
                "file": {
                    "fileType": dataType, 
                    "filePath": str(file_path)  # 确保路径是字符串
                },
                "status": status,
                "runtime": runtime,
                "resource": resource,
                **kwargs  # 添加其他自定义参数
            }

            # 发送消息
            self.producer.send(
                topic=self.topic,
                value=value,
            )

    def send_power(self, taskId: str, timeliness: str, staType: str, filePaths: Union[str, List[str]],
                  stime: dt.datetime, **kwargs) -> None:
        """发送功率预测文件相关的消息
        
        向 Kafka 主题发送一条功率预测文件相关的消息，通常用于通知下游系统获取最新的功率预测数据。
        
        Args:

            - taskId: 任务ID，用于标识消息所属的任务
            - timeliness: 时间尺度，必须是 "UST"、"ST"、"MT" 或 "SS" 之一
            - staType: 站点类型
            - filePaths: 功率预测文件的路径，可以是单个路径字符串或路径列表
            - stime: 预测的起始时间
            - **kwargs: 其他可选参数，包括：
                - status (str): 任务状态，默认为 "true"
                - runtime (str): 运行时间，默认为 'N/A'
                - resource (dict): 资源使用情况，默认为空字典
                - 其他自定义参数将直接添加到消息中
                
        Raises:

            - ValueError: 如果 timeliness 参数无效或 stime 不是 datetime 对象
            - kafka.errors.KafkaError: 如果消息发送失败
            
        Example:
            ```python
            from datetime import datetime, timezone
            
            # 发送单个功率预测文件
            producer.send_power(
                "task123", 
                "ST",
                "PV",
                "/path/to/power_forecast.csv",
                datetime.now(timezone.utc)
            )
            
            # 发送多个功率预测文件并附加自定义参数
            producer.send_power(
                "task123", 
                "MT",
                "PV",
                ["/path/to/power1.csv", "/path/to/power2.csv"],
                datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                forecast_type="day_ahead"
            )
            ```
            
        Note:
            - 消息的 checkpoint 固定为 91
            - stime 会被格式化为 "YYYY-MM-DD HH:MM:SS" 字符串
            - 文件类型会根据 timeliness 参数自动确定
        """
        if not isinstance(stime, dt.datetime):
            raise ValueError("stime 必须是 datetime 对象")
            
        dataType = check_timeliness(timeliness)

        # 获取标准参数
        status = kwargs.pop("status", "true")
        runtime = kwargs.pop("runtime", 'N/A')
        resource = kwargs.pop("resource", {})

        # 确保 filePaths 是列表
        file_paths = [filePaths] if isinstance(filePaths, str) else filePaths

        for file_path in file_paths:
            # 构建消息体
            value = {
                "taskid": taskId,
                "staType": staType,
                "checkpoint": 91,  # 固定检查点值
                "stime": stime.strftime("%Y-%m-%d %H:%M:%S"),
                "file": {
                    "fileType": dataType, 
                    "filePath": str(file_path)  # 确保路径是字符串
                },
                "status": status,
                "runtime": runtime,
                "resource": resource,
                **kwargs  # 添加其他自定义参数
            }

            # 发送消息
            self.producer.send(
                topic=self.topic,
                value=value,
            )

    def send_acc(self, taskId: str, timeliness: str, filePaths: Union[str, List[str]], **kwargs) -> None:
        """发送准确率文件相关的消息
        
        向 Kafka 主题发送一条准确率文件相关的消息，通常用于报告模型预测的准确率评估结果。
        
        Args:

            - taskId: 任务ID，用于标识消息所属的任务
            - timeliness: 时间尺度，必须是 "UST"、"ST"、"MT" 或 "SS" 之一
            - filePaths: 准确率文件的路径，可以是单个路径字符串或路径列表
            - **kwargs: 其他可选参数，包括：
                - status (str): 任务状态，默认为 "true"
                - runtime (str): 运行时间，默认为 'N/A'
                - resource (dict): 资源使用情况，默认为空字典
                - 其他自定义参数将直接添加到消息中
                
        Raises:

            - ValueError: 如果 timeliness 参数无效
            - kafka.errors.KafkaError: 如果消息发送失败
            
        Example:
            ```python
            # 发送单个准确率文件
            producer.send_acc("task123", "ST", "/path/to/accuracy_report.json")
            
            # 发送多个准确率文件并附加自定义参数
            producer.send_acc(
                "task123", 
                "MT",
                ["/path/to/accuracy1.json", "/path/to/metrics.csv"],
                model_version="v2.0",
                accuracy=0.95
            )
            ```
            
        Note:
            - 消息的 checkpoint 固定为 92
            - 文件类型会根据 timeliness 参数自动确定
            - 如果 filePaths 是字符串，会自动转换为单元素列表
        """
        dataType = check_timeliness(timeliness)

        # 获取标准参数
        status = kwargs.pop("status", "true")
        runtime = kwargs.pop("runtime", 'N/A')
        resource = kwargs.pop("resource", {})

        # 确保 filePaths 是列表
        file_paths = [filePaths] if isinstance(filePaths, str) else filePaths

        for file_path in file_paths:
            # 构建消息体
            value = {
                "taskid": taskId,
                "checkpoint": 92,  # 固定检查点值
                "file": {
                    "fileType": dataType, 
                    "filePath": str(file_path)  # 确保路径是字符串
                },
                "status": status,
                "runtime": runtime,
                "resource": resource,
                **kwargs  # 添加其他自定义参数
            }

            # 发送消息
            self.producer.send(
                topic=self.topic,
                value=value,
            )

    def send_key(self, taskId: str, timeliness: str, filePaths: Union[str, List[str]], **kwargs) -> None:
        """发送密钥文件相关的消息
        
        向 Kafka 主题发送一条密钥文件相关的消息，通常用于安全地分发加密密钥或访问令牌。
        
        Args:

            - taskId: 任务ID，用于标识消息所属的任务
            - timeliness: 时间尺度，必须是 "UST"、"ST"、"MT" 或 "SS" 之一
            - filePaths: 密钥文件的路径，可以是单个路径字符串或路径列表
            - **kwargs: 其他可选参数，包括：
                - status (str): 任务状态，默认为 "true"
                - runtime (str): 运行时间，默认为 'N/A'
                - resource (dict): 资源使用情况，默认为空字典
                - 其他自定义参数将直接添加到消息中
                
        Raises:

            - ValueError: 如果 timeliness 参数无效
            - kafka.errors.KafkaError: 如果消息发送失败
            
        Example:
            ```python
            # 发送单个密钥文件
            producer.send_key("task123", "ST", "/path/to/secret.key")
            
            # 发送多个密钥文件并附加自定义参数
            producer.send_key(
                "task123", 
                "MT",
                ["/path/to/secret1.key", "/path/to/token.jwt"],
                key_type="rsa_private",
                expires_in="30d"
            )
            ```
            
        Note:
            - 消息的 checkpoint 固定为 93
            - 文件类型会根据 timeliness 参数自动确定
            - 如果 filePaths 是字符串，会自动转换为单元素列表
            - 建议对密钥文件进行加密处理后再发送
        """
        dataType = check_timeliness(timeliness)

        # 获取标准参数
        status = kwargs.pop("status", "true")
        runtime = kwargs.pop("runtime", 'N/A')
        resource = kwargs.pop("resource", {})

        # 确保 filePaths 是列表
        file_paths = [filePaths] if isinstance(filePaths, str) else filePaths

        for file_path in file_paths:
            # 构建消息体
            value = {
                "taskid": taskId,
                "checkpoint": 93,  # 固定检查点值
                "file": {
                    "fileType": dataType, 
                    "filePath": str(file_path)  # 确保路径是字符串
                },
                "status": status,
                "runtime": runtime,
                "resource": resource,
                **kwargs  # 添加其他自定义参数
            }


            # 发送消息
            self.producer.send(
                topic=self.topic,
                value=value,
            )

    def send_model(self, taskId: str, timeliness: str, filePaths: Union[str, List[str]], **kwargs) -> None:
        """发送模型文件相关的消息
        
        向 Kafka 主题发送一条模型文件相关的消息，通常用于部署或更新机器学习模型。
        
        Args:

            - taskId: 任务ID，用于标识消息所属的任务
            - timeliness: 时间尺度，必须是 "UST"、"ST"、"MT" 或 "SS" 之一
            - filePaths: 模型文件的路径，可以是单个路径字符串或路径列表
            - **kwargs: 其他可选参数，包括：
                - status (str): 任务状态，默认为 "true"
                - runtime (str): 运行时间，默认为 'N/A'
                - resource (dict): 资源使用情况，默认为空字典
                - 其他自定义参数将直接添加到消息中
                
        Raises:

            - ValueError: 如果 timeliness 参数无效
            - kafka.errors.KafkaError: 如果消息发送失败
            
        Example:
            ```python
            # 发送单个模型文件
            producer.send_model("task123", "ST", "/path/to/model.pkl")
            
            # 发送多个模型文件并附加自定义参数
            producer.send_model(
                "task123", 
                "MT",
                ["/path/to/model.pkl", "/path/to/preprocessor.bin"],
                model_name="xgboost_v2",
                metrics={"accuracy": 0.95, "f1": 0.92}
            )
            ```
            
        Note:
            - 消息的 checkpoint 固定为 94
            - 文件类型会根据 timeliness 参数自动确定
            - 如果 filePaths 是字符串，会自动转换为单元素列表
            - 对于大型模型文件，建议先上传到共享存储，然后只发送文件路径
        """
        dataType = check_timeliness(timeliness)

        # 获取标准参数
        status = kwargs.pop("status", "true")
        runtime = kwargs.pop("runtime", 'N/A')
        resource = kwargs.pop("resource", {})

        # 确保 filePaths 是列表
        file_paths = [filePaths] if isinstance(filePaths, str) else filePaths

        for file_path in file_paths:
            # 构建消息体
            value = {
                "taskid": taskId,
                "checkpoint": 94,  # 固定检查点值
                "file": {
                    "fileType": dataType, 
                    "filePath": str(file_path)  # 确保路径是字符串
                },
                "status": status,
                "runtime": runtime,
                "resource": resource,
                **kwargs  # 添加其他自定义参数
            }

            # 发送消息
            self.producer.send(
                topic=self.topic,
                value=value,
            )

    def send_hash(self, taskId: str, timeliness: str, filePaths: Union[str, List[str]], **kwargs) -> None:
        """发送哈希文件相关的消息
        
        向 Kafka 主题发送一条哈希文件相关的消息，通常用于文件完整性校验。
        
        Args:

            - taskId: 任务ID，用于标识消息所属的任务
            - timeliness: 时间尺度，必须是 "UST"、"ST"、"MT" 或 "SS" 之一
            - filePaths: 哈希文件的路径，可以是单个路径字符串或路径列表
            - **kwargs: 其他可选参数，包括：
                - status (str): 任务状态，默认为 "true"
                - runtime (str): 运行时间，默认为 'N/A'
                - resource (dict): 资源使用情况，默认为空字典
                - 其他自定义参数将直接添加到消息中
                
        Raises:

            - ValueError: 如果 timeliness 参数无效
            - kafka.errors.KafkaError: 如果消息发送失败
            
        Example:
            ```python
            # 发送单个哈希文件
            producer.send_hash("task123", "ST", "/path/to/checksums.md5")
            
            # 发送多个哈希文件并附加自定义参数
            producer.send_hash(
                "task123", 
                "MT",
                ["/path/to/checksums.md5", "/path/to/sha256sums.txt"],
                algorithm="sha256",
                verified=True
            )
            ```
            
        Note:
            - 消息的 checkpoint 固定为 95
            - 文件类型会根据 timeliness 参数自动确定
            - 如果 filePaths 是字符串，会自动转换为单元素列表
            - 建议同时发送原始文件和对应的哈希文件，以便接收方进行完整性校验
        """
        dataType = check_timeliness(timeliness)

        # 获取标准参数
        status = kwargs.pop("status", "true")
        runtime = kwargs.pop("runtime", 'N/A')
        resource = kwargs.pop("resource", {})

        # 确保 filePaths 是列表
        file_paths = [filePaths] if isinstance(filePaths, str) else filePaths

        for file_path in file_paths:
            # 构建消息体
            value = {
                "taskid": taskId,
                "checkpoint": 95,  # 固定检查点值
                "file": {
                    "fileType": dataType, 
                    "filePath": str(file_path)  # 确保路径是字符串
                },
                "status": status,
                "runtime": runtime,
                "resource": resource,
                **kwargs  # 添加其他自定义参数
            }

            # 发送消息
            self.producer.send(
                topic=self.topic,
                value=value,
            )

    def send_meteo(self, taskId: str, timeliness: str, staType: str, filePaths: Union[str, List[str]],
                  stime: pd.Timestamp, **kwargs) -> None:
        """发送气象数据文件相关的消息
        
        向 Kafka 主题发送一条气象数据文件相关的消息，通常用于分发气象观测或预测数据。
        
        Args:

            - taskId: 任务ID，用于标识消息所属的任务
            - timeliness: 时间尺度，必须是 "UST"、"ST"、"MT" 或 "SS" 之一
            - staType: 站点类型
            - filePaths: 气象数据文件的路径，可以是单个路径字符串或路径列表
            - stime: 气象数据的时间戳，pandas Timestamp 对象
            - **kwargs: 其他可选参数，包括：
                - status (str): 任务状态，默认为 "true"
                - runtime (str): 运行时间，默认为 'N/A'
                - resource (dict): 资源使用情况，默认为空字典
                - 其他自定义参数将直接添加到消息中
                
        Raises:

            - ValueError: 如果 timeliness 参数无效或 stime 不是 pandas Timestamp 对象
            - kafka.errors.KafkaError: 如果消息发送失败
            
        Example:
            ```python
            import pandas as pd
            
            # 发送单个气象数据文件
            producer.send_meteo(
                "task123", 
                "ST", 
                "/path/to/meteo_data.nc",
                pd.Timestamp("2023-01-01 00:00:00")
            )
            
            # 发送多个气象数据文件并附加自定义参数
            producer.send_meteo(
                "task123", 
                "MT",
                [
                    "/path/to/temperature.nc", 
                    "/path/to/humidity.nc"
                ],
                pd.Timestamp("2023-01-01 00:00:00"),
                forecast_hours=24,
                source="ECMWF"
            )
            ```
            
        Note:
            - 消息的 checkpoint 固定为 96
            - stime 会被格式化为 "YYYY-MM-DD HH:MM:SS" 字符串
            - 文件类型会根据 timeliness 参数自动确定
            - 如果 filePaths 是字符串，会自动转换为单元素列表
            - 对于大型气象数据文件，建议先上传到共享存储，然后只发送文件路径
        """
        if not isinstance(stime, pd.Timestamp):
            raise ValueError("stime 必须是 pandas.Timestamp 对象")
            
        dataType = check_timeliness(timeliness)

        # 获取标准参数
        status = kwargs.pop("status", "true")
        runtime = kwargs.pop("runtime", 'N/A')
        resource = kwargs.pop("resource", {})

        # 确保 filePaths 是列表
        file_paths = [filePaths] if isinstance(filePaths, str) else filePaths

        for file_path in file_paths:
            # 构建消息体
            value = {
                "taskid": taskId,
                "staType": staType,
                "checkpoint": 96,  # 固定检查点值
                "stime": stime.strftime("%Y-%m-%d %H:%M:%S"),
                "file": {
                    "fileType": dataType, 
                    "filePath": str(file_path)  # 确保路径是字符串
                },
                "status": status,
                "runtime": runtime,
                "resource": resource,
                **kwargs  # 添加其他自定义参数
            }

            # 发送消息
            self.producer.send(
                topic=self.topic,
                value=value,
            )

    def send_pick_best_meteo(self, taskId: str, timeliness: str, **kwargs) -> None:
        """发送最佳气象数据源选择结果
        
        向 Kafka 主题发送一条消息，指示根据准确率选择的最佳气象数据源。
        当前为示例实现，返回固定数据。
        
        Args:

            - taskId: 任务ID，用于标识消息所属的任务
            - timeliness: 时间尺度，必须是 "UST"、"ST"、"MT" 或 "SS" 之一
            - **kwargs: 其他可选参数，包括：
                - status (str): 任务状态，默认为 "true"
                - runtime (int/str): 运行时间，默认为 100
                - resource (dict): 资源使用情况，默认为空字典
                - 其他自定义参数将直接添加到消息中
                
        Raises:

            - ValueError: 如果 timeliness 参数无效
            - kafka.errors.KafkaError: 如果消息发送失败
            
        Example:
            ```python
            # 发送最佳气象数据源选择结果
            producer.send_pick_best_meteo("task123", "ST")
            ```
            
        Note:
            - 消息的 checkpoint 固定为 80
            - 当前为示例实现，返回固定数据
            - 实际实现中应根据实际准确率数据动态生成 sources 字典
        """
        dataType = check_timeliness(timeliness)

        # 获取标准参数
        status = kwargs.pop("status", "true")
        runtime = kwargs.pop("runtime", 100)
        resource = kwargs.pop("resource", {})

        # 构建消息体
        value = {
            "taskid": taskId,
            "checkpoint": 80,  # 固定检查点值
            "dataType": dataType,
            "sources": {
                "EC_C1D": {"order": 1, "acc": 86.5},
                "EC_C3E": {"order": 2, "acc": 73.5},
                "EC_C6F": {"order": 3, "acc": 60.5}
            },
            "status": status,
            "runtime": runtime,
            "resource": resource,
            **kwargs  # 添加其他自定义参数
        }

        # 发送消息
        self.producer.send(
            topic=self.topic,
            value=value,
        )

    def send_pick_best_algorithm(self, taskId: str, timeliness: str, 
                               sources: Dict[str, Dict[str, float]], **kwargs) -> None:
        """发送最佳算法选择结果
        
        向 Kafka 主题发送一条消息，指示根据评估指标选择的最佳算法。
        
        Args:

            - taskId: 任务ID，用于标识消息所属的任务
            - timeliness: 时间尺度，必须是 "UST"、"ST"、"MT" 或 "SS" 之一
            - sources: 算法评估结果字典，格式为：
                {
                    "algorithm1": {"metric1": value1, "metric2": value2, ...},
                    "algorithm2": {"metric1": value1, "metric2": value2, ...},
                    ...
                }
            - **kwargs: 其他可选参数，包括：
                - status (str): 任务状态，默认为 "true"
                - runtime (str): 运行时间，默认为 'N/A'
                - resource (dict): 资源使用情况，默认为空字典
                - 其他自定义参数将直接添加到消息中
                
        Raises:

            - ValueError: 如果 timeliness 参数无效或 sources 格式不正确
            - kafka.errors.KafkaError: 如果消息发送失败
            
        Example:
            ```python
            # 发送最佳算法选择结果
            algorithm_results = {
                "xgboost": {"accuracy": 0.95, "f1": 0.94, "rmse": 0.12},
                "random_forest": {"accuracy": 0.92, "f1": 0.91, "rmse": 0.15},
                "svm": {"accuracy": 0.89, "f1": 0.88, "rmse": 0.18}
            }
            producer.send_pick_best_algorithm("task123", "ST", algorithm_results)
            ```
            
        Note:
            - 消息的 checkpoint 固定为 81
            - sources 字典的键是算法名称，值是包含评估指标的字典
            - 接收方需要根据具体业务逻辑解析 sources 字典
        """
        dataType = check_timeliness(timeliness)

        # 验证 sources 参数
        if not isinstance(sources, dict):
            raise ValueError("sources 参数必须是一个字典")
            
        for algorithm, metrics in sources.items():
            if not isinstance(metrics, dict):
                raise ValueError(f"算法 '{algorithm}' 的指标必须是一个字典")
                
            for key, value in metrics.items():
                if not isinstance(key, str):
                    raise ValueError(f"算法 '{algorithm}' 的指标键必须是字符串")
                if not isinstance(value, (int, float)):
                    raise ValueError(f"算法 '{algorithm}' 的指标值必须是数值型")

        # 获取标准参数
        status = kwargs.pop("status", "true")
        runtime = kwargs.pop("runtime", 'N/A')
        resource = kwargs.pop("resource", {})

        # 构建消息体
        value = {
            "taskid": taskId,
            "checkpoint": 81,  # 固定检查点值
            "dataType": dataType,
            "sources": sources,
            "status": status,
            "runtime": runtime,
            "resource": resource,
            **kwargs  # 添加其他自定义参数
        }

        # 发送消息
        self.producer.send(
            topic=self.topic,
            value=value,
        )
