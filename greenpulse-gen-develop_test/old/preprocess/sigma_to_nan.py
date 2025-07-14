import numpy as np
import pandas as pd

def sigma_to_nan(data: pd.DataFrame, ratio):
    """
    把每一列中超出ratio倍sigma的值, 赋值为np.nan

    参数:
    - data: pd.DataFrame, 输入的数据框, 要求每一列都有均值和标准差可以计算。
    - ratio: 超出均值的倍数, 以此来确定要替换为np.nan的值的范围。

    返回值:
    - data: pd.DataFrame, 处理后的数据框, 超出指定范围的值已被替换为np.nan。
    - error: int, 被替换为np.nan的总元素数量。
    """
    error = 0
    for i in range(data.shape[1]):
        Ser1 = data.iloc[:, i]
        rule = (Ser1.mean() - ratio * Ser1.std() > Ser1) | (
            Ser1.mean() + ratio * Ser1.std() < Ser1
        )
        index = np.arange(Ser1.shape[0])[rule]
        error += index.size
        rule = np.array(rule)
        data.iloc[rule, i] = np.nan

    return data, error
