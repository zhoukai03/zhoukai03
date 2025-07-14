"""
该模块定义评分细则基类

评分细则基类定义了一个通用的评分细则接口，任何具体的评分细则都可以继承该基类并实现其中的抽象方法，
以便在不同的应用场景中进行评分细则的计算。
"""

import logging
import pandas as pd
from abc import ABC, abstractmethod
from ..params import CStaParams


class BaseAccuracy(ABC):
    """
    评分细则基类的使用方法:
    1. 继承评分细则基类，并实现其中的抽象方法。
    2. 使用子类对象进行评分细则的初始化、计算。

    注意事项:
    1. 所有的子类必须实现基类中定义的所有抽象方法，否则会抛出异常。
    2. 在子类中可以根据具体需求添加额外的方法和属性。
    3. 在使用评分细则时，务必确保传入的数据格式和参数与评分细则的要求一致。
    """

    @abstractmethod
    def __init__(self, staParam: CStaParams, **kwargs):
        """
        - 参数：
          - `staParam`: 站点参数。
          - `**kwargs`: 其他可选参数。
        - 功能：初始化模型。
        """

    @abstractmethod
    def ust_day(self, pred: dict[pd.Timestamp, pd.Series], obs: pd.Series, logger: logging.Logger, **kwargs) -> dict[pd.Timestamp, dict[str, float]]:
        """
        - 参数：
          - `pred`: 预测值。
          - `obs`: 观测值。 
          - `logger`: 日志记录器。
          - `**kwargs`: 其他可选参数。
        - 功能：计算评分细则。
        """

    @abstractmethod
    def ust_month(self, pred: dict[pd.Timestamp, pd.Series], obs: pd.Series, logger: logging.Logger, **kwargs) -> dict[pd.Timestamp, dict[str, float]]:
        """
        - 参数：
          - `pred`: 预测值。
          - `obs`: 观测值。
          - `logger`: 日志记录器。
          - `**kwargs`: 其他可选参数。
        - 功能：计算评分细则。
        """

    @abstractmethod
    def st_day(self, pred: dict[pd.Timestamp, pd.Series], obs: pd.Series, logger: logging.Logger, **kwargs) -> dict[pd.Timestamp, dict[str, float]]:
        """
        - 参数：
          - `pred`: 预测值。
          - `obs`: 观测值。
          - `logger`: 日志记录器。
          - `**kwargs`: 其他可选参数。
        - 功能：计算评分细则。
        """

    @abstractmethod
    def st_month(self, pred: dict[pd.Timestamp, pd.Series], obs: pd.Series, logger: logging.Logger, **kwargs) -> dict[pd.Timestamp, dict[str, float]]:
        """
        - 参数：
          - `pred`: 预测值。
          - `obs`: 观测值。
          - `logger`: 日志记录器。
          - `**kwargs`: 其他可选参数。
        - 功能：计算评分细则。
        """
