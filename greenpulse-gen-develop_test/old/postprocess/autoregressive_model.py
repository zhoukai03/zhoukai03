import numpy as np
from statsmodels.tsa.ar_model import AutoReg


class AR(object):

    def __init__(self, x, lag):
        """
        初始化SomeClass实例。

        参数:
        - x: 输入数据，用于拟合自回归模型。

        属性:
        - x: 保存输入数据。
        - model: 自回归模型实例。
        - model_fit: 模型拟合结果。
        """
        self.x = x
        self.lag = lag
        # 拟合自回归模型
        self.model = AutoReg(self.x, lag)
        self.model_fit = self.model.fit()

    def forecast(self, start, end):
        """
        根据模型进行预测。

        参数:
        start : 预测的起始时间点。
        end : 预测的结束时间点。

        返回值:
        返回模型在给定时间范围内的预测结果。
        """

        return self.model_fit.predict(len(self.x) + start, len(self.x) + end)  # 使用训练好的模型进行预测


class AR_lte(object):

    def __init__(self, x, lag):
        """
        初始化SomeClass实例。

        参数:
        - x: 输入数据，用于拟合自回归模型。

        属性:
        - x: 保存输入数据。
        - model: 自回归模型实例。
        - model_fit: 模型拟合结果。
        """
        self.x = x
        self.lag = lag
        # 拟合自回归模型
        self.model = AR(self.x, self.lag).model
        self.model_fit = self.model.fit()

    def forecast(self, forecast_len, start, end):
        """
        根据模型进行预测。

        参数:
        start : 预测的起始时间点。
        end : 预测的结束时间点。

        返回值:
        返回模型在给定时间范围内的预测结果。
        """

        for i in range(forecast_len):
            np.append(self.x, self.model_fit.predict(i, i))
            self.model = AR(self.x, self.lag).model
            self.model_fit = self.model.fit()

        return self.model_fit.predict(len(self.x) + start, len(self.x) + end)  # 使用训练好的模型进行预测

