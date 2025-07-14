import logging
import numpy as np
import pandas as pd
from .base import BaseAccuracy
from ..params import CStaParams

class mae(BaseAccuracy):
    def __init__(self, staParam: CStaParams, **kwargs):
        """
        - 参数：
          - `staParam`: 站点参数。
          - `**kwargs`: 其他可选参数。
        - 功能：初始化模型。
        """
        pass

    def ust_day(self, pred: dict[pd.Timestamp, pd.Series], obs: pd.Series, logger: logging.Logger, **kwargs) -> dict[pd.Timestamp, dict[str, float]]:
        """
        - 参数：
          - `pred`: 预测值。
          - `obs`: 观测值。
          - `logger`: 日志记录器。
          - `**kwargs`: 其他可选参数。
        - 功能：计算评分细则。
        """
        result = dict()
        for taskDate, predSeries in pred.items():
          obsSeries = obs.loc[obs.index.isin(predSeries.index)]
          mae_value = np.mean(np.abs(predSeries - obsSeries))
          result.update({taskDate: {"acc": mae_value, "score": np.nan}})

        return result

    def ust_month(self, pred: dict[pd.Timestamp, pd.Series], obs: pd.Series, logger: logging.Logger, **kwargs) -> dict[pd.Timestamp, dict[str, float]]:
        """
        - 参数：
          - `pred`: 预测值。
          - `obs`: 观测值。
          - `logger`: 日志记录器。
          - `**kwargs`: 其他可选参数。
        - 功能：计算评分细则。
        """
        result = dict()
        for taskDate, predSeries in pred.items():
          obsSeries = obs.loc[obs.index.isin(predSeries.index)]
          mae_value = np.mean(np.abs(predSeries - obsSeries))
          result.update({taskDate: {"acc": mae_value, "score": np.nan}})

        return result

    def st_day(self, pred: dict[pd.Timestamp, pd.Series], obs: pd.Series, logger: logging.Logger, **kwargs) -> dict[pd.Timestamp, dict[str, float]]:
        """
        - 参数：
          - `pred`: 预测值。
          - `obs`: 观测值。
          - `logger`: 日志记录器。
          - `**kwargs`: 其他可选参数。
        - 功能：计算评分细则。
        """
        result = dict()
        for taskDate, predSeries in pred.items():
          obsSeries = obs.loc[obs.index.isin(predSeries.index)]
          mae_value = np.mean(np.abs(predSeries - obsSeries))
          result.update({taskDate: {"acc": mae_value, "score": np.nan}})

        return result

    def st_month(self, pred: dict[pd.Timestamp, pd.Series], obs: pd.Series, logger: logging.Logger, **kwargs) -> dict[pd.Timestamp, dict[str, float]]:
        """
        - 参数：
          - `pred`: 预测值。
          - `obs`: 观测值。
          - `logger`: 日志记录器。
          - `**kwargs`: 其他可选参数。
        - 功能：计算评分细则。
        """
        result = dict()
        for taskDate, predSeries in pred.items():
          obsSeries = obs.loc[obs.index.isin(predSeries.index)]
          mae_value = np.mean(np.abs(predSeries - obsSeries))
          result.update({taskDate: {"acc": mae_value, "score": np.nan}})

        return result
