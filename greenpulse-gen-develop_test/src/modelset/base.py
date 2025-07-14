"""
该模块定义模型基类

模型基类定义了一个通用的模型接口，任何具体的模型都可以继承该基类并实现其中的抽象方法，
以便在不同的应用场景中进行模型训练、预测、保存和加载操作。
"""

import logging
import pandas as pd
from typing import Any
from abc import ABC, abstractmethod

from ..params import CStaParams
from ..datasets.dataLoader import CDataLoader


class BaseModel(ABC):
    """
    模型基类的使用方法:
    1. 继承模型基类，并实现其中的抽象方法。
    2. 使用子类对象进行模型的初始化、训练、预测、保存和加载操作。

    注意事项:
    1. 所有的子类必须实现基类中定义的所有抽象方法，否则会抛出异常。
    2. 在子类中可以根据具体需求添加额外的方法和属性。
    3. 在使用模型时，务必确保传入的数据格式和参数与模型的要求一致。
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
    def load(self, model, patternLogger: logging.Logger) -> None:
        """
        - 参数：
          - `model`: 模型对象。
          - `patternLogger`: 模型日志记录器。
        - 功能：加载模型。
        """

    @abstractmethod
    def predict(self, X: dict, taskDate: pd.Timestamp, staParam: CStaParams, patternLogger: logging.Logger,
                dataLoader: CDataLoader, **kwargs) -> pd.DataFrame:
        """
        - 参数：
          - `X`: 用于模型预测的输入数据。
          - `taskDate`: 预测日期。
          - `staParam`: 站点参数。
          - `patternLogger`: 模型日志记录器。
          - `dataLoader`: 数据加载器。
          - `**kwargs`: 其他可选参数。
        - 功能：对输入数据进行预测。
        """

    @abstractmethod
    def train(self, X: dict, Y: dict, taskDateList: list[pd.Timestamp], staParam: CStaParams,
              patternLogger: logging.Logger, dataLoader: CDataLoader, **kwargs) -> Any:
        """
        - 参数：
          - `X`: 用于模型训练的输入数据。
          - `Y`: 用于模型训练的输出数据。
          - `taskDateList`: 训练日期列表。
          - `staParam`: 站点参数。
          - `patternLogger`: 模型日志记录器。
          - `dataLoader`: 数据加载器。
          - `**kwargs`: 其他可选参数。
        - 功能：对输入数据进行训练。
        """

    @abstractmethod
    def tuning(self, X: dict, Y: dict, taskDateList: list[pd.Timestamp], staParam: CStaParams,
               patternLogger: logging.Logger, dataLoader: CDataLoader, **kwargs) -> Any:
        """
        - 参数：
          - `model`: 模型对象。
          - `patternLogger`: 模型日志记录器。
        - 功能：模型调优。
        """


class BasePostProcessor(ABC):
    """
    模型后处理基类。
    """

    @abstractmethod
    def __init__(self, staParam: CStaParams, **kwargs):
        """
        - 参数：
          - `staParam`: 站点参数。
          - `**kwargs`: 其他可选参数。
        - 功能：初始化模型后处理。
        """


    @abstractmethod
    def load(self, model, patternLogger: logging.Logger) -> None:
        """
        - 参数：
          - `model`: 模型对象。
          - `patternLogger`: 模型日志记录器。
        - 功能：加载模型。
        """


    @abstractmethod
    def fit(self, X, Y, taskDateList: list[pd.Timestamp], patternLogger: logging.Logger, **kwargs):
        """
        - 参数：
          - `X`: 模型预测数据。
          - `Y`: 考核基准数据。
          - `taskDateList`: 训练日期列表。
          - `**kwargs`: 其他可选参数。
        - 功能：后处理参数选优。
        """


    @abstractmethod
    def transform(self, X, patternLogger: logging.Logger, **kwargs):
        """
        - 参数：
          - `X`: 模型预测数据。
          - `**kwargs`: 其他可选参数。
        - 功能：加载原始数据进行模型后处理。
        """
