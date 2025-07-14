"""日志管理模块

该模块提供了日志记录和管理的功能，包括根日志记录器的设置、任务日志记录器的设置以及日志文件的清理。

主要功能：
    - 设置根日志记录器，支持控制台和文件输出
    - 设置任务日志记录器，支持多文件输出
    - 自动清理过期的日志文件

模块依赖：
    - logging: Python 标准日志模块
    - pandas: 用于时间处理
    - typing: 提供类型注解支持

使用示例：
    ```python
    # 设置根日志记录器
    from src import logger
    
    # 初始化根日志记录器
    root_logger = logger.setRootLogger(logPath="logs", taskID=["task_001"])
    
    # 记录日志
    root_logger.info("这是一条信息日志")
    root_logger.error("这是一条错误日志")
    
    # 清理过期日志
    logger.rmRootLogger(logPath="logs", logger=root_logger)
    
    # 设置任务日志记录器
    task_logger = logger.setTaskLogger(
        logFileFullPath=["logs/task_001.log", "logs/task_001_debug.log"],
        logLevel=logging.DEBUG
    )
    
    # 清理任务日志
    logger.rmTaskLogger(["logs/tasks"], logger=task_logger)
    ```

注意事项：
    1. 日志文件默认保存31天，过期会自动清理
    2. 建议为每个任务创建独立的日志记录器
    3. 确保日志目录有写入权限
"""

import os
import glob
import logging
import pandas as pd
from typing import Union, List, Optional

from .config.TypeDefine import TimeLiness


def setRootLogger(logPath: str = "log", taskID: Optional[List[str]] = None) -> logging.Logger:
    """设置根日志记录器
    
    初始化并配置根日志记录器，同时添加控制台和文件处理器。
    
    Args:

        - logPath: 日志文件保存目录，默认为当前目录下的 "log" 文件夹
        - taskID: 任务ID列表，如果提供且长度为1，将用于生成日志文件名
        
    Returns:

        - logging.Logger: 配置好的日志记录器实例
        
    Raises:

        - OSError: 当日志目录创建失败时抛出
        
    Example:
        ```python
        # 基本用法
        logger = setRootLogger()
        logger.info("这是一条信息日志")
        
        # 指定任务ID
        task_logger = setRootLogger(logPath="logs", taskID=["task_001"])
        task_logger.debug("调试信息")
        ```
        
    Note:
        - 日志级别默认为 DEBUG
        - 日志文件名格式: GreenPulse_<taskID>_<timestamp>.log 或 GreenPulse_<timestamp>.log
        - 时间戳使用 UTC 时间
    """
    formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # 添加控制台处理器
    sHandler = logging.StreamHandler()
    sHandler.setFormatter(formatter)
    logger.addHandler(sHandler)

    # 生成日志文件名
    nowTime = pd.Timestamp.utcnow().strftime("%Y%m%d.%H%M%S.%f")
    if taskID and len(taskID) == 1:
        logFile = os.path.join(logPath, f"GreenPulse_{taskID[0]}_{nowTime}.log")
    else:
        logFile = os.path.join(logPath, f"GreenPulse_{nowTime}.log")
        
    # 确保日志目录存在
    os.makedirs(os.path.dirname(logFile), exist_ok=True)
    
    # 添加文件处理器
    fHandler = logging.FileHandler(logFile, encoding="utf-8")
    fHandler.setFormatter(formatter)
    logger.addHandler(fHandler)

    return logger


