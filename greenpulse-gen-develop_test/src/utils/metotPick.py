import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import params as pp
import logging
from params import  CStaParams
import  warnings
warnings.filterwarnings("ignore")

class MeteorologicalSelector():
    """ 气象数据对比 """

    def __init__(self, params, logger: logging.Logger):
        self.params = params
        self.logger = logger
        # self.data = self.load_data()

    def load_data(self,nwp_data,obs_data):
        # 实况数据、nwp数据处理
        self.logger.info("加载实况数据...")
        if obs_data['obs_weather'] is not None: # 有实况气象优先用
            real_df = obs_data['obs_weather']
            # 获取对比列字段名称
            if self.params['mode'] =='solar':
                self.params['act_para_col'] = 'toradi' # 光伏实况列名称
                self.params['nwp_para_col'] = 'ghi' # 光伏nwp要素名称
            else:
                self.params['act_para_col'] =''
                self.params['nwp_para_col'] = 'win100_spd'
        else:#否则使用实况功率数据
            real_df = obs_data['obs_power']
            if self.params['mode'] == 'solar':
                self.params['act_para_col'] = 'power'  # 光伏实况列名称
                self.params['nwp_para_col'] = 'ghi'  # 光伏nwp要素名称
            else:
                self.params['act_para_col'] = 'power'
                self.params['nwp_para_col'] = 'win100_spd'
        self.logger.info("加载NWP数据...")

        # 执行重组预报气象数据
        reorganized_data = self._extract_next_day_forecasts(nwp_data)
        # 对每个模型的数据进行时区转换
        reorganized_data = self._convert_to_china_time(reorganized_data)
        return real_df,reorganized_data

    def select(self,nwp_data,obs_data):
        self.logger.info("计算NWP与实况数据相关性...")
        real_data,reorganized_nwp_data = self.load_data(nwp_data,obs_data)

        result = {}
        for name, tmp_nwp_data in reorganized_nwp_data.items():
            data = pd.merge(tmp_nwp_data, real_data, on='time')
            # 计算相关系数
            corr = data[self.params['nwp_para_col']].corr(data[self.params['act_para_col']])
            corr = np.nan_to_num(corr, nan=0.0)
            score = round(corr * 100)
            result[name] = {'score': score, 'rank': 1}  # 先都设为1，后面再排序
        # 根据score排序并设置rank
        if result:
            sorted_models = sorted(result.items(), key=lambda x: x[1]['score'], reverse=True)
            for rank, (name, _) in enumerate(sorted_models, 1):
                result[name]['rank'] = rank
        return result

    def _extract_next_day_forecasts(self,nwp_data):
        result = {}

        for model, run_data in nwp_data.items():
            model_dfs = []
            if run_data is not None:
                for run_time, forecast_df in run_data.items():
                    # 计算次日的时间范围
                    next_day_start = run_time + timedelta(days=1)
                    next_day_end = next_day_start + timedelta(days=1)

                    # 筛选出次日的预报数据
                    mask = (forecast_df['time'] >= next_day_start) & (forecast_df['time'] < next_day_end)
                    next_day_forecast = forecast_df[mask].copy()

                    if not next_day_forecast.empty:
                        # 添加起报时间列
                        next_day_forecast['run_time'] = run_time
                        model_dfs.append(next_day_forecast)

            if model_dfs:
                # 合并该模型的所有预报数据
                result[model] = pd.concat(model_dfs, ignore_index=True)

        return result

    def _convert_to_china_time(self,dict_df):
        # 将时间列和起报时间列都转换为中国时间
        for model in dict_df:
            # print(model)
            if not dict_df[model].empty:
                dict_df[model]['time'] = pd.to_datetime(dict_df[model]['time']).dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai').dt.tz_localize(None)
                dict_df[model]['run_time'] = pd.to_datetime(dict_df[model]['run_time']).dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai').dt.tz_localize(None)
        return dict_df

def PickNWP(params, NWP: dict, OBS: dict, logger: logging.Logger) :
    """
    新能源功率预测气象寻优函数
    参数:
        params(CStaParams): 站点参数类型，包含必要站点配置参数
        NWP(dict): 气象预测数据字典，数据格式为 { Name:{ 起报时间:{ 预测数据(pd.DataFrame) } } }
        OBS(dict): 气象预测数据字典，数据格式为 { Name:{ 预测数据(pd.DataFrame) } }
        logger: 日志记录器
    返回:
        模型选优评分和排名，例如 { Name: { score:99, rank:1 } }
    """
    try:

        # 初始化选择器并执行选择
        selector = MeteorologicalSelector(params, logger)
        corr_nwp = selector.select(NWP,OBS)

        logger.info("NWP评比完成")
        return corr_nwp

    except Exception as e:
        logger.warning(f"NWP评比完成失败: {str(e)}")
        raise

if __name__=='__main__':


    #  NWP 数据

    nwp_data = {
        "ECMWF": {
            datetime(2023, 1, 1, 0): pd.DataFrame({
                "time": [datetime(2023, 1, 2, 12), datetime(2023, 1, 2, 13)],
                "win100_spd": [15.2, 16.1],
                "ghi": [0, 0]
            }),
            datetime(2023, 1, 1, 12): pd.DataFrame({
                "time": [datetime(2023, 1, 2, 14), datetime(2023, 1, 2, 15)],
                "win100_spd": [14.8, 15.3],
                "ghi": [1, 2]
            })
        },
        "GFS": {
            datetime(2023, 1, 1, 0): pd.DataFrame({
                "time": [datetime(2023, 1, 2, 12), datetime(2023, 1, 2, 13)],
                "win100_spd": [15.5, 16.3],
                "ghi": [-100, 0]
            })
        }
    }
 #  OBS 数据
    obs_data = {
        "obs_weather": pd.DataFrame({
            "time": [datetime(2023, 1, 2, 20), datetime(2023, 1, 2, 21)],
            "temperature": [15.3, 16.0],
            "toradi": [860, 910]
        }),
        "obs_power": pd.DataFrame({
            "time": [datetime(2023, 1, 2, 20), datetime(2023, 1, 2, 21)],
            "power": [120.5, 135.2]
        })
    }


    deploy_params = {
        'mode': 'solar',  # 电站类型 str solar wind
    }
    import logging

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    a = PickNWP(deploy_params,nwp_data,obs_data,logger)
    print(a)