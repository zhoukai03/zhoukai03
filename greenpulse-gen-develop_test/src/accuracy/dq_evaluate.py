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

def load_dq_data(filetime, fcst_aging, obs_path, fcst_path):
    obsfile = obs_path + '/' + filetime[:6] + '/O_PV_FARM_WHOLE_' + filetime[:8] + '.csv'
    label = pd.read_csv(obsfile)
    label = label[['time', 'power']]
    label.rename(columns={'power': 'real_value'}, inplace=True)

    filetime = (datetime.strptime(filetime, "%Y%m%d") - timedelta(days=fcst_aging)).strftime('%Y%m%d')
    file_pattern = f"F_PV_FARM_WHOLE_240H_{filetime}*.csv"
    fcst_path1 = os.path.join(fcst_path, filetime[:6])
    matching_files = [f for f in os.listdir(fcst_path1) if f.startswith(f"F_PV_FARM_WHOLE_240H_{filetime}")]
    fcstfile = os.path.join(fcst_path1, matching_files[0])
    data = pd.read_csv(fcstfile)
#    data = data.head(96)
    data = data.iloc[fcst_aging * 96:(fcst_aging + 1) * 96]
    data = data[['time', 'power']]
    data.rename(columns={'power': 'pred'}, inplace=True)

    merged_data = pd.merge(label, data, on='time', how='inner')

    return merged_data

def bias_integral_power_new(da, r):
    pred = da['pred'].values
    real = da['real_value'].values
#    error = (real - pred) / pred * 100
    error = np.abs((real - pred) / pred) * 100
    error = np.where(np.abs(error) <= r *100, 0.0, error)
    # 单一预测点偏差积分电量=0.25*超出真值0.25部分的误差
    d = 0.25 * (abs(real - pred) - r * real)
    d = np.where(d < 0, 0.0, d)  # 低于0.25真值的是0
#    print(error)
    return error , d
#西北2019细则
def Short_score_point_day_2019_new(da, cap, day, r):
    '''
    : da: dataFrame ,columns=['time','real_value','pred']  一天的数据 长度为96
    : cap: 开机容量 float
    : return: dataFrame  columns=['time','max_error','electric','score']
    '''
    # pred==0,real<cap*0.03 -> abs_error = 0  and pred==0,real >= cap*0.03 -> abs_error = 1
    # pred>0 real=0 -> abs_error = 1
    da.loc[da.index[np.where((da['pred'] == 0) & (da['real_value'] <= cap * 0.03))[0]], ['real_value', 'pred']] = np.array([0, 0])
    da.loc[da.index[np.where((da['pred'] <= cap * 0.03) & (da['real_value'] == 0))[0]], ['real_value', 'pred']] = np.array([0, 0])
    da.loc[da.index[np.where((da['pred'] == 0) & (da['real_value'] > cap * 0.03))[0]], ['real_value', 'pred']] = np.array([0, 1])
    da.loc[da.index[np.where((da['pred'] > cap * 0.03) & (da['real_value'] == 0))[0]], ['real_value', 'pred']] = np.array([0, 1])

    #新能源大发
    condition_d1 = (40 <= da.index) & (da.index <= 64)
    #用电高峰
    condition_d2 = (24 <= da.index) & (da.index <= 36) | (68 <= da.index) & (da.index <= 88)

    # 新能源大发
    da1 = da[condition_d1]
    error1, d1 = bias_integral_power_new(da1, r)
    s1 = np.zeros_like(error1)
    for i in range(len(d1)):
        if error1[i] <= 0 :
            s1[i] = 0.2 * d1[i] *0.1
        else:
            s1[i] = 0.4 * d1[i] * 0.1

    # 用电高峰
    da2 = da[condition_d2]  #用电高峰
    error2, d2 = bias_integral_power_new(da2, r)
    s2 = np.zeros_like(error2)
    for i in range(len(d2)):
        if error2[i] <= 0:
            s2[i] = 0.4 * d2[i] * 0.1
        else:
            s2[i] = 0.2 * d2[i] * 0.1
    # 其他时段
    da3 = da[~condition_d1 & ~condition_d2]
    error3, d3 = bias_integral_power_new(da3, r)
    #print(error3)
    s3 = 0.2 * d3 * 0.1

    newda = pd.DataFrame({
        'timedelta': [f'd{day + 1}', f'd{day + 1}'],
        'moment': ['important', 'other'],
        'max_error': [max(np.max(abs(error1)), np.max(abs(error2))), np.nanmax(abs(error3))],
        'electric': [np.sum(d1) + np.sum(d2), np.sum(d3)],
        'score': [np.sum(s1) + np.sum(s2), np.sum(s3)],
    })
#    print(newda)
    return newda