def setTaskLogger(logFileFullPath: List[str], logLevel: Union[str, int] = logging.DEBUG) -> logging.Logger:
    """设置任务日志记录器
    
    为特定任务配置日志记录器，支持同时输出到多个日志文件。
    
    Args:

        - logFileFullPath: 日志文件完整路径列表，支持同时输出到多个文件
        - logLevel: 日志级别，可以是字符串（如'DEBUG'）或logging模块的常量（如logging.DEBUG）
        
    Returns:

        - logging.Logger: 配置好的日志记录器实例
        
    Raises:

        - OSError: 当日志目录创建失败时抛出
        - ValueError: 当日志级别无效时抛出
        
    Example:
        ```python
        # 基本用法
        logger = setTaskLogger(
            logFileFullPath=["logs/task1.log", "logs/task1_debug.log"],
            logLevel=logging.DEBUG
        )
        
        # 使用字符串设置日志级别
        logger = setTaskLogger(
            logFileFullPath=["logs/task2.log"],
            logLevel="INFO"
        )
        
        # 记录不同级别的日志
        logger.debug("调试信息")
        logger.info("一般信息")
        logger.warning("警告信息")
        logger.error("错误信息")
        logger.critical("严重错误")
        ```
        
    Note:
        - 如果指定的目录不存在，会自动创建
        - 日志格式: "%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s"
        - 文件编码使用 UTF-8
    """
    formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
    logger = logging.getLogger()
    
    # 设置日志级别
    if isinstance(logLevel, str):
        logLevel = getattr(logging, logLevel.upper(), logging.DEBUG)
    logger.setLevel(logLevel)

    # 为每个日志文件添加处理器
    for path in logFileFullPath:
        try:
            dirPath = os.path.dirname(path)
            if dirPath and not os.path.exists(dirPath):
                os.makedirs(dirPath, exist_ok=True)
            fHandler = logging.FileHandler(path, encoding="utf-8")
            fHandler.setFormatter(formatter)
            logger.addHandler(fHandler)
        except Exception as e:
            logger.error(f"Failed to add file handler for {path}: {e}")
            continue

    return logger


def rmRootLogger(logPath: str = "log", logger: Optional[logging.Logger] = None) -> None:
    """清理过期的根日志文件
    
    删除指定目录中超过31天的日志文件。
    
    Args:

        - logPath: 日志文件所在目录，默认为 "log"
        - logger: 可选的日志记录器，用于记录错误信息
        
    Returns:

        - None
        
    Raises:

        - OSError: 当文件删除失败时记录错误（不会抛出）
        
    Example:
        ```python
        # 基本用法
        rmRootLogger()  # 清理默认目录中的过期日志
        
        # 指定日志目录
        rmRootLogger(logPath="/var/log/myapp")
        
        # 使用自定义日志记录器记录错误
        import logging
        logger = logging.getLogger(__name__)
        rmRootLogger(logPath="logs", logger=logger)
        ```
        
    Note:
        - 只删除文件名符合 GreenPulse_*.log 格式的日志文件
        - 从文件名中提取时间戳判断文件是否过期
        - 默认保留31天内的日志文件
        - 错误会被记录到提供的日志记录器（如果提供）
    """
    try:
        # 确保日志目录存在
        if not os.path.exists(logPath):
            return
            
        # 获取所有日志文件
        fileList = glob.glob(os.path.join(logPath, "GreenPulse_*.log"))
        
        for logFile in fileList:
            try:
                # 从文件名中提取时间戳
                # 格式: GreenPulse_<taskID>_YYYYMMDD.HHMMSS.ffffff.log 或 GreenPulse_YYYYMMDD.HHMMSS.ffffff.log
                base_name = os.path.basename(logFile)
                time_str = base_name.split('_')[-1].split('.')[0]  # 获取时间戳部分
                
                # 解析时间戳
                logUTCTime = pd.Timestamp(time_str, tz="UTC")
                
                # 删除超过31天的日志文件
                if (pd.Timestamp.utcnow() - logUTCTime).days > 31:
                    os.remove(logFile)
                    if logger and logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Deleted old log file: {logFile}")
                        
            except (ValueError, IndexError) as e:
                if logger:
                    logger.warning(f"Skipping invalid log file name: {logFile}: {e}")
                continue
                
    except Exception as e:
        if logger:
            logger.error(f"Error in rmRootLogger: {e}", exc_info=True)

