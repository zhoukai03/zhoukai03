"""模型集管理模块

该模块提供了动态加载和初始化预测模型的功能。支持按时效类型和算法动态加载对应的模型实现。

主要功能:
1. 根据时效类型和算法名称动态加载对应的模型模块
2. 提供统一的模型获取接口，简化模型初始化过程
3. 支持模型版本管理

模块依赖:
    - importlib: 用于动态导入模块
    - CStaParams: 站点参数类，包含模型初始化所需的站点信息
    - TimeLiness: 时效类型枚举，定义支持的预测时效类型

示例:
    >>> from params import CStaParams
    >>> from config.TypeDefine import TimeLiness
    >>> from modelset import modelget
    >>> import logging
    >>>
    >>> # 初始化站点参数
    >>> sta_params = CStaParams()
    >>> sta_params.staId = "TEST001"
    >>> sta_params.staCap = 10.0  # MW
    >>>
    >>> # 获取短期预测模型
    >>> model = modelget(
    ...     sta_params,
    ...     TimeLiness.ST,  # 短期预测
    ...     "baseline",      # 基础算法
    ...     "v1.0",          # 模型版本
    ...     logger=logging.getLogger(__name__)
    ... )
"""

import importlib
import logging
from typing import Any, Type, Dict, Optional

from ..params import CStaParams
from ..config.TypeDefine import TimeLiness


def getVersion(timeLiness: TimeLiness, algorithm: str) -> Any:
    """根据时效类型和算法名称动态加载对应的模型模块
    
    该函数会根据时效类型和算法名称动态导入对应的Python模块。
    模块的路径格式为：`.{时效类型名称}.{算法名称}`。
    
    参数
    ----------
    timeLiness : TimeLiness
        时效类型枚举值，如 TimeLiness.ST（短期）、TimeLiness.MT（中期）等
    algorithm : str
        算法名称，对应模块的文件名（不含.py）
        
    返回
    -------
    module
        导入的Python模块对象
        
    异常
    --------
    ImportError
        当指定的时效类型或算法对应的模块不存在时抛出
        
    示例
    -------
    >>> from config.TypeDefine import TimeLiness
    >>> module = getVersion(TimeLiness.ST, "baseline")
    >>> print(module.__name__)
    'modelset.ST.baseline'
    """
    module_name = f".{timeLiness.name}.{algorithm}"
    try:
        # 动态导入当前包中的模块
        timeLinessModule = importlib.import_module(module_name, __name__)
        return timeLinessModule
    except ImportError as e:
        raise ImportError(
            f"Failed to import module '{module_name}'. "
            f"Make sure the module exists in the {__name__} package."
        ) from e
    except Exception as e:
        raise ImportError(
            f"Unexpected error while importing module '{module_name}': {str(e)}"
        ) from e


def modelget(
    staParam: CStaParams, 
    timeLiness: TimeLiness, 
    algorithm: str, 
    version: Optional[str] = None, 
    **kwargs
) -> Any:
    """获取指定配置的模型实例
    
    根据提供的参数动态加载并初始化对应的模型实例。
    
    参数
    ----------
    staParam : CStaParams
        包含站点配置信息的参数对象
    timeLiness : TimeLiness
        时效类型枚举值，如 TimeLiness.ST（短期）
    algorithm : str
        算法名称，对应模块的文件名（不含.py）
    version : str, optional
        模型版本，如果为None则使用algorithm作为版本名
    **kwargs
        其他传递给模型构造函数的参数
        
    返回
    -------
    Any
        初始化后的模型实例
        
    异常
    --------
    AttributeError
        当指定的版本在模块中不存在时抛出
    ImportError
        当无法加载指定的算法模块时抛出
    Exception
        模型初始化失败时可能抛出各种异常
        
    示例
    -------
    >>> from params import CStaParams
    >>> from config.TypeDefine import TimeLiness
    >>> import logging
    >>> 
    >>> # 配置日志
    >>> logging.basicConfig(level=logging.INFO)
    >>> logger = logging.getLogger(__name__)
    >>> 
    >>> # 初始化站点参数
    >>> sta_params = CStaParams()
    >>> sta_params.staId = "TEST001"
    >>> sta_params.staCap = 10.0  # MW
    >>> 
    >>> # 获取模型实例
    >>> model = modelget(
    ...     sta_params,
    ...     TimeLiness.ST,  # 短期预测
    ...     "baseline",      # 基础算法
    ...     "v1.0",          # 模型版本
    ...     logger=logger    # 日志记录器
    ... )
    """
    logger = kwargs.get("logger")
    if logger is not None:
        logger.info(f"Loading model: {timeLiness.name}.{algorithm}")
    
    # 动态导入模型模块
    model_module = getVersion(timeLiness, algorithm)
    
    # 如果未指定版本，则使用算法名作为版本
    if version is None:
        version = algorithm
    
    if logger is not None:
        logger.info(f"Initializing model: [{algorithm}] with version: [{version}]")
    
    try:
        # 获取模型类
        model_class = getattr(model_module, version)
        # 初始化模型实例
        model = model_class(staParam, **kwargs)
        
        if logger is not None:
            logger.info(f"Model initialized: {model}")
        
        return model
    except AttributeError as e:
        if logger is not None:
            logger.error(f"Model version '{version}' not found in module '{algorithm}'")
        raise AttributeError(
            f"Model version '{version}' not found in module '{algorithm}'. "
            f"Available versions: {[name for name in dir(model_module) if not name.startswith('_')]}"
        ) from e
