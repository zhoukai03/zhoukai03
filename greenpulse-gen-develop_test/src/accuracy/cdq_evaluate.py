# -*- coding: UTF-8 -*-
import numpy as np
import pandas as pd
import os
import argparse
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def CheckDir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def load_cdq_data(filetime, fcst_aging, obs_path, fcst_path):
    # 将输入的字符串转换为datetime对象
    start_time = datetime.strptime(filetime, "%Y%m%d")

    # 初始化时间列表
    time_list = []

    # 生成96个时间戳，每个间隔15分钟
    for i in range(96):
        time_list.append(start_time + timedelta(minutes=15 * i))

    # 根据 fcst_aging 计算时间偏移量
    if fcst_aging == 1:
        time_delta = timedelta(minutes=45)
    elif fcst_aging == 2:
        time_delta = timedelta(minutes=105)
    elif fcst_aging == 3:
        time_delta = timedelta(minutes=165)
    elif fcst_aging == 4:
        time_delta = timedelta(minutes=225)
    else:
        raise ValueError("fcst_aging must be 1, 2, 3, or 4")

    # 初始化结果列表
    result_data = []

    # 遍历每个时间点
    for time in time_list:
        # 计算调整后的时间（用于文件名）
        adjusted_time = time - time_delta
        # 将调整后的时间转换为 yyyymmddhhmm 格式
        adjusted_time_str = adjusted_time.strftime("%Y%m%d%H%M")
        # 构建文件名模式
        file_pattern = f"F_PV_FARM_WHOLE_4H_{adjusted_time_str}*.csv"
        fcst_path1 = os.path.join(fcst_path, adjusted_time_str[:6])
        # 在 fcst_path 中查找匹配的文件
        matching_files = [f for f in os.listdir(fcst_path1) if f.startswith(f"F_PV_FARM_WHOLE_4H_{adjusted_time_str}")]

        if not matching_files:
            raise FileNotFoundError(f"No matching file found for {file_pattern} in {fcst_path1}")

        # 读取第一个匹配的文件
        file_path = os.path.join(fcst_path1, matching_files[0])
        df = pd.read_csv(file_path)

        # 将时间列转换为 datetime 格式（假设时间列名为 'time'）
        df['time'] = pd.to_datetime(df['time'])

        # 将原始的 time 转换为与 df['time'] 相同的格式（yyyy-mm-dd HH:MM:SS）
        time_formatted = time.strftime("%Y-%m-%d %H:%M:%S")
        time_formatted = pd.to_datetime(time_formatted)

        # 查找与原始 time 匹配的行
        matched_row = df[df['time'] == time_formatted]

        if matched_row.empty:
            raise ValueError(f"No matching time {time_formatted} found in file {file_path}")

        # 提取 power 值（假设 power 列名为 'power'）
        power = matched_row['power'].values[0]

        # 将结果添加到列表中
        result_data.append({
            'time': time_formatted,
            'pred': power
        })

    # 将结果转换为 DataFrame
    result_df = pd.DataFrame(result_data)
#    obs_infile = obs_path + filetime + '_power.csv'
    obs_infile = obs_path + '/' + filetime[:6] + '/O_PV_FARM_WHOLE_' + filetime[:8] + '.csv'
    obs_data = pd.read_csv(obs_infile)
    obs_data = obs_data.rename(columns={'power': 'trued'})
    obs_data['time'] = pd.to_datetime(obs_data['time'])
    merged_data = pd.merge(obs_data, result_df, on='time', how='inner')

    return merged_data

# 西北考核
def xibei_acc(trued, pred, cap):
    ind = np.where((trued <= cap * 0.03) & (pred <= cap * 0.03))
    trued[ind] = 0
    pred[ind] = 0
    p = pred
    r = trued
    mae = np.sum(np.abs(r - p))
    raa = np.nansum(np.abs((r / (r + p)) - 0.5) * (np.abs(r - p) / mae))
    raa = (1 - 2 * raa) * 100
    raa = np.round(raa, 2)

    return raa


def xibei_score_2019(trued, pred, cap):
    '''
    # 考核第2h预测结果
    '''
    acc = xibei_acc(trued, pred, cap)

    if acc < 75:
        score = (75 - acc) * cap * 0.015 / 10
        score = np.round(score, 4)
    else:
        score = 0

    return acc, score