#西北2023细则
def Short_score_point_day_2023(da, cap, day):
    '''
    : da: dataFrame ,columns=['time','real_value','pred']
    : cap: 开机容量 float
    : return: dataFrame  columns=['time','max_error','electric','score']
    '''
    #均在装机容量0.03以内不参与考核
    da.loc[da.index[np.where((da['pred'] <= cap * 0.03)  & (da['real_value'] <= cap * 0.03))[0]], ['real_value', 'pred']] = np.array([1, 1])

    pred = da['pred'].values
    real = da['real_value'].values

    pred = np.where(pred < 0, 0, pred)
    real = np.where(real < 0, 0, real)

    error = (real - pred) / real * 100
    error = np.where(np.abs(error) <= 20, 0.0, error)

    # 单一预测点偏差积分电量=0.20*超出真值0.2部分的误差
    d = 0.25 * (abs(real - pred) - 0.2 * real)
    d = np.where(d < 0, 0.0, d) #低于0.20真值的是0

    s = np.zeros_like(error)

    for i in range(len(error)):
        if 40 <= i <= 64:
            if error[i] ==0:
                s[i] =0
            elif error[i] < 0:
                s[i] = 0.05 * d[i] * 0.1
            else:
                s[i] = 0.1 * d[i] * 0.1
        elif 24 <= i <= 36 or 68 <= i <= 88:
            if error[i] ==0:
                s[i] =0
            elif error[i] < 0:
                s[i] = 0.15 * d[i] * 0.1
            else:
                s[i] = 0.05 * d[i] * 0.1
        else:
            if error[i] ==0:
                s[i] =0
            else:
                s[i] = 0.05 * d[i] * 0.1

    da['error'] = abs(error)
    da['d'] = d
    da['s'] = s

    condition_d1 = (40 <= da.index) & (da.index <= 64) | (24 <= da.index) & (da.index <= 36) | (68 <= da.index) & (da.index <= 88)

    # 分割成两个 DataFrame
    da1 = da[condition_d1] #重要时段
    da2 = da[~condition_d1]


    newda = pd.DataFrame({
        'timedelta': [f'd{day + 1}', f'd{day + 1}'],
        'moment': ['important', 'other'],
        'max_error': [np.max(da1['error'].values), np.max(da2['error'].values)],
        'electric': [np.sum(da1['d'].values), np.sum(da2['d'].values)],
        'score': [np.sum(da1['s'].values), np.sum(da2['s'].values)],
    })

    return newda
#华中细则
def huazhong_acc(trued, pred, cap, tag):
    n = len(trued)
    err = np.sqrt(np.sum((pred - trued) ** 2)) / (cap * np.sqrt(n))
    acc = (1 - err) * 100
    if tag == 'wind':
        if acc < 83:
            score = (83 - acc) * cap * 1
            score = np.round(score, 4)
        else:
            score = 0
    elif tag == 'solar':
        if acc < 85:
            score = (85 - acc) * cap * 1
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
def nanwang_acc(trued, pred, cap):
    cap_tmp = trued.copy()
    cap_tmp[trued < 0.2 * cap] = 0.2 * cap
    acc = 1 - np.sqrt(np.nansum(((trued - pred) / cap_tmp) ** 2) / len(trued))
    acc = np.round(acc * 100, 2)

    return acc

