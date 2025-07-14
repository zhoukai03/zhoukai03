import datetime as dt
import numpy as np
import pandas as pd
import pvlib

import modelset.base as base


class Baseline(base.BaseModel):

    def __init__(self, params, **kwargs):
        self.model = pd.DataFrame

    def train(self, train_data, val_data, **kwargs) -> None:
        #print("该模型为打底曲线，无需训练")
        pass

    def predict(self, data, **kwargs):
        result = data.copy()
        result['radi'] = 0
        x = self.model["fit_radi"]
        y = self.model["fit_pw"]
        print(data)
        for i, row in enumerate(data.iterrows()):
            # 1. 定义位置（纬度、经度、海拔）
            latitude = 36.87    # 纽约市纬度
            longitude = 93.37  # 纽约市经度
            altitude = 0         # 海拔高度（米）
            # 创建位置对象
            location = pvlib.location.Location(latitude, longitude, altitude=altitude)
            # 2. 定义时间序列
            times = pd.to_datetime([row[1][0]])
            # 3. 使用晴空模型计算晴空辐照度
            clearsky = location.get_clearsky(times=times, model='ineichen')
            result.iloc[i, -1] = clearsky['ghi']
            result.iloc[i, -1] = np.interp(clearsky['ghi'], x, y)
        return result

    def dump(self, file_path, **kwarg) -> None:
        #print("该模型为打底曲线，无需保存模型")
        pass

    def load(self, file_path, **kwarg):
        self.model = pd.read_csv("/mnt/PRESKY/project/FGGLYC/pc_default_data/pc_default_6328010200000000.csv")