def xibei_score_2023(trued, pred, cap, tag, baseacc):
    '''
    考核第1、2、3、4小时预测结果
    baseacc: wind(1h/2h/3h/4h): 80/75/70/65; solar(1h/2h/3h/4h): 85/80/75/70
    '''
    acc = xibei_acc(trued, pred, cap)

    if tag == 'important':
        if acc < baseacc:
            score = (baseacc - acc) * cap * 0.0015 / 10
            score = np.round(score, 4)
        else:
            score = 0
    else:
        if acc < baseacc:
            score = (baseacc - acc) * cap * 0.0003 / 10
            score = np.round(score, 4)
        else:
            score = 0

    return acc, score


# 华中考核
def huazhong_acc(trued, pred, cap):
    n = len(trued)
    err = np.sqrt(np.sum((pred - trued) ** 2)) / (cap * np.sqrt(n))
    acc = (1 - err) * 100
    return acc


def huazhong_score(trued, pred, cap, tag):
    '''
    考核第4h预测结果, 月平均准确率wind >= 87%, solar >= 90%
    '''
    acc = huazhong_acc(trued, pred, cap)

    if tag == 'wind':
        if acc < 87:
            score = (87 - acc) * cap * 1
            score = np.round(score, 4)
        else:
            score = 0
    elif tag == 'solar':
        if acc < 90:
            score = (90 - acc) * cap * 1
            score = np.round(score, 4)
        else:
            score = 0

    return acc, score


# 华东考核
def huadong_acc(trued, pred, cap):
    mse = np.sqrt(np.mean(np.square((trued - pred) / cap)))
    accR = 1 - mse
    accR = np.round(accR * 100, 4)

    return accR


# 华北考核
def huabei_acc(trued, pred, avail_cap):
    aa = np.square(trued - pred)
    bb = np.abs(trued - pred)
    cc = np.sum(np.abs(trued - pred))
    if cc == 0:
        acc = 100
    else:
        acc = (1 - np.sqrt(np.sum(aa * bb / cc)) / avail_cap) * 100

    return acc


# 南网准确率
def nanwang_acc(trued, pred, cap):
    cap_tmp = trued.copy()
    cap_tmp[trued < 0.2 * cap] = 0.2 * cap
    acc = 1 - np.sqrt(np.nansum(((trued - pred) / cap_tmp) ** 2) / len(trued))
    acc = np.round(acc * 100, 2)

    return acc


if __name__ == '__main__':
#    data = pd.read_csv('/home/chengnan/chengnan/cdqyc/check/guangdongriqian.csv')
#    data = data.rename(columns={'Unnamed: 0': 'time', 'obs': 'trued'})
#    data = data.dropna()
#    trued = data['trued'].values
#    pred = data['pred'].values
#    cap = 1500  # MW
    # basic parameters
    parser = argparse.ArgumentParser(description='超短期检验细则。')
    parser.add_argument('-v', '--verbose', action="store_true", help='if print and save log or not.')
    parser.add_argument('-o', '--output', default='logs/', help='the output path of log file.')
    parser.add_argument('-n', '--name', type=str, default='multi_cmp', help='the name of log file.')
    parser.add_argument('-m', '--mode', type=str, default='solar', choices=['solar', 'wind'],
                        help='the type of farm to evaluate.')
    # path parameters
    parser.add_argument('-label', '--label_path', type=str, default='./', help='the actual label path.')
    parser.add_argument('-pred', '--pred_path_list', type=str, default='./', help='the predict path list.')
#    parser.add_argument('-fa', '--cdq_fcst_aging', type=int, default='2', help='the cdq fcst aging.')

    # date parameters
    parser.add_argument('-sd', '--start_date', type=str, default=datetime.now().strftime('%Y%m%d'),
                        help='the start date of compare, [format: YYYYMMDD].')
    parser.add_argument('-ed', '--end_date', type=str, default=datetime.now().strftime('%Y%m%d'),
                        help='the end date of compare, [format: YYYYMMDD].')

    # output parameters
    parser.add_argument('-fo', '--file_output', type=str, default='./', help='the file output path.')
    parser.add_argument('-fn', '--file_output_name', type=str, default='F_PV_ACC_SCORE_WHOLE_4H_', help='the file output name.')
