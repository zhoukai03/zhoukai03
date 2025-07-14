"""模型加载模块

该模块提供了从加密文件中安全加载机器学习模型的功能。
主要功能包括：
1. 从文件系统加载加密的模型文件
2. 加载并验证加密密钥
3. 解密模型数据
4. 验证模型完整性（通过哈希校验）

模块依赖:
    - cryptography: 用于模型加密/解密
    - pickle: 用于模型序列化/反序列化
    - hashlib: 用于哈希计算

示例:
    >>> import logging
    >>> from modelLoad import modelLoad
    >>>
    >>> # 配置日志
    >>> logging.basicConfig(level=logging.INFO)
    >>> logger = logging.getLogger(__name__)
    >>>
    >>> # 加载模型
    >>> model = modelLoad(
    ...     modelPath="/path/to/encrypted_model.pkl",
    ...     hashPath="/path/to/model_hash.md5",
    ...     keyPath="/path/to/secret.key",
    ...     logger=logger
    ... )
"""

import pickle
import logging
import hashlib
from typing import Any, Optional
from cryptography.fernet import Fernet


def loadKey(keyPath: str, logger: logging.Logger) -> Fernet:
    """加载并验证加密密钥
    
    从指定路径加载加密密钥文件，并返回用于加解密的Fernet对象。
    该函数会检查密钥文件是否存在、是否可读以及是否包含有效内容。
    
    参数
    ----------
    keyPath : str
        密钥文件的完整路径
    logger : logging.Logger
        用于记录操作日志的logger对象
        
    返回
    -------
    cryptography.fernet.Fernet
        初始化后的Fernet加密对象，用于后续的加解密操作
        
    异常
    --------
    FileNotFoundError
        当密钥文件不存在时抛出
    ValueError
        当密钥文件为空或包含无效内容时抛出
    PermissionError
        当没有权限读取密钥文件时抛出
        
    示例
    -------
    >>> import logging
    >>> from modelLoad import loadKey
    >>> logger = logging.getLogger(__name__)
    >>> cipher = loadKey("/path/to/secret.key", logger)
    """
    try:
        # 打开密钥文件并读取内容
        with open(keyPath, "rb") as f:
            key = f.read()

        # 如果密钥为空，则抛出异常
        if not key:
            raise ValueError("密钥为空")

        # 密钥加载成功，记录日志
        logger.info(f"密钥加载成功，路径: {keyPath}")

        # 返回Fernet对象
        cipher = Fernet(key)
        return cipher
    except Exception as e:
        # 密钥加载失败，记录错误日志并抛出异常
        logger.critical(f"密钥加载失败，路径: {keyPath}, 错误: {e}")
        raise e


def loadEncryptedModel(modelPath: str, logger: logging.Logger) -> bytes:
    """加载加密的模型文件
    
    从指定路径读取加密的模型文件内容，并验证文件是否有效。
    该函数会检查模型文件是否存在、是否可读以及是否包含数据。
    
    参数
    ----------
    modelPath : str
        加密模型文件的完整路径
    logger : logging.Logger
        用于记录操作日志的logger对象
        
    返回
    -------
    bytes
        包含加密模型数据的字节流
        
    异常
    --------
    FileNotFoundError
        当模型文件不存在时抛出
    ValueError
        当模型文件为空时抛出
    IOError
        当读取模型文件失败时抛出
        
    示例
    -------
    >>> encrypted_data = loadEncryptedModel("/path/to/encrypted_model.pkl", logger)
    >>> len(encrypted_data) > 0
    True
    """
    try:
        # 打开模型文件并尝试加载
        with open(modelPath, "rb") as f:
            encryptedModel = f.read()
        # 如果模型为空，则抛出异常
        if not encryptedModel:
            raise ValueError("加密模型为空")
        # 模型加载成功，记录日志并返回模型对象
        logger.info(f"模型加载成功，路径: {modelPath}")
        return encryptedModel
    except Exception as e:
        # 模型加载失败，记录关键错误日志并重新抛出异常
        logger.critical(f"模型加载失败，路径: {modelPath}, 错误: {e}")
        raise e


