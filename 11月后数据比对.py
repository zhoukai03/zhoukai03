import os
import glob
import pandas as pd
from datetime import datetime, timedelta
import rasterio
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from tqdm import tqdm
import pytz

# 设置中文显示
plt.rcParams["font.family"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

# ==================== 配置参数 ====================
# 站点信息
STATION_NAME = "启辉"
STATION_LON, STATION_LAT = 100.51, 36.02  # 经纬度

# 路径配置
BASE_PATH = r"C:\Users\111\Desktop\武博卫星反演数据评估\FY4B_SSR_corrected"
CSV_PATH = r"C:\Users\111\Desktop\qihui_obs_update.csv"
OUTPUT_DIR = os.path.join(BASE_PATH, "output_plots")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 时间参数
START_MONTH = 11  # 只处理11月及之后的数据
UTC_TO_CST = timedelta(hours=8)  # UTC转北京时间偏移量

# SSI验证参数
SSI_VALID_RANGE = (0, 1500)  # 合理物理范围 (W/m²)
NODATA_VALUES = [-9999, 65535, np.nan]  # 无效值标记

# ==================== 函数定义 ====================
def safe_extract_ssi(tif_file, lon, lat):
    """安全提取SSI值，包含严格验证"""
    try:
        with rasterio.open(tif_file) as src:
            data = src.read(1)
            row, col = src.index(lon, lat)
            
            # 边界检查
            if not (0 <= row < data.shape[0] and 0 <= col < data.shape[1]):
                return None
                
            value = data[row, col]
            
            # 有效性验证
            if (value in NODATA_VALUES) or (not SSI_VALID_RANGE[0] <= value <= SSI_VALID_RANGE[1]):
                return None
                
            return float(value)
    except Exception as e:
        print(f"处理失败 {os.path.basename(tif_file)}: {str(e)}")
        return None

def parse_time(filename):
    """从文件名解析时间并转换为北京时间"""
    try:
        datetime_str = filename.split('_')[-2][:10]  # 提取前10位 (YYYYMMDDHH)
        utc_time = datetime.strptime(datetime_str, "%Y%m%d%H")
        
        # 只保留11月及之后的数据
        if utc_time.month < START_MONTH:
            return None
            
        # UTC转北京时间
        return utc_time + UTC_TO_CST
    except:
        return None

def process_obs_data(csv_path, start_time=None, end_time=None):
    """处理地面观测数据，返回北京时间DataFrame"""
    try:
        # 读取CSV并解析时间
        obs_df = pd.read_csv(
            csv_path,
            parse_dates=['Datetime'],
            date_format='mixed'
        )
        
        # 确保时间列是datetime类型
        obs_df['Datetime'] = pd.to_datetime(obs_df['Datetime'], errors='coerce')
        obs_df = obs_df.dropna(subset=['Datetime'])
        
        # 假设CSV中的时间已经是北京时间，无需转换
        # 过滤无效值和指定时间范围
        obs_df = obs_df[obs_df['radi'] > 0]
        
        if start_time and end_time:
            obs_df = obs_df[
                (obs_df['Datetime'] >= start_time) & 
                (obs_df['Datetime'] <= end_time)
            ]
            
        return obs_df
    except Exception as e:
        print(f"地面观测数据处理失败: {str(e)}")
        return pd.DataFrame()

# ==================== 主流程 ====================
if __name__ == "__main__":
    # 1. 处理卫星数据 (UTC时间)
    print("\n开始提取卫星数据(UTC时间)...")
    tif_files = glob.glob(os.path.join(BASE_PATH, "**", "MSP3_PMSC_ENGSOLMFC_SSI_CHN_4KM_*.TIF"), recursive=True)
    print(f"找到 {len(tif_files)} 个TIFF文件...")
    
    ssi_data = []
    for tif_file in tqdm(tif_files, desc="处理进度"):
        cst_time = parse_time(os.path.basename(tif_file))  # 返回的已经是北京时间
        if not cst_time:
            continue
            
        ssi = safe_extract_ssi(tif_file, STATION_LON, STATION_LAT)
        if ssi is not None:
            ssi_data.append({'time': cst_time, 'ssi': ssi})

    # 转换为DataFrame
    ssi_df = pd.DataFrame(ssi_data).sort_values('time').drop_duplicates('time')
    print(f"\n有效卫星数据点数(11月及之后): {len(ssi_df)}/{len(tif_files)}")
    
    # 2. 处理地面观测数据 (北京时间)
    print("\n处理地面观测数据(北京时间)...")
    obs_df = process_obs_data(
        CSV_PATH,
        start_time=ssi_df['time'].min() if not ssi_df.empty else None,
        end_time=ssi_df['time'].max() if not ssi_df.empty else None
    )
    print(f"有效地面观测点数: {len(obs_df)}")

    # 3. 时间序列绘图
    if not ssi_df.empty:
        plt.figure(figsize=(16, 8))
        
        # 绘制卫星数据 (已转换为北京时间)
        plt.plot(ssi_df['time'], ssi_df['ssi'], 
                 'b-', marker='o', markersize=5, 
                 label=f'FY4B SSI ({STATION_NAME})', alpha=0.7)
        
        # 绘制地面观测数据
        if not obs_df.empty:
            plt.plot(obs_df['Datetime'], obs_df['radi'], 
                     'r-', marker='s', markersize=4, 
                     label='地面观测辐射', alpha=0.7)
        
        # 图形美化
        plt.title(f'太阳辐射观测对比 (北京时间)\n{STATION_NAME}站 ({STATION_LON}°E, {STATION_LAT}°N)', fontsize=14)
        plt.xlabel('时间 (北京时间)', fontsize=12)
        plt.ylabel('辐射值 (W/m²)', fontsize=12)
        plt.grid(True, linestyle=':', alpha=0.5)
        
        # 时间轴设置
        ax = plt.gca()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        plt.gcf().autofmt_xdate()
        
        plt.legend(fontsize=10, loc='upper left')
        plt.tight_layout()
        
        # 保存图片
        output_path = os.path.join(OUTPUT_DIR, f"{STATION_NAME}_辐射对比_北京时间.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\n对比图已保存至: {output_path}")
        plt.show()

    # 4. 保存处理结果
    if not ssi_df.empty:
        ssi_df.to_csv(os.path.join(OUTPUT_DIR, "ssi_data_cst.csv"), index=False)
    if not obs_df.empty:
        obs_df.to_csv(os.path.join(OUTPUT_DIR, "obs_data_cst.csv"), index=False)