#    parser.add_argument('-mo', '--map_output', type=str, default=None, help='the map output path.')
    parser.add_argument('-lo', '--log_output', type=str, default=None, help='the log output path.')
    parser.add_argument('-lf', '--log_file', type=str, default=None, help='the full path of log file output.')

    # acc & farm parameters
    parser.add_argument('-acc', '--acc_pick', type=str,  default='xibei2019',
                        help='the acc score rules to pick, [nanwang | huabei | ..].')
    parser.add_argument('-c', '--cap', type=float, default=None, required=True, help='the capacity of the farm.')
    parser.add_argument('-dm', '--day_month', type=str, default='day', help='the day for evaluate, or month for evaluate.')


    args = parser.parse_args()
    print(args)
    cap = args.cap
    start_date = args.start_date
    end_date = args.end_date
    file_output = args.file_output
    file_output_name = args.file_output_name
    log_output = args.log_output
    log_file = args.log_file
    obs_path = args.label_path
    pred_path = args.pred_path_list
    acc_type = args.acc_pick
    dm_type = args.day_month
    mode_type = args.mode

    acc_list = []
    score_list = []

    while start_date <= end_date:
        if acc_type == 'xibei2019':
            # 西北2019细则
            data = load_cdq_data(start_date, 2, obs_path, pred_path)
            trued = data['trued'].values
            pred = data['pred'].values
            acc, score = xibei_score_2019(trued, pred, cap)
            result_dict = {
                'time': [start_date],  # 将 start_date 转换为 datetime 对象
                'acc': [acc],  # 准确率
                'score': [score]  # 分数
            }
            result_df = pd.DataFrame(result_dict)
            print(result_df)
            if dm_type == 'day':
                outfile = os.path.join(file_output, start_date[:6], f"{file_output_name}{start_date[:8]}.csv")
                CheckDir(os.path.dirname(outfile))
                result_df.to_csv(outfile,sep=',',index=False)
                print('西北2019考核:', acc, score)
            elif dm_type == 'month':
                acc_list.append(acc)
                score_list.append(score)
        elif acc_type == 'xibei2023':
            # 西北2023细则
            # baseacc: wind(1h/2h/3h/4h): 80/75/70/65; solar(1h/2h/3h/4h): 85/80/75/70
            data = load_cdq_data(start_date, 2, obs_path, pred_path)
            trued = data['trued'].values
            pred = data['pred'].values
            data['time'] = pd.to_datetime(data['time'])
            cond = (((data['time'].dt.time >= pd.to_datetime('00:00:00').time()) & (
                        data['time'].dt.time <= pd.to_datetime('06:00:00').time())) |
                    ((data['time'].dt.time >= pd.to_datetime('09:00:00').time()) & (
                                data['time'].dt.time <= pd.to_datetime('10:00:00').time())) |
                    ((data['time'].dt.time >= pd.to_datetime('16:00:00').time()) & (
                                data['time'].dt.time <= pd.to_datetime('17:00:00').time())) |
                    (data['time'].dt.time >= pd.to_datetime('22:00:00').time()))
            # 重要时段
            h1_df0 = data.loc[~cond]
            h2_df0 = data.loc[~cond]
            h3_df0 = data.loc[~cond]
            h4_df0 = data.loc[~cond]
            acc1_0, score1_0 = xibei_score_2023(h1_df0['trued'].values, h1_df0['pred'].values, cap, 'important', 80)
            acc2_0, score2_0 = xibei_score_2023(h1_df0['trued'].values, h1_df0['pred'].values, cap, 'important', 75)
            acc3_0, score3_0 = xibei_score_2023(h1_df0['trued'].values, h1_df0['pred'].values, cap, 'important', 70)
            acc4_0, score4_0 = xibei_score_2023(h1_df0['trued'].values, h1_df0['pred'].values, cap, 'important', 65)
            acc0 = (acc1_0 + acc2_0 + acc3_0 + acc4_0) / 4
            score0 = score1_0 + score2_0 + score3_0 + score4_0
            # 非重要时段
            h1_df1 = data.loc[cond]
            h2_df1 = data.loc[cond]
            h3_df1 = data.loc[cond]
            h4_df1 = data.loc[cond]
            acc1_1, score1_1 = xibei_score_2023(h1_df1['trued'].values, h1_df1['pred'].values, cap, 'other', 80)
            acc2_1, score2_1 = xibei_score_2023(h1_df1['trued'].values, h1_df1['pred'].values, cap, 'other', 75)
            acc3_1, score3_1 = xibei_score_2023(h1_df1['trued'].values, h1_df1['pred'].values, cap, 'other', 70)
            acc4_1, score4_1 = xibei_score_2023(h1_df1['trued'].values, h1_df1['pred'].values, cap, 'other', 65)
            acc1 = (acc1_1 + acc2_1 + acc3_1 + acc4_1) / 4
            score1 = score1_1 + score2_1 + score3_1 + score4_1
            acc = np.round((acc0 + acc1) / 2, 4)
            score = np.round(score0 + score1, 4)
            print('西北2023考核:', acc, score)
            result_dict = {
                'time': [start_date],  # 将 start_date 转换为 datetime 对象
                'acc': [acc],  # 准确率
                'score': [score]  # 分数
            }
            result_df = pd.DataFrame(result_dict)
            print(result_df)
            outfile = os.path.join(file_output, start_date[:6], f"{file_output_name}{start_date[:8]}.csv")
            CheckDir(os.path.dirname(outfile))
            result_df.to_csv(outfile, sep=',', index=False)
        elif acc_type == 'huazhong':
            # 华中细则
            data = load_cdq_data(start_date, 4, obs_path, pred_path)
            trued = data['trued'].values
            pred = data['pred'].values
