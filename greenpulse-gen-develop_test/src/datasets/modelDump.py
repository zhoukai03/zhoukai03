import os
import pickle
import logging
import hashlib
from typing import Union
from cryptography.fernet import Fernet
from ..message import Cproducer, CNullKafkaProducer

def _dirCheckandCreate(path: str, logger: Union[logging.Logger, None] = None) -> None:
    """
    检查目录是否存在，如果不存在则创建该目录。

    参数:
    path (str): 需要检查和创建的目录路径。
    logger (Union[logging.Logger, None], optional): 用于记录日志的logger对象，如果为None，则不记录日志。默认为None。

    返回:
    无返回值。
    """
    try:
        # 检查目录是否存在，如果不存在则尝试创建
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            # 如果目录成功创建，且提供了logger对象，则记录成功创建目录的信息
            if logger:
                logger.info(f"目录 {path} 未创建，已成功创建")
    except Exception as e:
        # 如果在创建目录过程中发生异常，且提供了logger对象，则记录错误信息
        if logger:
            logger.error(f"创建目录 {path} 失败: {e}")
        # 抛出异常，以便调用者可以捕获并处理
        raise e

def _fileWrite(file_path: str, content: any, mode: str = 'wb', logger: Union[logging.Logger, None] = None):
    """
    将内容写入文件。

    参数:
    file_path (str): 文件路径。
    content (any): 要写入文件的内容。
    mode (str, optional): 文件打开模式。默认为'wb'（二进制写入）。
    logger (Union[logging.Logger, None], optional): 用于记录日志的logger对象，如果为None，则不记录日志。默认为None。

    返回:
    无返回值。
    """
    try:
        # 打开文件并写入内容
        with open(file_path, mode) as f:
            f.write(content)
            # 确保文件内容被写入磁盘
            #os.fsync(f.fileno())
    except Exception as e:
        # 捕获异常并使用日志记录对象记录错误
        if logger:
            logger.error(f"写入文件 {file_path} 失败: {e}")
        # 重新抛出异常
        raise e

def modelDump(taskId: str, model: any, timeliness: str, modelPath: str, hashPath: str, keyPath: str, 
              logger: logging.Logger, messageQueueProducer: Union[Cproducer, CNullKafkaProducer]) -> None:
    """将模型加密后保存到指定路径，并生成相应的哈希值和密钥。
    
    该函数负责将训练好的模型进行序列化、加密，并保存到指定路径。
    同时会生成模型的哈希值（用于完整性校验）和加密密钥（用于后续解密）。
    所有操作都会记录到日志中，并支持通过消息队列发送通知。
    
    主要功能:
    1. 模型序列化：使用pickle将模型对象序列化为字节流
    2. 数据加密：使用Fernet对称加密算法对序列化后的模型进行加密
    3. 完整性校验：计算并保存模型的MD5哈希值
    4. 密钥管理：安全地保存加密密钥
    5. 目录管理：自动创建不存在的目录
    
    参数
    ----------
    taskId : str
        唯一标识符，用于在日志和消息中追踪模型
    model : any
        需要保存的模型对象，必须支持pickle序列化
    timeliness : str
        模型时效性描述（如：'ST'短期，'MT'中期等）
    modelPath : str
        加密后模型文件的保存路径（包括文件名）
    hashPath : str
        模型哈希值的保存路径（包括文件名）
    keyPath : str
        加密密钥的保存路径（包括文件名）
    logger : logging.Logger
        用于记录操作日志的logger对象
    messageQueueProducer : Union[Cproducer, CNullKafkaProducer]
        消息队列生产者，用于发送模型保存状态通知
        
    返回
    -------
    None
        
    异常
    --------
    IOError
        当文件写入失败或目录创建失败时抛出
    pickle.PickleError
        当模型对象无法序列化时抛出
    cryptography.fernet.InvalidToken
        当加密/解密过程中出现错误时抛出
    
    注意事项
    ----------
    1. 确保传入的目录有写入权限
    2. 密钥文件(keyPath)需要妥善保管，丢失后将无法解密模型
    3. 建议对密钥文件设置适当的文件权限
    
    示例
    -------
    >>> import logging
    >>> from your_module import Cproducer, CNullKafkaProducer
    >>> 
    >>> # 配置日志
    >>> logging.basicConfig(level=logging.INFO)
    >>> logger = logging.getLogger(__name__)
    >>> 
    >>> # 初始化消息生产者（使用空生产者作为示例）
    >>> producer = CNullKafkaProducer()
    >>> 
    >>> # 示例模型（实际使用时替换为真实模型）
    >>> example_model = {}
    >>> 
    >>> # 保存模型
    >>> modelDump(
    ...     taskId="model_001",
    ...     model=example_model,
    ...     timeliness="ST",
    ...     modelPath="/path/to/model.enc",
    ...     hashPath="/path/to/model.md5",
    ...     keyPath="/path/to/secret.key",
    ...     logger=logger,
    ...     messageQueueProducer=producer
    ... )
    """
    # 检查并创建目录
    for path in [modelPath, hashPath, keyPath]:
        dirPath = os.path.dirname(path)
        _dirCheckandCreate(dirPath, logger)

    # 生成密钥并保存
    key = Fernet.generate_key()
    try:
        _fileWrite(keyPath, key, 'wb', logger)
        logger.info(f"任务 {taskId} 密钥保存成功")
        messageQueueProducer.send_key(taskId, timeliness, keyPath)
    except Exception as e:
        logger.error(f"任务 {taskId} 密钥处理失败: {e}")
        raise e

    try:
        encryptedModel = pickle.dumps(model)
        hashVal = hashlib.sha256(encryptedModel).hexdigest()
        _fileWrite(hashPath, hashVal, 'w', logger)
        logger.info("模型哈希值保存成功")
        messageQueueProducer.send_hash(taskId, timeliness, hashPath)
    except Exception as e:
        logger.error(f"任务 {taskId} 哈希处理失败: {e}")

    try:
        import time
        cipher = Fernet(key)
        logger.info(f"任务 {taskId} 加密模型")
        
        # 测量加密时间
        start_time = time.perf_counter()
        encryptedModel = cipher.encrypt(encryptedModel)
        end_time = time.perf_counter()

        # 计算并记录加密耗时（毫秒）
        encryption_time_ms = (end_time - start_time) * 1000
        model_size_mb = len(encryptedModel) / (1024 * 1024)  # 计算加密后模型大小(MB)
        logger.info(f"加密完成 - 耗时: {encryption_time_ms:.2f} 毫秒, 加密后大小: {model_size_mb:.2f} MB")

        _fileWrite(modelPath, encryptedModel, 'wb', logger)
        logger.info("模型保存成功")
        messageQueueProducer.send_model(taskId, timeliness, modelPath)
    except Exception as e:
        logger.error(f"任务 {taskId} 模型保存失败: {e}")
