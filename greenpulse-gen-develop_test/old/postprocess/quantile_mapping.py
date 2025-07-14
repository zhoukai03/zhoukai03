# -*- coding: utf-8 -*-
"""
@Version: 3.9
@Time   : 2022/3/7
@Author : YeXiancai

分位数映射(Quantile Mapping, QM)方法通过将预报降水的CDF调整至与观测降水的CDF近似一致, 以此实现对数值模式输出数据的误差订正。
此代码实现经验分位数映射(EQM)
"""
import numpy as np
from scipy.stats import gaussian_kde, gamma
from sklearn.metrics import mean_squared_error, mean_absolute_error


class CorrectCDF(object):
    """ CDF订正（累积分布函数订正）

    通过寻找predicted与real之间的关系，然后将关系应用到cntPredicted上，修正结果

    Args:
        true_data: 历史样本的真实值; 列表
        fcst_data: 历史样本的预测值; 列表
        level: 分段数

    Examples:
        >>> import numpy as np
        >>> from mbai.cal import CorrectCDF
        >>>
        >>> History_TrueD = np.random.gamma(0.7, scale=50, size=1000)
        >>> History_FcstD = np.random.gamma(0.7, scale=50, size=1000)
        >>>
        >>> fcst_data = (70 - 20) * np.random.random_sample(size=21) + 20
        >>>
        >>> cdf = CorrectCDF(History_TrueD, History_FcstD, level=10000)
        >>>
        >>> result = cdf.correct(fcst_data)
    """

    def __init__(
            self,
            true_data=None,
            fcst_data=None,
            level: int = 10000
    ) -> None:
        self.true_data = true_data
        self.fcst_data = fcst_data
        self.level = level

        if (self.true_data is not None) and (self.fcst_data is not None):
            self.true_dist, self.fcst_dist = self.cdf_dist()

    def cdf_dist(self):
        """ 计算 true_data、fcst_data 各自的CDF分布

        Returns:
        """
        true_l = np.percentile(self.true_data, np.linspace(0, 100, self.level + 1))
        fcst_l = np.percentile(self.fcst_data, np.linspace(0, 100, self.level + 1))
        return true_l, fcst_l

    def correct(self, fcst_data, true_dist=None, fcst_dist=None):
        """ 订正

        Args:
            fcst_data: 待订正的数据
            true_dist: 累积分布情况; 设置后会替换 self.true_dist 进行计算
            fcst_dist: 累积分布情况; 设置后会替换 self.fcst_dist 进行计算

        Returns:
            订正后的数据
        """
        if (true_dist is not None) and (fcst_dist is not None):
            _true_dist = true_dist
            _fcst_dist = fcst_dist
        elif (self.true_dist is not None) and (self.fcst_dist is not None):
            _true_dist = self.true_dist
            _fcst_dist = self.fcst_dist
        else:
            raise ValueError('true_level or fcst_level not set')
        fcst_level = np.digitize(fcst_data, _fcst_dist) - 1
        fcst_correct = _true_dist[fcst_level]
        return fcst_correct


class CorrectCDF_Gamma(object):
    """ CDF订正（累积分布函数订正）

    Args:
        true_data: 历史样本的真实值; 列表
        fcst_data: 历史样本的预测值; 列表

    Examples:
        >>> import numpy as np
        >>> from mbai.cal import CorrectCDF_Gamma
        >>>
        >>> History_TrueD = np.random.gamma(0.7, scale=50, size=1000)
        >>> History_FcstD = np.random.gamma(0.7, scale=50, size=1000)
        >>>
        >>> fcst_data = (70 - 20) * np.random.random_sample(size=21) + 20
        >>>
        >>> cdf = CorrectCDF(History_TrueD, History_FcstD)
        >>>
        >>> result = cdf.correct(fcst_data)
    """

    def __init__(
            self,
            true_data=None,
            fcst_data=None,
    ) -> None:
        self.true_data = true_data
        self.fcst_data = fcst_data

        if (self.true_data is not None) and (self.fcst_data is not None):
            self.true_dist, self.fcst_dist = self.cal_dist()

    def cal_dist(self):
        """ 计算 Gamma 分布函数 """
        true_dist = gamma(*gamma.fit(self.true_data, floc=0))
        fcst_dist = gamma(*gamma.fit(self.fcst_data, floc=0))
        return true_dist, fcst_dist

    def correct(self, fcst_data, true_dist=None, fcst_dist=None):
        """ 订正

        Args:
            fcst_data: 待订正的数据
            true_dist: 累积分布情况; 设置后会替换 self.true_dist 进行计算
            fcst_dist: 累积分布情况; 设置后会替换 self.fcst_dist 进行计算

        Returns:
            订正后的数据
        """
        if (true_dist is not None) and (fcst_dist is not None):
            _true_dist = true_dist
            _fcst_dist = fcst_dist
        elif (self.true_dist is not None) and (self.fcst_dist is not None):
            _true_dist = self.true_dist
            _fcst_dist = self.fcst_dist
        else:
            raise ValueError('true_level or fcst_level not set')

        return _true_dist.ppf(_fcst_dist.cdf(fcst_data))