#            acc, score = huazhong_score(trued, pred, cap, 'wind')
#            print('华中细则风电考核:', acc, score)
#            acc, score = huazhong_score(trued, pred, cap, 'solar')
#            print('华中细则光伏考核:', acc, score)
            acc, score = huazhong_score(trued, pred, cap, mode_type)
            result_dict = {
                'time': [start_date],  # 将 start_date 转换为 datetime 对象
                'acc': [acc],  # 准确率
                'battery': [score]  # 分数
            }
            result_df = pd.DataFrame(result_dict)
            outfile = os.path.join(file_output, start_date[:6], f"{file_output_name}{start_date[:8]}.csv")
            CheckDir(os.path.dirname(outfile))
            result_df.to_csv(outfile, sep=',', index=False)
            print(result_df)
        elif acc_type == 'huadong':
            # 华东细则 预测值每个点为16次预测的平均值; 风电大于等于96
            data = load_cdq_data(start_date, 2, obs_path, pred_path)
            trued = data['trued'].values
            pred = data['pred'].values
            acc = huadong_acc(trued, pred, cap)
            print('华东细则考核:', acc)
            result_dict = {
                'time': [start_date],  # 将 start_date 转换为 datetime 对象
                'acc': [acc]  # 准确率
            }
            result_df = pd.DataFrame(result_dict)
            outfile = os.path.join(file_output, start_date[:6], f"{file_output_name}{start_date[:8]}.csv")
            CheckDir(os.path.dirname(outfile))
            result_df.to_csv(outfile, sep=',', index=False)
            print(result_df)
        elif acc_type == 'huabei':
            data = load_cdq_data(start_date, 2, obs_path, pred_path)
            trued = data['trued'].values
            pred = data['pred'].values
            # 华北细则 全天每个点的准确率取平均, 共96个; 风电和光伏acc大于等于90%,
            acc0 = huabei_acc(trued, pred, cap)
            acc1 = huabei_acc(trued, pred, cap)
            print('华北细则考核:', np.round((acc0 + acc1) / 2, 2))
            result_dict = {
                'time': [start_date],  # 将 start_date 转换为 datetime 对象
                'acc': [np.round((acc0 + acc1) / 2, 2)]  # 准确率
            }
            result_df = pd.DataFrame(result_dict)
            outfile = os.path.join(file_output, start_date[:6], f"{file_output_name}{start_date[:8]}.csv")
            CheckDir(os.path.dirname(outfile))
            result_df.to_csv(outfile, sep=',', index=False)
            print(result_df)
        elif acc_type == 'nanwang':
            # 南网准确率 预测值每个点为16次预测的均值  风电acc不低于65%, 光伏acc不低于
            data = load_cdq_data(start_date, 2, obs_path, pred_path)
            trued = data['trued'].values
            pred = data['pred'].values
            acc = nanwang_acc(trued, pred, cap)
            print('南网细则考核:', acc)
            result_dict = {
                'time': [start_date],  # 将 start_date 转换为 datetime 对象
                'acc': [acc]  # 准确率
            }
            result_df = pd.DataFrame(result_dict)
            outfile = os.path.join(file_output, start_date[:6], f"{file_output_name}{start_date[:8]}.csv")
            CheckDir(os.path.dirname(outfile))
            result_df.to_csv(outfile, sep=',', index=False)
            print(result_df)
        start_date = (datetime.strptime(start_date, "%Y%m%d") + timedelta(days=1)).strftime('%Y%m%d')
    if dm_type == 'month':
        avg_acc = sum(acc_list) / len(acc_list)
        avg_score = sum(score_list) / len(score_list)
        month_result_dict = {
            'time': [start_date[:6]],  # 将 start_date 转换为 datetime 对象
            'acc': [avg_acc],  # 准确率
            'score': [avg_score]  # 分数
        }
        month_result_df = pd.DataFrame(month_result_dict)
        outfile = os.path.join(file_output, start_date[:6], f"{file_output_name}{start_date[:6]}.csv")
        CheckDir(os.path.dirname(outfile))
        month_result_df.to_csv(outfile, sep=',', index=False)