def rmTaskLogger(logRootFullPath: List[str], logger: Optional[logging.Logger] = None) -> None:
    """清理过期的任务日志文件
    
    递归删除指定目录中超过31天的任务日志文件。
    
    Args:

        - logRootFullPath: 任务日志根目录列表，支持多个根目录
        - logger: 可选的日志记录器，用于记录错误和警告信息
        
    Returns:

        - None
        
    Raises:

        - OSError: 当文件或目录操作失败时记录错误（不会抛出）
        
    Example:
        ```python
        # 基本用法
        rmTaskLogger(["/var/log/tasks"])
        
        # 清理多个目录的日志
        rmTaskLogger([
            "/var/log/tasks",
            "/backup/logs/tasks"
        ])
        
        # 使用自定义日志记录器记录错误
        import logging
        logger = logging.getLogger(__name__)
        rmTaskLogger(["/var/log/tasks"], logger=logger)
        ```
        
    Note:
        - 目录结构应遵循: <logRootPath>/<staId>/log/<timeLiness>/YYYYMMDDHH/
        - 只删除超过31天的日志目录
        - 如果目录不存在或没有权限访问，会记录警告信息
        - 错误会被记录到提供的日志记录器（如果提供）
    """
    try:
        for logRootPath in logRootFullPath:
            # 检查根目录是否存在
            if not os.path.exists(logRootPath):
                if logger:
                    logger.warning(f"Log root directory does not exist: {logRootPath}")
                continue
                
            try:
                # 获取所有站点ID目录
                staIds = os.listdir(logRootPath)
            except Exception as e:
                if logger:
                    logger.error(f"Failed to list directory {logRootPath}: {e}")
                continue
                
            for staId in staIds:
                for timeLiness in TimeLiness.__iter__():
                    try:
                        # 构建日志目录路径
                        logDirPath = os.path.join(logRootPath, staId, "log", timeLiness.name)
                        
                        # 检查日志目录是否存在
                        if not os.path.exists(logDirPath):
                            if logger and logger.isEnabledFor(logging.DEBUG):
                                logger.debug(f"Log directory does not exist: {logDirPath}")
                            continue
                            
                        # 获取所有日期目录
                        try:
                            dirList = os.listdir(logDirPath)
                        except Exception as e:
                            if logger:
                                logger.error(f"Failed to list directory {logDirPath}: {e}")
                            continue
                            
                        for dirName in dirList:
                            try:
                                # 解析日期时间（格式：YYYYMMDDHH）
                                if len(dirName) < 10:
                                    if logger and logger.isEnabledFor(logging.DEBUG):
                                        logger.debug(f"Skipping invalid directory name (too short): {dirName}")
                                    continue
                                    
                                # 构建完整路径
                                dirPath = os.path.join(logDirPath, dirName)
                                
                                # 解析日期时间
                                dateStr = f"{dirName[0:4]}-{dirName[4:6]}-{dirName[6:8]} {dirName[8:10]}"
                                logUTCTime = pd.Timestamp(dateStr, tz="UTC")
                                
                                # 删除超过31天的日志目录
                                if (pd.Timestamp.utcnow() - logUTCTime).days > 31:
                                    try:
                                        if os.path.isfile(dirPath):
                                            os.remove(dirPath)
                                            if logger and logger.isEnabledFor(logging.DEBUG):
                                                logger.debug(f"Deleted old log file: {dirPath}")
                                        elif os.path.isdir(dirPath):
                                            # 如果是目录，递归删除
                                            import shutil
                                            shutil.rmtree(dirPath)
                                            if logger and logger.isEnabledFor(logging.DEBUG):
                                                logger.debug(f"Deleted old log directory: {dirPath}")
                                    except Exception as e:
                                        if logger:
                                            logger.error(f"Failed to delete {dirPath}: {e}")
                                        
                            except ValueError as e:
                                if logger and logger.isEnabledFor(logging.DEBUG):
                                    logger.debug(f"Skipping invalid directory name: {dirName}: {e}")
                                continue
                                
                    except Exception as e:
                        if logger:
                            logger.error(f"Error processing {logDirPath}: {e}")
                        continue
                        
    except Exception as e:
        if logger:
            logger.error(f"Error in rmTaskLogger: {e}", exc_info=True)
