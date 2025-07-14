"""华中地区风光功率预测精度评估模块。

该模块实现了华中地区风光功率预测的精度评估规范，支持超短期和短期预测的日评估和月评估。
评估结果包括准确率（acc）和扣分（score）两个指标。

评估方法说明
-----------
1. 超短期日评估（ust_day）:
   - 计算预测值与观测值之间的平均绝对误差（MAE）
   - 结果包含 acc 和 score 两个指标

2. 超短期月评估（ust_month）:
   - 计算预测值与观测值之间的平均绝对误差（MAE）
   - 结果包含 acc 和 score 两个指标

3. 短期日评估（st_day）:
   - 计算预测值与观测值之间的均方根误差（RMSE）
   - 根据站点类型（风电/光伏）和容量计算扣分
   - 风电站点：当 acc < 83 时扣分 = (83 - acc) * 容量 * 1
   - 光伏站点：当 acc < 85 时扣分 = (85 - acc) * 容量 * 1
   - 结果包含 acc 和 score 两个指标

4. 短期月评估（st_month）:
   - 计算预测值与观测值之间的平均绝对误差（MAE）
   - 结果包含 acc 和 score 两个指标

使用示例
-------
```python
import pandas as pd
import logging
from accuracy.huazhong import huazhong
from ..params import CStaParams

# 初始化站点参数
sta_param = CStaParams()
sta_param.staCap = 100.0  # 设置容量为100MW
sta_param.staType = 'wind'  # 设置站点类型为风电

# 创建评估器
evaluator = huazhong(sta_param)

# 准备预测和观测数据
pred_data = {
    pd.Timestamp('2023-01-01'): pd.Series(
        [0.1, 0.2, 0.3],
        index=pd.date_range('2023-01-01 00:00:00', periods=3, freq='15T')
    )
}
obs_data = pd.Series(
    [0.15, 0.25, 0.35],
    index=pd.date_range('2023-01-01 00:00:00', periods=3, freq='15T')
)

# 执行评估
logger = logging.getLogger(__name__)
result = evaluator.ust_day(pred=pred_data, obs=obs_data, logger=logger)
print(result)
```

注意事项
-------
- 所有时间序列数据应使用 pandas 的 Series 或 DataFrame 格式
- 时间索引应包含时区信息（如 'Asia/Shanghai'）
- 预测数据和观测数据的时间范围应对齐
- 短期日评估要求数据长度为96个时间点（15分钟间隔）
- 站点容量（staCap）和类型（staType）必须在 CStaParams 中正确设置
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any
from ..params import CStaParams
from .base import BaseAccuracy

class huazhong(BaseAccuracy):
    """华中地区风光功率预测精度评估类。
    
    该类实现了华中地区风光功率预测的精度评估规范，支持超短期和短期预测的日评估和月评估。
    
    Parameters
    ----------
    staParam : CStaParams
        站点参数对象，包含站点容量、类型等信息。
    **kwargs : dict, optional
        其他可选参数。
        
    Attributes
    ----------
    staParam : CStaParams
        站点参数对象。
        
    See Also
    --------
    BaseAccuracy : 精度评估基类
    CStaParams : 站点参数类
    """
    
    def __init__(self, staParam: CStaParams, **kwargs):
        """初始化华中地区精度评估器。
        
        Parameters
        ----------
        staParam : CStaParams
            站点参数对象，必须包含以下属性：
            - staCap: 站点容量（MW）
            - staType: 站点类型（'wind' 或 'PV'）
        **kwargs : dict, optional
            其他可选参数，当前版本未使用。
            
        Notes
        -----
        - 站点容量（staCap）用于计算扣分
        - 站点类型（staType）影响扣分计算的标准
        """
        self.staParam = staParam

    def cdq_acc(self, da, cap, tag, label_column='real_value', pred_column='pred', delta=None, baseacc=None, **kwargs):
        """
        Args:
            da (pd.DataFrame): 输入数据
            cap (str, optional): 装机容量
            tag (str, optional): 场站预测类型
            label_column (str, optional): 实况标签列名. Defaults to 'real_value'.
            pred_column (str, optional): 预测标签列名. Defaults to 'pred'.
            delta (str, optional): 预测时刻, 重要时刻或其它时刻
            baseacc (str, optional): 基准准确率
        Returns:
            {acc (float): 准确率, score (float): 扣分}
        """
        obs = da[label_column].values
        pred = da[pred_column].values
        n = len(obs)
        squared_errors = (obs - pred) ** 2
        err = np.sqrt(np.sum(squared_errors)) / (cap * np.sqrt(n))
        acc = (1 - err) * 100 if err <= 1 else 0

        if tag == 'PV':
            score = (90 - acc) * cap * 1 if acc < 90 else 0
        elif tag == 'WD':
            score = (87 - acc) * cap * 1 if acc < 87 else 0
        else:
            logger.warning(f"未知站点类型：{tag}, score设为NaN")
            score = np.nan
        
        return {'acc': acc, 'score': score}

    def dq_acc(self, da, cap, tag, label_column='real_value', pred_column='pred', **kwargs):
        """
        Args:
            da (pd.DataFrame): 输入数据
            cap (str, optional): 装机容量
            tag (str, optional): 场站预测类型
            label_column (str, optional): 实况标签列名. Defaults to 'real_value'.
            pred_column (str, optional): 预测标签列名. Defaults to 'pred'.
        Returns:
            {acc (float): 准确率, score (float): 扣分}
        """
        obs = da[label_column].values
        pred = da[pred_column].values
        n = len(obs)
        squared_errors = (obs - pred) ** 2
        err = np.sqrt(np.nansum(squared_errors)) / (cap * np.sqrt(n))
        acc = (1 - err) * 100 if err <= 1 else 0

        # 计算扣分（score）
        if tag == 'WD':
            score = (83 - acc) * cap * 1 if acc < 83 else 0
        elif tag == 'PV':
            score = (85 - acc) * cap * 1 if acc < 85 else 0
        else:
            logger.warning(f"未知类型：{tag}, score 设为NaN")
            score = np.nan
        
        return {'acc': acc, 'score': score}


    def ust_day(self, pred: Dict[pd.Timestamp, pd.Series], obs: pd.Series, 
               logger: logging.Logger, **kwargs) -> Dict[pd.Timestamp, Dict[str, float]]:
        """计算超短期日评估结果。
        
        计算预测值与观测值之间的平均绝对误差（MAE）作为评估指标。
        
        Parameters
        ----------
        pred : Dict[pd.Timestamp, pd.Series]
            预测值字典，键为预测时间点，值为对应时间点的预测功率序列。
        obs : pd.Series
            观测功率序列，索引为时间戳。
        logger : logging.Logger
            日志记录器，用于记录评估过程中的信息。
        **kwargs : dict, optional
            其他可选参数，当前版本未使用。
            
        Returns
        -------
        Dict[pd.Timestamp, Dict[str, float]]
            评估结果字典，键为预测时间点，值为包含以下键的字典：
            - 'acc': 准确率（1 - 标准化MAE）
            - 'score': 扣分（当前版本为np.nan）
            
        Notes
        -----
        - 该方法会打印预测和观测数据，用于调试目的
        - 返回的score字段在当前版本中始终为np.nan
        """
        cap = self.staParam.staCap  # 获取容量参数
        sta_type = self.staParam.staType  # 获取预测类型参数
        result = {}
        logger.debug("开始执行超短期日评估")

        # 处理实况数据
        obs_df = pd.DataFrame(obs)
        obs_df = obs_df.reset_index()
        obs_df['Datetime'] = obs_df['Datetime'] + pd.Timedelta(hours=8)  # 传过来的数据均为世界时, 按照业务需转为北京时

        # 处理pred数据
        pred_df = pd.DataFrame(columns=['Datetime', 'pred'])
        for pred_bj_date, pred_series in pred.items():
            try:
                if len(pred_series) >= 8:
                    pred_time = pred_series.index[-1]
                    pred_value = pred_series.iloc[-1]
                    pred_df.loc[len(pred_df)] = [pred_time, pred_value]
            except Exception as e:
                logger.error(f"处理预测日期 {pred_bj_date} 时出错: {str(e)}")
                continue
        
        pred_df['Datetime'] = pred_df['Datetime'] + pd.Timedelta(hours=8)  # 传过来的数据均为世界时, 按照业务需转为北京时
        dates = pred_df['Datetime'].dt.date.unique()
        for date in dates:
            predi = pred_df[pred_df['Datetime'].dt.date == date]
            obsi = obs_df[obs_df['Datetime'].dt.date == date]
            predi = predi.merge(obsi, on='Datetime', how='inner')
            date = pd.Timestamp(date, tz='Asia/Shanghai')
            if len(predi) == 0:
                logger.warning(f"在 {date} 没有匹配的观测数据")
                result[date] = {"acc": np.nan, "score": np.nan}
                continue
            acc = self.cdq_acc(predi, cap, sta_type, label_column='power', pred_column='pred')
            result.update({date: acc})
            logger.debug(f"评估完成 - 评估日期: {date}, 细则结果：{acc}")
        
        return result
    
    def ust_month(self, pred: dict[pd.Timestamp, pd.Series], obs: pd.Series, logger: logging.Logger, **kwargs) -> dict[pd.Timestamp, dict[str, float]]:
        """
        - 参数：
          - `pred`: 预测值。
          - `obs`: 观测值。
          - `taskDate`: 任务日期。
          - `logger`: 日志记录器。
          - `**kwargs`: 其他可选参数。
        - 功能：计算评分细则。
        """
        result = dict()
        for taskDate, predSeries in pred.items():
            obsSeries = obs.loc[obs.index.isin(predSeries.index)]
            rmse_value = np.sqrt(np.mean((predSeries - obsSeries) ** 2))
            result.update({taskDate: {"acc": rmse_value, "score": np.nan}})

        return result

    def st_day(self, pred: Dict[pd.Timestamp, pd.Series], obs: pd.Series, 
              logger: logging.Logger, **kwargs) -> Dict[pd.Timestamp, Dict[str, float]]:
        """计算短期日评估结果。
        
        计算预测值与观测值之间的均方根误差（RMSE）作为评估指标，并根据站点类型和容量计算扣分。
        
        Parameters
        ----------
        pred : Dict[pd.Timestamp, pd.Series]
            预测值字典，键为预测时间点，值为对应时间点的预测功率序列。
        obs : pd.Series
            观测功率序列，索引为时间戳。
        logger : logging.Logger
            日志记录器，用于记录评估过程中的信息。
        **kwargs : dict, optional
            其他可选参数，当前版本未使用。
            
        Returns
        -------
        Dict[pd.Timestamp, Dict[str, float]]
            评估结果字典，键为预测时间点，值为包含以下键的字典：
            - 'acc': 准确率（1 - 标准化RMSE）
            - 'score': 扣分（根据准确率和站点类型计算）
            
        Notes
        -----
        - 风电站点：当 acc < 83 时扣分 = (83 - acc) * 容量 * 1
        - 光伏站点：当 acc < 85 时扣分 = (85 - acc) * 容量 * 1
        - 要求数据长度为96个时间点（15分钟间隔）
        - 所有时间都会转换为北京时间（Asia/Shanghai）
        """
        result = {}
        cap = self.staParam.staCap  # 获取容量参数（MW）
        sta_type = self.staParam.staType  # 获取站点类型（'wind' 或 'PV'）
        
        logger.info(f"开始短期日评估 - 容量: {cap}MW, 类型: {sta_type}")

        # 处理实况数据
        obs_df = pd.DataFrame(obs)
        obs_df = obs_df.reset_index()
        obs_df['Datetime'] = pd.to_datetime(obs_df['Datetime']) + pd.Timedelta(hours=8)  # 转为北京时

        # 处理pred数据, 并计算细则
        pred_df = pd.DataFrame(columns=['Datetime', 'pred'])
        for pred_bj_date, pred_series in pred.items():
            try:
                if len(pred_series) >= 96:
                    pred_time = pred_series.index[0:96]
                    pred_value = pred_series.iloc[0:96]
                    df_temp = pd.DataFrame()
                    df_temp['Datetime'] = pred_time
                    df_temp['pred'] = pred_value.values
                    df_temp['Datetime'] = df_temp['Datetime'] + pd.Timedelta(hours=8)  # 转为北京时
                    df_temp = df_temp.merge(obs_df, on='Datetime', how='inner')
                    # 计算细则
                    acc = self.dq_acc(df_temp, cap, sta_type, label_column='power', pred_column='pred')
                    check_date = df_temp['Datetime'].iloc[0].strftime("%Y%m%d")
                    check_date = pd.Timestamp(check_date, tz='Asia/Shanghai')
                    result[check_date] = acc
                    logger.info(f"评估完成 - 评估日期: {check_date}, 细则结果: {acc}")
            except Exception as e:
                logger.error(f"处理预测日期 {pred_bj_date} 时出错: {str(e)}")
                continue
        
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
