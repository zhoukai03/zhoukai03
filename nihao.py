import pandas as pd
import numpy as np
import glob
import os
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from datetime import datetime, timedelta
from tqdm import tqdm
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from pykrige.ok import OrdinaryKriging
from matplotlib.animation import FuncAnimation, PillowWriter  # 新增动画保存相关库
from matplotlib.widgets import Slider, Button

# 设置中文字体
plt.rcParams["font.family"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

def safe_read_csv(file):
    """安全读取CSV文件，提取小时信息并清洗异常值"""
    try:
        df = pd.read_csv(
            file,
            usecols=['Lon', 'Lat', 'bias'],
            dtype={'Lon': 'float32', 'Lat': 'float32', 'bias': 'float32'},
            engine='c'
        )
        
        # 异常值处理
        abnormal_values = [9999, -999, 999999, '9999', '-999', '999999', 'NaN', 'NA']
        df['bias'] = df['bias'].replace(abnormal_values, np.nan)
        
        # 过滤经纬度范围和有效数据
        valid_mask = (
            df['bias'].notna() &
            df['Lon'].between(70, 138) &
            df['Lat'].between(3, 55)
        )
        cleaned_df = df[valid_mask].copy()
        
        # 从文件名提取小时信息（忽略日期，只保留小时）
        filename = os.path.basename(file)
        try:
            time_str = filename.split('_')[-2][8:10]  # 提取小时部分（如"12"）
            hour = int(time_str)
            cleaned_df['hour'] = hour  # 给该文件的所有数据标记小时（0-23）
            return cleaned_df
        except:
            print(f"文件 {filename} 无法提取小时信息，格式可能不符")
            return None
    except Exception as e:
        print(f"读取文件 {os.path.basename(file)} 出错: {str(e)}")
        return None

def process_files(file_list):
    """处理所有文件，按小时（0-23）聚合所有站点数据"""
    all_data = []
    for file in tqdm(file_list, desc="处理文件中"):
        df = safe_read_csv(file)
        if df is not None and not df.empty:
            all_data.append(df)
    
    if not all_data:
        raise ValueError("未找到有效数据")
    
    # 合并所有数据并按小时+站点聚合（跨天平均）
    combined = pd.concat(all_data, ignore_index=True)
    
    # 按小时和经纬度分组，计算每个站点在各小时的平均偏差（跨所有天）
    hourly_data = combined.groupby(['hour', 'Lon', 'Lat'])['bias'].mean().reset_index()
    
    # 按小时排序
    unique_hours = sorted(hourly_data['hour'].unique())
    print(f"成功提取 {len(unique_hours)} 个小时的数据（0-23时）")
    return hourly_data, unique_hours

def kriging_interpolation(lon, lat, values, grid_lon, grid_lat):
    """克里金插值"""
    gridx = np.linspace(np.min(grid_lon), np.max(grid_lon), len(grid_lon))
    gridy = np.linspace(np.min(grid_lat), np.max(grid_lat), len(grid_lat))
    
    if len(lon) < 3:  # 数据点太少时返回空
        return np.full((len(gridy), len(gridx)), np.nan)
    
    try:
        OK = OrdinaryKriging(
            lon, lat, values, 
            variogram_model='exponential',
            verbose=False, 
            enable_plotting=False,
            nlags=8,
        )
        z, _ = OK.execute('grid', gridx, gridy)
        return z
    except:
        return np.full((len(gridy), len(gridx)), np.nan)

def plot_hourly_changes(hourly_data, unique_hours):
    """绘制小时级动态分布图+日变化周期图（增加保存功能）"""
    # 创建共用网格
    grid_lon = np.linspace(70, 138, 120, dtype='float32')
    grid_lat = np.linspace(3, 55, 120, dtype='float32')
    grid_lon, grid_lat = np.meshgrid(grid_lon, grid_lat)
    
    # 预处理所有小时的插值结果和全局统计量
    interpolated = []  # 存储每个小时的插值结果
    hourly_stats = []  # 存储每个小时的整体统计（用于日变化图）
    
    # 计算全局颜色范围（避免小时间颜色跳变）
    all_biases = hourly_data['bias'].dropna().values
    global_vmin = np.nanpercentile(all_biases, 2)
    global_vmax = np.nanpercentile(all_biases, 98)
    
    # 提前计算每个小时的插值结果
    print("预处理所有小时的插值结果...")
    for hour in tqdm(unique_hours, desc="插值计算中"):
        # 提取该小时的数据
        hour_data = hourly_data[hourly_data['hour'] == hour]
        
        # 3σ清洗该小时的异常值
        if len(hour_data) > 5:
            mean_val = hour_data['bias'].mean()
            std_val = hour_data['bias'].std()
            hour_data = hour_data[(hour_data['bias'] >= mean_val - 3*std_val) &
                                 (hour_data['bias'] <= mean_val + 3*std_val)]
        
        # 插值
        lon = hour_data['Lon'].values
        lat = hour_data['Lat'].values
        bias = hour_data['bias'].values
        grid_bias = kriging_interpolation(lon, lat, bias, grid_lon[0], grid_lat[:,0])
        interpolated.append(grid_bias)
        
        # 记录该小时的整体统计（用于日变化图）
        hourly_stats.append({
            'hour': hour,
            'mean_bias': hour_data['bias'].mean(),
            'std_bias': hour_data['bias'].std(),
            'count': len(hour_data)  # 有效站点数
        })
    
    # 创建双面板图形（左：空间分布，右：日变化周期）
    fig = plt.figure(figsize=(20, 8))
    ax_map = fig.add_subplot(121, projection=ccrs.PlateCarree())  # 左：空间分布图
    ax_diurnal = fig.add_subplot(122)  # 右：日变化周期图
    plt.subplots_adjust(bottom=0.25)  # 增加底部空间，容纳保存按钮
    
    # ----------------------
    # 左侧：空间分布图初始化
    # ----------------------
    ax_map.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=0.6)
    ax_map.add_feature(cfeature.BORDERS.with_scale('10m'), linestyle=':', linewidth=0.5)
    ax_map.add_feature(cfeature.LAND, facecolor='#F0F0F0', alpha=0.3)
    ax_map.set_extent([70, 138, 3, 55], crs=ccrs.PlateCarree())
    
    # 初始空间分布
    pcm = ax_map.pcolormesh(
        grid_lon, grid_lat, interpolated[0],
        cmap='coolwarm',
        vmin=global_vmin, vmax=global_vmax,
        transform=ccrs.PlateCarree(),
        shading='auto'
    )
    
    # 颜色条
    cbar = fig.colorbar(pcm, ax=ax_map, shrink=0.7, pad=0.02)
    cbar.set_label('小时平均Bias值', fontsize=12)
    
    # 网格和标题
    gl = ax_map.gridlines(draw_labels=True, linestyle='--', alpha=0.5)
    gl.top_labels = False
    gl.right_labels = False
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER
    map_title = ax_map.set_title(
        f'小时平均Bias分布 (0{unique_hours[0]}时)',
        fontsize=14, pad=20
    )
    
    # ----------------------
    # 右侧：日变化周期图初始化
    # ----------------------
    # 准备日变化数据
    hours = [stat['hour'] for stat in hourly_stats]
    means = [stat['mean_bias'] for stat in hourly_stats]
    stds = [stat['std_bias'] for stat in hourly_stats]
    
    # 绘制日变化曲线（均值±标准差）
    ax_diurnal.plot(hours, means, 'o-', color='blue', label='小时平均偏差')
    ax_diurnal.fill_between(
        hours,
        [m - s for m, s in zip(means, stds)],
        [m + s for m, s in zip(means, stds)],
        color='blue', alpha=0.2, label='±1标准差'
    )
    ax_diurnal.axhline(y=0, color='red', linestyle='--', alpha=0.5)  # 零偏差参考线
    
    # 添加每个小时的样本数（站点数）
    for i, stat in enumerate(hourly_stats):
        ax_diurnal.text(stat['hour'], stat['mean_bias'] + 0.1, 
                       f"{stat['count']}", ha='center', fontsize=9)
    
    # 设置X轴为24小时制
    ax_diurnal.set_xticks(range(0, 24, 2))  # 每2小时一个刻度
    ax_diurnal.set_xlim(-1, 24)  # 稍微扩展边界
    ax_diurnal.set_title('小时平均偏差日变化周期', fontsize=14, pad=20)
    ax_diurnal.set_xlabel('小时 (UTC+8)', fontsize=12)
    ax_diurnal.set_ylabel('平均Bias值', fontsize=12)
    ax_diurnal.grid(True, linestyle='--', alpha=0.6)
    ax_diurnal.legend()
    
    # 添加当前时刻标记线
    vline = ax_diurnal.axvline(x=hours[0], color='green', linestyle='-', linewidth=2, label='当前时刻')
    
    # ----------------------
    # 交互控件（新增保存按钮）
    # ----------------------
    # 滑动条控制
    ax_slider = plt.axes([0.2, 0.1, 0.65, 0.03])
    slider = Slider(
        ax=ax_slider,
        label='小时',
        valmin=0,
        valmax=len(unique_hours)-1,
        valinit=0,
        valstep=1
    )
    
    # 自动播放按钮
    ax_button = plt.axes([0.85, 0.1, 0.1, 0.03])
    play_button = Button(ax_button, '自动播放')
    
    # 保存动画按钮（新增）
    ax_save = plt.axes([0.7, 0.1, 0.1, 0.03])
    save_button = Button(ax_save, '保存动图')
    
    # ----------------------
    # 交互功能实现（含保存逻辑）
    # ----------------------
    # 滑动条更新函数
    def update(frame):
        frame = int(frame)  # 确保是整数索引
        hour = unique_hours[frame]
        # 更新空间分布图
        pcm.set_array(interpolated[frame].ravel())
        map_title.set_text(f'小时平均Bias分布 ({hour:02d}时)')
        
        # 更新日变化周期标记线
        vline.set_xdata([hour])
        
        fig.canvas.draw_idle()
    
    slider.on_changed(update)
    
    # 自动播放函数
    def animate(event):
        for i in range(len(unique_hours)):
            slider.set_val(i)
            plt.pause(0.8)  # 每小时停留0.8秒
    
    play_button.on_clicked(animate)
    
    # 保存动图函数（核心新增功能）
    def save_animation(event):
        print("开始保存动图...（可能需要几秒到几分钟）")
        
        # 定义动画帧更新函数（用于生成GIF）
        def animate_frame(i):
            update(i)  # 复用滑动条的更新逻辑
            return pcm, vline  # 返回需要更新的元素
        
        # 创建动画对象
        ani = FuncAnimation(
            fig, 
            animate_frame, 
            frames=len(unique_hours),  # 总帧数=小时数
            interval=800,  # 每帧停留800毫秒（与自动播放速度一致）
            blit=True  # 只更新变化的部分，加速渲染
        )
        
        # 保存为GIF（使用Pillow库，兼容性好）
        save_path = "hourly_bias_animation.gif"
        ani.save(
            save_path,
            writer=PillowWriter(fps=1.25),  # 1.25帧/秒 = 每帧0.8秒
            dpi=150  # 控制清晰度（值越高文件越大）
        )
        
        print(f"动图已保存至：{os.path.abspath(save_path)}")
        print("可在文件管理器中找到该GIF文件，双击即可播放")
    
    save_button.on_clicked(save_animation)  # 绑定保存按钮事件
    
    plt.tight_layout(rect=[0, 0.15, 1, 1])  # 预留底部控件空间
    plt.show()

def main():
    base_path = r"C:\Users\111\Desktop\武博卫星反演数据评估\FY4B_SSR_corrected"
    file_pattern = os.path.join(base_path, "**", "MSP3_PMSC_ENGSOLMFC_SSI_CHN_4KM_*_0000-0000.CSV")
    file_list = glob.glob(file_pattern, recursive=True)
    
    if not file_list:
        raise FileNotFoundError("未找到匹配的文件")
    
    print(f"找到 {len(file_list)} 个文件，开始处理...")
    hourly_data, unique_hours = process_files(file_list)
    
    # 绘制小时级动态图和日变化周期
    print("生成小时级动态分布图...")
    plot_hourly_changes(hourly_data, unique_hours)

if __name__ == '__main__':
    main()