def decryptModel(cipher: Fernet, encryptedModel: bytes, logger: logging.Logger) -> Any:
    """解密模型数据并反序列化
    
    使用提供的Fernet密钥解密加密的模型数据，
    然后使用pickle将解密后的数据反序列化为Python对象。
    
    参数
    ----------
    cipher : cryptography.fernet.Fernet
        用于解密的Fernet对象
    encryptedModel : bytes
        加密的模型数据
    logger : logging.Logger
        用于记录操作日志的logger对象
        
    返回
    -------
    Any
        解密并反序列化后的Python对象（通常是模型）
        
    异常
    --------
    ValueError
        当解密失败或数据损坏时抛出
    pickle.UnpicklingError
        当反序列化失败时抛出
        
    警告
    -------
    反序列化不受信任的数据可能存在安全风险。
    确保只加载来自可信来源的模型文件。
    """
    try:
        decryptedData = cipher.decrypt(encryptedModel)
        decryptedData = pickle.loads(decryptedData)
        logger.info("模型解密成功")
        return decryptedData
    except Exception as e:
        logger.critical(f"模型解密失败，错误: {e}")
        raise ValueError("模型解密失败")

def loadHash(hashPath: str, logger: logging.Logger) -> str:
    """加载并验证模型哈希值
    
    从指定文件加载预计算的模型哈希值，用于后续的完整性校验。
    
    参数
    ----------
    hashPath : str
        包含模型哈希值的文件路径
    logger : logging.Logger
        用于记录操作日志的logger对象
        
    返回
    -------
    str
        从文件读取的哈希值字符串（去除首尾空白字符）
        
    异常
    --------
    FileNotFoundError
        当哈希文件不存在时抛出
    ValueError
        当哈希值为空或无效时抛出
    """
    try:
        with open(hashPath, "r") as f:
            hashVal = f.read().strip()
        if not hashVal:
            raise ValueError("哈希值为空")
        logger.info(f"模型哈希值加载成功，路径: {hashPath}")
        return hashVal
    except Exception as e:
        logger.critical(f"模型哈希值加载失败，路径: {hashPath}, 错误: {e}")
        raise e

def verifyModelHash(decryptedData: Any, hashVal: str, logger: logging.Logger) -> bool:
    """验证模型数据的完整性
    
    通过比较计算出的模型哈希值与预期哈希值，
    验证模型数据在传输或存储过程中是否被篡改。
    
    参数
    ----------
    decryptedData : Any
        解密后的模型数据
    hashVal : str
        预期的MD5哈希值
    logger : logging.Logger
        用于记录操作日志的logger对象
        
    返回
    -------
    bool
        如果哈希值匹配则返回True
        
    异常
    --------
    ValueError
        当哈希值不匹配时抛出，表明数据可能已被篡改
    """
    try:
        computedHash = hashlib.sha256(pickle.dumps(decryptedData)).hexdigest()
        if hashVal != computedHash:
            logger.critical(f"哈希值不匹配，预期: {hashVal}, 实际: {computedHash}")
            raise ValueError("模型文件损坏")
        logger.info("模型校验成功")
    except Exception as e:
        logger.critical(f"模型校验失败，错误: {e}")
        raise e


def modelLoad(modelPath: str, hashPath: str, keyPath: str, logger: logging.Logger) -> Any:
    """加载并验证加密的模型
    
    这是模块的主要入口函数，负责协调整个模型加载流程：
    1. 加载加密密钥
    2. 加载加密的模型文件
    3. 解密模型数据
    4. 验证模型完整性
    
    参数
    ----------
    modelPath : str
        加密模型文件的路径
    hashPath : str
        包含模型哈希值的文件路径
    keyPath : str
        加密密钥文件的路径
    logger : logging.Logger
        用于记录操作日志的logger对象
        
    返回
    -------
    Any
        加载并验证后的模型对象
        
    异常
    --------
    FileNotFoundError
        当任何必需的文件不存在时抛出
    ValueError
        当数据验证失败时抛出
    
    示例
    -------
    >>> import logging
    >>> logging.basicConfig(level=logging.INFO)
    >>> logger = logging.getLogger(__name__)
    >>>
    >>> # 加载模型
    >>> model = modelLoad(
    ...     modelPath="model.enc",
    ...     hashPath="model.md5",
    ...     keyPath="secret.key",
    ...     logger=logger
    ... )
    >>> # 使用加载的模型进行预测
    >>> # prediction = model.predict(data)
    """
    # 加载密钥
    cipher = loadKey(keyPath, logger)

    # 加载加密模型
    encryptedModel = loadEncryptedModel(modelPath, logger)

    # 解密模型
    decryptedData = decryptModel(cipher, encryptedModel, logger)

    # 加载并验证模型哈希值
    hashVal = loadHash(hashPath, logger)
    verifyModelHash(decryptedData, hashVal, logger)

    return decryptedData
