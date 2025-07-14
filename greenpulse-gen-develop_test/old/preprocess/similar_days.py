import os
import pandas as pd
import math
import numpy as np


def similar(input_path1, input_path2, out_path):
    def compare_rows(row):
        df1_value = pd.to_numeric(row['df1'], errors='coerce')
        df2_value = pd.to_numeric(row['df2'], errors='coerce')
        if not np.isnan(df1_value) and not np.isnan(df2_value):
            if 0 <= row['df2'] <= 3:
                if math.fabs(row['df2'] - row['df1']) <= 0.5:
                    return 1
                else:
                    return 0
            elif 3 < row['df2'] <= 5:
                if math.fabs(row['df2'] - row['df1']) <= 1:
                    return 1
                else:
                    return 0
            elif 5 < row['df2'] <= 7:
                if math.fabs(row['df2'] - row['df1']) <= 2:
                    return 1
                else:
                    return 0
            elif 7 < row['df2'] <= 11:
                if math.fabs(row['df2'] - row['df1']) <= 3:
                    return 1
                else:
                    return 0
            elif row['df2'] > 11:
                if math.fabs(row['df2'] - row['df1']) <= 4:
                    return 1
                else:
                    return 0
        else:
            return 'nan值'

    df1 = pd.read_csv(input_path1, sep='\s+')  # 测试集数据
    df2 = pd.read_csv(input_path2, sep='\s+')  # 训练集数据
    df1['date'] = pd.to_datetime(df1['Datetime'])
    df2['date'] = pd.to_datetime(df2['Datetime'])
    start_date = pd.to_datetime('2022-02-21')
    end_date = pd.to_datetime('2023-02-18')
    current_date = start_date
    similar_result = []
    data_result = pd.DataFrame()
    time = []
    corr = []
    while current_date <= end_date:
        end_of_4th_day = current_date + pd.Timedelta(days=3)
        subset = df2[(df2['date'] >= current_date) & (df2['date'] <= end_of_4th_day)]
        subset = subset.reset_index(drop=True)
        # print(f'当前相似日的数据为：{subset}')
        df1 = df1.reset_index(drop=True)
        pearson_corr = round(subset['Speed100'].corr(df1['Speed100'], method='pearson'), 2)
        corr.append(pearson_corr)
        combined_df = pd.concat([subset['Speed100'], df1['Speed100']], axis=1, keys=['df2', 'df1'])
        combined_df['comparison_result'] = combined_df.apply(compare_rows, axis=1)
        filtered_df = combined_df[combined_df['comparison_result'] != 'nan值']
        total_count = len(filtered_df)
        count_0 = filtered_df['comparison_result'].value_counts().get(0, 0)
        count_1 = filtered_df['comparison_result'].value_counts().get(1, 0)
        if count_0 != 0:
            percentage_1 = round(count_1 / total_count, 2)
            similar_result.append(percentage_1)
            # print(f'占比为 1 的比例（相似的比例为）：{percentage_1:.2%}')
            # 控制相似比大小，输出训练集数据
            if percentage_1 > 0.5:
                data_result = pd.concat([data_result, subset], ignore_index=True)
                # print(f'当前相似日的数据为：{data_result}')
        time.append(current_date)
        current_date += pd.Timedelta(days=1)
        print(current_date)

    result_df_00 = pd.DataFrame(data_result)
    result_df_01 = pd.DataFrame(similar_result)
    result_df_02 = pd.DataFrame(corr)
    # print(f'similar为: {result_df_01.head(10)}')
    # print(f'corr为: {result_df_02.head(10)}')
    # print(time[:5])
    result_df_03 = pd.concat([result_df_01, result_df_02], axis=1, keys=['similar', 'corr'])
    result_df_04 = pd.DataFrame(time)
    similar_result_df = pd.concat([result_df_04, result_df_03], axis=1)
    print(similar_result_df.describe())
    similar_result_df.to_csv(os.path.join(out_path, 'similar_result.csv'), index=False, header=['data', 'similar', 'corr'])
    data_result_df = result_df_00.drop_duplicates(subset=['date'])
    data_result_df.to_csv(
        os.path.join(out_path, "similar_data_result.csv"), index=False
    )
