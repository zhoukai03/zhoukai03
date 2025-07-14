"""
该模块为训练和预测提供通用的辅助函数
"""

import os
import numpy as np
import pandas as pd


def check_dir(path):
    """
    检查目前是否存在临时文件夹，若不存在则创建
    """
    if not os.path.exists(path):
        os.makedirs(path)
        print("Create temporary directory: ", path)


def get_subdir(base_dir):
    """
    获取指定基目录下的所有子目录列表。

    参数:
    base_dir: 基目录的路径，为字符串格式。

    返回值:
    subdir: 包含所有子目录名称的列表。
    """
    # 使用列表推导式遍历base_dir下的所有条目，仅保留子目录的名称
    subdir = [
        x for x in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, x))
    ]
    return subdir


def get_subfile(base_dir):
    """
    获取指定目录下的所有文件列表。

    参数:
    base_dir: 字符串，指定的目录路径。

    返回值:
    subfile: 列表，包含指定目录下所有文件的名称。
    """
    # 使用列表推导式遍历base_dir下的所有项，仅保留文件项
    subfile = [
        x for x in os.listdir(base_dir) if os.path.isfile(os.path.join(base_dir, x))
    ]
    return subfile


def add_hour_wind(data, type_):
    """
    增加小时平均和月平均风速/地面辐射特征
    """
    se_all = "Speed100" if (type_ == "wind") else "Groundradiation"
    data["hour_mean"] = 0
    # 小时平均
    for hour in np.arange(1, 24):
        select = data["hour"] == hour
        data[select]["hour_mean"] = np.nanmean(data[select][se_all])
    data["month_mean"] = 0
    # 月平均
    for month in np.arange(1, 24):
        select = data["month"] == month
        data[select]["month_mean"] = np.nanmean(data[select][se_all])
    return data


def feature_engine(area_info, data, type_):
    """
    特征工程
    """
    se_all = (
        ["Speed100", "Temp2"]
        if (type_ in area_info["风"].values)
        else ["Groundradiation", "Irradiance"]
    )
    # 时间周期设置
    ll_all = [3, 6, 4, 12, 24, 48, 96]
    # 增加时间滑动平均特征
    for ll in ll_all:
        for se in se_all:
            averaged_data = data[se].rolling(window=ll).mean()
            missing_indices = averaged_data.isnull()
            averaged_data[missing_indices] = averaged_data[missing_indices].fillna(
                method="ffill"
            )
            data[f"{se}_{ll}"] = averaged_data
    # 拆分出小时特征
    data["hour"] = data["Datetime"].map(lambda x: int(x[11:13]))
    # 拆分出月特征
    data["month"] = data["Datetime"].map(lambda x: x[5:7])
    data = add_hour_wind(data, type_)
    # 风速特征处理
    if type_ == "wind":
        # 逐层进行风向特征处理
        for lev in [str(l) for l in [10, 30, 50, 70, 90, 100]]:
            data[f"Direction{lev}"] = np.cos(data[f"Direction{lev}"] * np.pi / 360.0)
        # 100米风速处理
        data["Speed100_2"] = np.power(data["Speed100"], 2)
    return data


def sum_area(dir_list:list, area_dir:str, area_id):
    """
    前置条件为遍历区域下各场站获取路径构成dir_list
    读取区域路径下各场站预报txt,,检查文件生成情况并读取功率值进行统计
    输出area_dir下区域总功率文件DQYC_AREA_OUT_PREDICT_POWER.txt
    """
    power_list = []
    for sta_res in dir_list:
        res = pd.read_csv(sta_res,sep=',')
        power_list.append(res.Power.values)
    area_power = np.nansum(np.array(power_list),axis=0)
    id_value = np.ones((res.shape[0]))*int(area_id)
    area_df = pd.DataFrame({'AreaID':id_value, "Datetime":res['Datetime'].values, "Power":area_power.reshape(area_power.size)}, \
                               index=res.index)
    os.makedirs(area_dir, mode=0o777, exist_ok=True)
    save_file = os.path.join(area_dir, 'DQYC_AREA_OUT_PREDICT_POWER.txt')
    area_df.to_csv(save_file, sep=',' , index=None)


# 调整数据格式 数据df->numpy->tensor
def create_dataset(data:pd.DataFrame, target_features, input_features):
    import torch
    data_x = data[input_features]
    data_y = data[target_features]
    data_x = torch.from_numpy(data_x.to_numpy()).float()
    data_x = data_x.reshape(data_x.shape[0], 1, data_x.shape[1])
    data_y = torch.squeeze(torch.from_numpy(data_y.to_numpy()).float())
    return data_x, data_y

# ================================================
# 按时间筛选数据,用于按时间订正
def select_df(df:pd.DataFrame, st='06:00:00', et='19:00:00'):
    """
    光伏筛选夜间段功率置零
    df: 以timeindex为index的数据集
    注:昼夜时间不一定合理,参考63光伏区域早晚向外取1小时
    """
    df = df.set_index("Datetime")
    locs = df.index.indexer_between_time(st,et,include_start=True,include_end=True)
    s_loc = []
    for i in range(df.shape[0]):
        if not (i in locs):
            s_loc.append(i)

    return s_loc