if __name__ == '__main__':
    # basic parameters
    parser = argparse.ArgumentParser(description='短期检验细则。')
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
    parser.add_argument('-fn', '--file_output_name', type=str, default='F_PV_ACC_SCORE_WHOLE_72H_',
                        help='the file output name.')
    #    parser.add_argument('-mo', '--map_output', type=str, default=None, help='the map output path.')
    parser.add_argument('-lo', '--log_output', type=str, default=None, help='the log output path.')
    parser.add_argument('-lf', '--log_file', type=str, default=None, help='the full path of log file output.')

    # acc & farm parameters
    parser.add_argument('-acc', '--acc_pick', type=str, default='xibei2019',
                        help='the acc score rules to pick, [nanwang | huabei | ..].')
    parser.add_argument('-c', '--cap', type=float, default=None, required=True, help='the capacity of the farm.')
    parser.add_argument('-dm', '--day_month', type=str, default='day',
                        help='the day for evaluate, or month for evaluate.')

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
            gv_r = 0.20
            main_df_2019 = pd.DataFrame()
            for day in range(3):
                t = (datetime.strptime(start_date, "%Y%m%d") - timedelta(days=day)).strftime('%Y%m%d')
                merged_data = load_dq_data(start_date,day,obs_path, pred_path)
                score_2019 = Short_score_point_day_2019_new(merged_data, cap, day, gv_r)
                main_df_2019 = pd.concat([main_df_2019, score_2019], ignore_index=True)
            main_df_2019.insert(0, 'time', str(start_date[:8]))
            QD1_2019 = main_df_2019[main_df_2019['timedelta'] == 'd1']['score'].sum()
            QD2_2019 = main_df_2019[main_df_2019['timedelta'] == 'd2']['score'].sum()
            QD3_2019 = main_df_2019[main_df_2019['timedelta'] == 'd3']['score'].sum()
            all_score_2019 = QD1_2019
            max_error_2019 = main_df_2019['max_error'].max()
            electric_2019 = main_df_2019['electric'].sum()
            all = pd.DataFrame([{
                'time': main_df_2019['time'].iloc[0],
                'timedelta': 'short-term',
                'moment': 'Weighted',
                'max_error': max_error_2019,
                'electric': electric_2019,
                'score': all_score_2019}])
            main_df_new = pd.concat([main_df_2019, all], ignore_index=True)
            main_df_new['score'] = main_df_new['score'] / 2
            outfile = os.path.join(file_output, start_date[:6], f"{file_output_name}{start_date[:8]}.csv")
            CheckDir(os.path.dirname(outfile))
            main_df_new.to_csv(outfile, sep=',', index=False)
            print(main_df_new)
        if acc_type == 'xibei2023':
            gv_r = 0.20
            main_df_2023 = pd.DataFrame()
            for day in range(3):
                t = (datetime.strptime(start_date, "%Y%m%d") - timedelta(days=day)).strftime('%Y%m%d')
                merged_data = load_dq_data(start_date,day,obs_path, pred_path)
                score_2023 = Short_score_point_day_2023(merged_data, cap, day)
                main_df_2023 = pd.concat([main_df_2023, score_2023], ignore_index=True)
            main_df_2023.insert(0, 'time', str(start_date[:8]))
            QD1_2023 = main_df_2023[main_df_2023['timedelta'] == 'd1']['score'].sum()
            QD2_2023 = main_df_2023[main_df_2023['timedelta'] == 'd2']['score'].sum()
            QD3_2023 = main_df_2023[main_df_2023['timedelta'] == 'd3']['score'].sum()
            all_score_2023 = 0.6 * QD1_2023 + 0.3 * QD2_2023 + 0.1 * QD3_2023
            max_error_2023 = main_df_2023['max_error'].max()
            electric_2023 = main_df_2023['electric'].sum()
            all = pd.DataFrame([{
                'time': main_df_2023['time'].iloc[0],
                'timedelta': 'short-term',
                'moment': 'Weighted',
                'max_error': max_error_2023,
                'electric': electric_2023,
                'score': all_score_2023}])
            main_df_new = pd.concat([main_df_2023, all], ignore_index=True)
            main_df_new['score'] = main_df_new['score'] / 2
            outfile = os.path.join(file_output, start_date[:6], f"{file_output_name}{start_date[:8]}.csv")
            CheckDir(os.path.dirname(outfile))
            main_df_new.to_csv(outfile, sep=',', index=False)
            print(main_df_new)
        if acc_type == 'huazhong':
            data = load_dq_data(start_date, 0, obs_path, pred_path)
            trued = data['real_value'].values
            pred = data['pred'].values
            acc, score = huazhong_acc(trued, pred, cap, mode_type)
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
        if acc_type == 'huadong':
            data = load_dq_data(start_date, 0, obs_path, pred_path)
            trued = data['real_value'].values
            pred = data['pred'].values
            acc = huadong_acc(trued, pred, cap)
            result_dict = {
                'time': [start_date],  # 将 start_date 转换为 datetime 对象
                'acc': [acc]  # 准确率
            }
            result_df = pd.DataFrame(result_dict)
            outfile = os.path.join(file_output, start_date[:6], f"{file_output_name}{start_date[:8]}.csv")
            CheckDir(os.path.dirname(outfile))
            result_df.to_csv(outfile, sep=',', index=False)
            print(result_df)
        if acc_type == 'huabei':
            data = load_dq_data(start_date, 0, obs_path, pred_path)
            trued = data['real_value'].values
            pred = data['pred'].values
            acc = huabei_acc(trued, pred, cap)
            result_dict = {
                'time': [start_date],  # 将 start_date 转换为 datetime 对象
                'acc': [acc]  # 准确率
            }
            result_df = pd.DataFrame(result_dict)
            outfile = os.path.join(file_output, start_date[:6], f"{file_output_name}{start_date[:8]}.csv")
            CheckDir(os.path.dirname(outfile))
            result_df.to_csv(outfile, sep=',', index=False)
            print(result_df)
        if acc_type == 'nanwang':
            data = load_dq_data(start_date, 0, obs_path, pred_path)
            trued = data['real_value'].values
            pred = data['pred'].values
            acc = nanwang_acc(trued, pred, cap)
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

