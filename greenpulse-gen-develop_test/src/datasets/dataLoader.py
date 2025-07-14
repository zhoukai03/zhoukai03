"""数据加载模块，用于从多种数据源加载和处理气象及功率数据。

该模块提供了数据加载、处理和分析的功能，支持从CSV文件、NetCDF文件和PostgreSQL数据库
中加载气象和功率数据，并进行格式转换、时间序列处理和缓存管理。

主要功能
--------
- 从多种数据源加载数据：
  - CSV文件
  - NetCDF文件
  - PostgreSQL数据库
- 数据格式转换和标准化
- 时间序列数据处理和重采样
- 数据缓存管理
- 光伏计算
- YAML配置文件解析

类
--
CDataLoader
    数据加载器类，提供统一的数据加载接口

函数
----
readYamlDataConfig(fileYaml: str) -> Dict[str, Any]
    从YAML文件读取数据配置

cal_poa(lat, lon, tm, ghi=None, dni=None, dhi=None)
    计算光伏发电量

示例
----
>>> import logging
>>> import psycopg2
>>> from datetime import datetime
>>>
>>> # 配置日志
>>> logging.basicConfig(level=logging.INFO)
>>> logger = logging.getLogger(__name__)
>>>
>>> # 初始化数据库连接
>>> db_conn = psycopg2.connect(
...     dbname="your_db",
...     user="your_user",
...     password="your_password",
...     host="your_host",
...     port="5432"
... )
>>>
>>> # 创建数据加载器
>>> data_loader = CDataLoader(
...     meotoCachePaths=["./cache/meteo"],
...     meotoOriginalCsvPaths=["./data/original/meteo"],
...     meotoBusinessCsvPaths=["./data/business/meteo"],
...     powerOriginalCsvPaths=["./data/original/power"],
...     powerBusinessCsvPaths=["./data/business/power"],
...     logger=logger,
...     DataBase=db_conn,
...     DataBaseURL="localhost",
...     DataBaseName="your_db",
...     DataBasePort="5432",
...     DataBaseUser="your_user",
...     DataBasePassword="your_password"
... )
>>>
>>> # 加载数据
>>> data = data_loader.OBSLoadPoint()
>>> data = data_loader.FCLoadPoint()
>>> data = data_loader.NWPLoadPoint()

注意事项
--------
1. 确保数据源路径存在且可读
2. 数据库连接参数必须完整且正确
3. 时间序列数据应使用UTC时区
4. 大数据量时注意内存使用
5. 使用后及时关闭数据库连接

异常
----
FileNotFoundError
    当数据文件不存在时抛出
ValueError
    当参数无效或数据格式错误时抛出
psycopg2.Error
    当数据库操作失败时抛出
Exception
    其他未处理的异常
"""

import os
import pathlib
import traceback
import yaml
import logging
import psycopg2
import pandas as pd
import datetime as dt
import numpy as np
from pvlib.forecast import GFS
from typing import Union, Dict, List, Optional, Any, Tuple
from ..config.TypeDefine import meteoSourceDataType
from ..utils import IO

import pytz
from pvlib.location import Location
from pvlib import irradiance
from pvlib.solarposition import get_solarposition


def readYamlDataConfig(fileYaml: str = "dataConfig.yaml") -> Dict[str, Any]:
    """从YAML文件读取数据配置

    从指定的YAML配置文件中加载数据源配置信息，返回配置字典。

    参数
    ----------
    fileYaml : str, optional
        YAML配置文件路径，默认为"dataConfig.yaml"

    返回
    -------
    dict
        包含配置信息的字典

    异常
    --------
    FileNotFoundError
        当配置文件不存在时抛出
    yaml.YAMLError
        当YAML文件格式错误时抛出

    示例
    -------
    >>> config = readYamlDataConfig("config/data_config.yaml")
    >>> print(config['database']['host'])
    'localhost'
    """
    try:
        with open(fileYaml, "r", encoding="utf-8") as rf:
            crf = rf.read()
            yamlData = yaml.load(crf, Loader=yaml.FullLoader)
        return yamlData or {}
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"YAML解析错误: {e}")
    except Exception as e:
        raise Exception(f"读取配置文件失败: {e}")


def cal_poa(lat: float, lon: float, tm: pd.DataFrame, ghi=None, dni=None, dhi=None) -> np.ndarray:
    """计算光伏发电量（Plane of Array Irradiance）。
    
    根据给定的地理位置、时间以及可选的辐照度数据，计算光伏板阵列接收到的总辐照度。
    如果未提供GHI、DNI、DHI数据，则使用PVLib库计算晴朗天空条件下的辐照度。
    
    Parameters
    ----------
    lat : float
        纬度，单位：度（-90到90）
    lon : float
        经度，单位：度（-180到180）
    tm : pd.DataFrame
        包含时间戳的DataFrame，用于计算太阳位置
    ghi : array-like, optional
        水平面总辐射（Global Horizontal Irradiance）
    dni : array-like, optional
        直接法向辐射（Direct Normal Irradiance）
    dhi : array-like, optional
        散射水平辐射（Diffuse Horizontal Irradiance）
        
    Returns
    -------
    numpy.ndarray
        光伏板阵列接收到的总辐照度（W/m²）
        
    Notes
    -----
    - 光伏板倾斜角度默认为纬度值
    - 光伏板方位角默认为180度（朝南）
    - 使用PVLib库进行太阳位置和辐照度计算
    
    Examples
    --------
    >>> import pandas as pd
    >>> times = pd.date_range('2023-01-01 12:00', periods=1, freq='H')
    >>> poa = cal_poa(39.9, 116.4, times)
    """
    tz = pytz.timezone('UTC')
    location = Location(lat, lon, tz=tz)
    # 计算晴朗天空辐照度
    clearsky = location.get_clearsky(tm)
    solar_position = get_solarposition(tm, lat, lon)

    if ghi is None:
        ghi = clearsky['ghi'].values
    if dni is None:
        dni = clearsky['dni'].values
    if dhi is None:
        dhi = clearsky['dhi'].values

    poa_global = irradiance.get_total_irradiance(
        surface_tilt=lat,     # 假设光伏板倾斜角度为纬度
        surface_azimuth=180,  # 假设光伏板方位角为180度（朝南）
        ghi=np.array(ghi),
        dni=np.array(dni),
        dhi=np.array(dhi),
        solar_zenith=solar_position['apparent_zenith'],
        solar_azimuth=solar_position['azimuth']
    )

    clearsky['poa'] = poa_global['poa_global'].values

    return poa_global['poa_global'].values


class CDataLoader:
    """数据加载器类，用于从多种数据源加载和处理气象及功率数据。
    
    提供统一接口从CSV文件、NetCDF文件和PostgreSQL数据库加载气象和功率数据，
    支持数据格式转换、时间序列处理和缓存管理。
    
    Parameters
    ----------
    meotoCachePaths : list of str, optional
        气象数据缓存路径列表，用于存储和读取缓存的气象数据
    meotoOriginalCsvPaths : list of str, optional
        原始气象数据CSV文件路径列表，包含原始气象观测数据
    meotoBusinessCsvPaths : list of str, optional
        业务气象数据CSV文件路径列表，包含经过业务处理的气象数据
    powerOriginalCsvPaths : list of str, optional
        原始功率数据CSV文件路径列表，包含原始功率观测数据
    powerBusinessCsvPaths : list of str, optional
        业务功率数据CSV文件路径列表，包含经过业务处理的功率数据
    logger : logging.Logger, optional
        日志记录器实例，用于记录运行日志
    DataBase : psycopg2.extensions.connection, optional
        PostgreSQL数据库连接对象，如果提供则优先使用
    DataBaseURL : str, optional
        数据库服务器地址，用于建立新连接
    DataBaseName : str, optional
        数据库名称，用于建立新连接
    DataBasePort : str, optional
        数据库端口，用于建立新连接
    DataBaseUser : str, optional
        数据库用户名，用于建立新连接
    DataBasePassword : str, optional
        数据库密码，用于建立新连接
    
    Attributes
    ----------
    timelinessList : list of str
        支持的数据时效性列表，包括 ["UST", "ST", "MT", "SS"]
    dbconn : psycopg2.extensions.connection or None
        数据库连接对象，如果已建立连接
    dbcursor : psycopg2.extensions.cursor or None
        数据库游标对象，用于执行SQL查询
    logger : logging.Logger or None
        日志记录器实例
        
    Notes
    -----
    1. 数据加载优先级：数据库 > CSV文件 > 缓存
    2. 时间序列数据统一使用UTC时区
    3. 支持断点续传和增量更新
    
    Examples
    --------
    从CSV文件加载数据：
    
    >>> from src.datasets.dataLoader import CDataLoader
    >>> import logging
    >>> 
    >>> # 配置日志
    >>> logging.basicConfig(level=logging.INFO)
    >>> logger = logging.getLogger(__name__)
    >>> 
    >>> # 创建数据加载器
    >>> loader = CDataLoader(
    ...     meotoOriginalCsvPaths=["data/meteo/original"],
    ...     powerOriginalCsvPaths=["data/power/original"],
    ...     logger=logger
    ... )
    >>> 
    >>> # 加载数据
    >>> data = loader.load()
    
    从数据库加载数据：
    
    >>> loader = CDataLoader(
    ...     DataBaseURL="localhost",
    ...     DataBaseName="weather_db",
    ...     DataBasePort="5432",
    ...     DataBaseUser="user",
    ...     DataBasePassword="password"
    ... )
    >>> data = loader.load()
    
    Raises
    ------
    FileNotFoundError
        当数据文件不存在时抛出
    ValueError
        当参数无效或数据格式错误时抛出
    psycopg2.Error
        当数据库操作失败时抛出
    
    Returns
    -------
    dict
        加载的数据，格式为：
        {
            'station_id': {
                'timeliness': {
                    'data_source': {
                        'data_element': pd.DataFrame
                    }
                }
            }
        }
    """

    timelinessList = ["UST", "ST", "MT", "SS"]

    def __init__(self,
                 meotoCachePaths: list[str] = None,
                 meotoOriginalCsvPaths: list[str] = None,
                 meotoBusinessCsvPaths: list[str] = None,
                 powerOriginalCsvPaths: list[str] = None,
                 powerBusinessCsvPaths: list[str] = None,
                 logger: logging.Logger = None,
                 DataBase: psycopg2.extensions.connection = None, DataBaseURL: str = None, DataBaseName: str = None,
                 DataBasePort: str = None, DataBaseUser: str = None, DataBasePassword: str = None):

        self.meotoCachePaths = meotoCachePaths
        self.meotoOriginalCsvPaths = meotoOriginalCsvPaths
        self.meotoBusinessCsvPaths = meotoBusinessCsvPaths
        self.powerOriginalCsvPaths = powerOriginalCsvPaths
        self.powerBusinessCsvPaths = powerBusinessCsvPaths

        self.dbconn = None
        self.dbcursor = None
        if logger:
            self.logger = logger
            logger.info("数据配置加载成功")
        else:
            self.logger = None

        try:
            if DataBase and DataBaseURL and DataBaseName and DataBasePort and DataBaseUser and DataBasePassword:
                if logger:
                    logger.info("初始化数据库连接")
                self.dbconn = psycopg2.connect(
                    dbname=DataBaseName, user=DataBaseUser, password=DataBasePassword, host=DataBaseURL,
                    port=DataBasePort
                )
                self.dbcursor = self.dbconn.cursor()
                if logger:
                    logger.info("数据库连接初始化完成")
            else:
                if logger:
                    logger.info("数据库连接未初始化")
        except Exception as e:
            if logger:
                logger.error(f"数据库连接初始化失败: {e}")

    def DataFrame2Dict(self, dataFrame: pd.DataFrame, staId: str = None, dataSource: str = None, 
                     timestart: dt.datetime = None, logger: logging.Logger = None, 
                     ratio: float = 0.1, isTrain: bool = True, isPower: bool = False) -> Dict[str, pd.DataFrame]:
        """将DataFrame转换为按列名组织的字典，并进行时间序列重采样。
        
        将输入的DataFrame按列转换为字典，其中键为列名，值为重采样后的时间序列数据。
        支持15分钟间隔的重采样和插值处理，适用于气象和功率数据的预处理。

        Parameters
        ----------
        dataFrame : pd.DataFrame
            需要转换的DataFrame，必须包含时间索引和'departureTime'列
        staId : str, optional
            站点ID，用于日志记录和错误追踪
        dataSource : str, optional
            数据源标识，用于日志记录
        timestart : datetime, optional
            时间序列的起始时间，用于插值处理
        logger : logging.Logger, optional
            日志记录器实例
        ratio : float, default=0.1
            空值比例阈值，超过此阈值将跳过该列
        isTrain : bool, default=True
            是否为训练模式，影响插值策略
        isPower : bool, default=False
            是否为功率数据，影响插值方法

        Returns
        -------
        dict
            转换后的字典，格式为：{'column_name': pd.DataFrame}
            其中每个DataFrame包含重采样后的时间序列数据

        Raises
        ------
        ValueError
            当输入DataFrame不包含'departureTime'列时抛出
        
        Notes
        -----
        1. 时间序列数据会按15分钟频率进行重采样
        2. 对于训练数据，空值比例超过ratio的列将被跳过
        3. 功率数据使用线性插值，气象数据根据配置使用不同插值策略

        Examples
        --------
        >>> import pandas as pd
        >>> from datetime import datetime
        >>> 
        >>> # 创建测试数据
        >>> df = pd.DataFrame({
        ...     'value1': [1, 2, 3],
        ...     'value2': [4, 5, 6],
        ...     'departureTime': [pd.Timestamp('2023-01-01')] * 3
        ... }, index=pd.date_range('2023-01-01', periods=3, freq='5min'))
        >>> 
        >>> # 转换数据
        >>> result = loader.DataFrame2Dict(
        ...     df, 
        ...     staId='test_station',
        ...     dataSource='test_source',
        ...     isTrain=True
        ... )
        >>> 
        >>> # 查看结果
        >>> print(result.keys())  # 输出: dict_keys(['value1', 'value2'])
        >>> print(result['value1'].head())  # 查看重采样后的数据
        """
        try:
            dataColumn = dict()
            dataFrameGrouped = dataFrame.groupby('departureTime')

            for name, group in dataFrameGrouped:
                group.index = pd.to_datetime(group.index, utc=True)
                departureTime = group.iloc[0]['departureTime']
                for column in group.columns:
                    if column == 'departureTime':
                        continue
                    try:
                        new_index = pd.date_range(
                            start = group[column].index.min(),
                            end = group[column].index.max(),
                            freq = '15min'
                        )
                        groupColumn = group[column]
                        groupColumn = groupColumn[~groupColumn.index.duplicated(keep='last')]
                        if isPower:  # >> 功率预测数据插补
                            data = groupColumn.reindex(new_index).interpolate(method='linear')
                        else:  # >> 气象预测数据插补
                            null_ratio = groupColumn.isnull().sum().sum() / len(group[column])
                            if isTrain:  # 训练数据进行数据插补
                                if null_ratio > 0.5:
                                    continue
                                else:
                                    data = groupColumn.reindex(new_index).interpolate(method='linear')
                            else:  # 预测数据进行严格数据插补
                                data = self.DataFrameInterpolation(groupColumn, staId, dataSource, timestart, logger, ratio)
                        data = data.reindex(new_index).interpolate(method='linear')
                        data15min = data.T
                        data15min = pd.DataFrame(data15min).T
                        data15min.index = [departureTime]
                        data15min.columns = [i for i in range(len(data15min.columns))]

                        lastData = dataColumn.get(column, None)
                        if lastData is None:
                            dataColumn.update({column: data15min})
                        else:
                           dataColumnConcat = pd.concat([lastData, data15min], axis=0).sort_index(axis=1, ascending=True)
                           dataColumn.update({column: dataColumnConcat})

                    except Exception as e:
                        traceback.print_exc()
                        continue

        except Exception as e:
            traceback.print_exc()

        return dataColumn


    def DataFrame2Dict4OBS(self, dataFrame: pd.DataFrame) -> Dict[str, pd.Series]:
        """将观测数据的DataFrame转换为按列名组织的字典。
        
        专为观测数据设计的转换方法，将DataFrame按列转换为字典，
        保留原始时间序列数据，不进行重采样。
        
        与`DataFrame2Dict`方法的主要区别：
        - 不进行时间序列重采样
        - 保留原始时间分辨率
        - 返回的是pd.Series而不是pd.DataFrame

        Parameters
        ----------
        dataFrame : pd.DataFrame
            需要转换的观测数据DataFrame，索引应为时间戳
            
            - 每列代表一个观测变量
            - 索引应为pandas.DatetimeIndex

        Returns
        -------
        dict
            转换后的字典，格式为：{'column_name': pd.Series}
            - key: str, 列名
            - value: pd.Series, 时间序列数据，索引为时间戳

        Notes
        -----
        1. 此方法适用于需要保持原始时间分辨率的观测数据
        2. 不会对数据进行插值或重采样处理
        3. 如果输入DataFrame的索引不是时间戳，可能会导致意外结果

        Examples
        --------
        >>> import pandas as pd
        >>> from datetime import datetime
        >>> 
        >>> # 创建测试数据
        >>> df = pd.DataFrame({
        ...     'temp': [20.1, 20.3, 20.5],
        ...     'humidity': [45, 46, 47]
        ... }, index=pd.date_range('2023-01-01', periods=3, freq='5min'))
        >>> 
        >>> # 转换数据
        >>> result = loader.DataFrame2Dict4OBS(df)
        >>> 
        >>> # 查看结果
        >>> print(list(result.keys()))  # 输出: ['temp', 'humidity']
        >>> print(result['temp'].values)  # 输出: [20.1, 20.3, 20.5]
        >>> print(result['temp'].index)  # 显示时间索引
        
        输出::
        
            ['temp', 'humidity']
            [20.1 20.3 20.5]
            DatetimeIndex(['2023-01-01 00:00:00', '2023-01-01 00:05:00',
                         '2023-01-01 00:10:00'],
                        dtype='datetime64[ns]', freq=None)
        """
        try:
            dataColumn = dict()
            for column in dataFrame.columns:
                dataColumn.update({column: dataFrame[column]})
        except Exception as e:
            traceback.print_exc()
        return dataColumn


    def Dict2DataFrame(self, dataDict: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, Dict[pd.Timestamp, pd.DataFrame]]]]:
        """将多层嵌套的字典结构转换为包含时间序列DataFrame的结构化格式。

        此方法将输入的多层嵌套字典转换为标准化的数据结构，最内层数据会被转换为带有时间索引的
        DataFrame，并按照15分钟的频率进行重采样。

        Parameters
        ----------
        dataDict : Dict[str, Dict]
            输入的多层嵌套字典，要求结构为：
            {
                'station_id': {
                    'timeliness': {
                        'data_source': {
                            'data_element': pd.Series  # 数据元素，应为pandas Series类型
                        }
                    }
                }
            }
            
            - station_id: str
                站点标识符
            - timeliness: str
                时效性标识
            - data_source: str
                数据源标识
            - data_element: str
                数据元素名称
            - pd.Series:
                包含时间序列数据的pandas Series，其索引为时间戳

        Returns
        -------
        Dict[str, Dict[str, Dict[str, Dict[pd.Timestamp, pd.DataFrame]]]]
            转换后的结构化数据，格式为：
            {
                'station_id': {
                    'timeliness': {
                        'data_source': {
                            departure_time: pd.DataFrame  # 包含时间序列数据的DataFrame
                        }
                    }
                }
            }
            
            - departure_time: pd.Timestamp
                出发时间，作为DataFrame的键
            - pd.DataFrame:
                包含以下列的数据框：
                - 各数据元素列：从输入数据中提取的各个数据元素
                - departureTime: 出发时间
                - 索引：时间戳，以15分钟为间隔

        Notes
        -----
        1. 输出DataFrame将包含时间索引和departure_time列
        2. 时间索引将按15分钟间隔进行重采样
        3. 当前实现仅支持单个起报时间，这是一个已知限制

        Examples
        --------
        >>> data = {
        ...     'station1': {
        ...         'timeliness1': {
        ...             'source1': {
        ...                 'temp': pd.Series([20, 21, 22], 
        ...                             index=pd.date_range('2023-01-01', periods=3, freq='15min'))
        ...             }
        ...         }
        ...     }
        ... }
        >>> result = loader.Dict2DataFrame(data)
        >>> result['station1']['timeliness1']['source1']
        {
            Timestamp('2023-01-01 00:00:00'): 
                           temp  departureTime
                time                         
                2023-01-01 00:00:00  20.0 2023-01-01 00:00:00
                2023-01-01 00:15:00  21.0 2023-01-01 00:00:00
                2023-01-01 00:30:00  22.0 2023-01-01 00:00:00
        }
        """

        dataDictFrame = dict()
        for _staId, _value in dataDict.items():
            if _staId not in dataDictFrame:
                dataDictFrame.update({_staId: {}})
            for _timeliness, value2 in _value.items():
                if _timeliness not in dataDictFrame[_staId]:
                    dataDictFrame[_staId].update({_timeliness: {}})
                for _dataSet, value3 in value2.items():
                    if _dataSet not in dataDictFrame[_staId][_timeliness]:
                        dataDictFrame[_staId][_timeliness].update({_dataSet:{}})
                    dataFrame = pd.DataFrame()
                    for _dataElement, value4 in value3.items():
                        for _i, _v in value4.iterrows():
                            try:
                                departureTime = _v.name
                                dataFrame[_dataElement] = _v
                                dataFrame['departureTime'] = departureTime
                            except Exception as e:
                                traceback.print_exc()
                    dataFrame.index = pd.date_range(start=departureTime,
                                                    end=departureTime + pd.Timedelta(minutes=15 * len(_v) - 1),
                                                    freq='15min')
                    dataFrame.index.name = 'time'

                    # TODO: fix 目前仅能有一个起报时间，需要修复
                    dataDictFrame[_staId][_timeliness][_dataSet].update({departureTime: dataFrame})


        return dataDictFrame

    def OBSLoadPoint(self, staIds: Union[list, str], staTypes: Union[list, str], key: str, 
                    timestart: Union[pd.Timestamp, None], timestop: Union[pd.Timestamp, None],
                    logger: logging.Logger) -> Dict[str, Dict[str, pd.Series]]:
        """从数据库加载观测站点数据并转换为字典格式。

        该方法支持从数据库加载单个或多个站点的观测数据，并将结果转换为标准化的字典格式。
        数据会自动进行时区转换（从亚洲/上海时区转换为UTC）和时间索引排序。

        Parameters
        ----------
        staIds : Union[list, str]
            站点ID或站点ID列表。支持以下格式：
            - 单个站点ID: 'station1'
            - 多个站点ID: ['station1', 'station2']
        
        staTypes : Union[list, str]
            站点类型或站点类型列表，与staIds一一对应。支持的类型包括：
            - 'PV': 光伏电站
            - 'WD': 风电场
            
        key : str
            数据键名，用于标识数据用途（当前版本未直接使用，保留参数）
            
        timestart : pd.Timestamp, optional
            查询开始时间（UTC时区）。如果为None，则查询所有时间的数据
            
        timestop : pd.Timestamp, optional
            查询结束时间（UTC时区）。如果为None，则查询所有时间的数据
            
        logger : logging.Logger
            日志记录器实例，用于记录运行日志和错误信息

        Returns
        -------
        Dict[str, Dict[str, pd.Series]]
            嵌套字典结构，格式为：
            {
                'station1': {
                    'column1': pd.Series(...),  # 列数据，索引为时间戳（UTC）
                    'column2': pd.Series(...),
                    ...
                },
                'station2': {...},
                ...
            }

        Raises
        ------
        ValueError
            1. 当数据库连接未初始化时
            2. 当指定的站点类型不支持时
            3. 当查询结果为空时（找不到指定站点的数据）

        Notes
        -----
        1. 时间处理：
           - 输入时间参数应为UTC时区
           - 数据库查询时会自动转换为亚洲/上海时区
           - 返回数据的时间索引为UTC时区
           
        2. 数据转换：
           - 使用DataFrame2Dict4OBS方法将DataFrame转换为字典
           - 时间列重命名为'Datetime'并设置为索引
           - 按时间索引排序
           
        3. 日志记录：
           - 记录数据加载开始和完成信息
           - 记录错误和异常信息

        Examples
        --------
        >>> from datetime import datetime, timezone
        >>> import pandas as pd
        >>> import logging
        >>> 
        >>> # 初始化数据加载器
        >>> loader = CDataLoader()
        >>> 
        >>> # 设置时间范围（UTC时区）
        >>> start = pd.Timestamp('2023-01-01 00:00:00', tz='UTC')
        >>> end = pd.Timestamp('2023-01-02 00:00:00', tz='UTC')
        >>> 
        >>> # 加载单个站点数据
        >>> data = loader.OBSLoadPoint(
        ...     staIds='station1',
        ...     staTypes='PV',
        ...     key='solar_power',
        ...     timestart=start,
        ...     timestop=end,
        ...     logger=logging.getLogger()
        ... )
        >>> 
        >>> # 查看加载的数据
        >>> print(data['station1'].keys())  # 输出列名
        >>> print(data['station1']['power'])  # 查看功率数据
        """

        if not self.dbcursor:
            logger.error("数据库连接未初始化")
            raise ValueError("数据库连接未初始化")

        if isinstance(staIds, str):
            staIds = [staIds]
        if isinstance(staTypes, str):
            staTypes = [staTypes]

        obsData = dict()
        for i, staId in enumerate(staIds):
            logger.info(f"加载数据: {staId} {timestart} {timestop}")

            if staTypes[i] == "PV":
                dbName = "solar_power"
            elif staTypes[i] == "WD":
                dbName = "wind_power"
            else:
                logger.error(f"站点类型 {staTypes[i]} 不支持")
                raise ValueError(f"站点类型 {staTypes[i]} 不支持")

            if timestart and timestop:
                self.dbcursor.execute(
                    f"SELECT * FROM {dbName} WHERE station_id = '{staId}' AND time >= '{timestart.tz_convert('Asia/Shanghai').strftime('%Y-%m-%d %H:%M:%S')}' AND time <= '{timestop.tz_convert('Asia/Shanghai').strftime('%Y-%m-%d %H:%M:%S')}'")
            else:
                self.dbcursor.execute(
                    f"SELECT * FROM {dbName} WHERE station_id = '{staId}'")
            data = self.dbcursor.fetchall()
            if not data:
                logger.error(f"没有找到站点 {staId} 的数据")
                raise ValueError(f"没有找到站点 {staId} 的数据")

            columns = [desc[0] for desc in self.dbcursor.description]
            dataFrame = pd.DataFrame(data, columns=columns)
            dataFrame["time"] = pd.to_datetime(dataFrame["time"]).dt.tz_localize('Asia/Shanghai').dt.tz_convert('UTC')
            dataFrame.rename(columns={"time": "Datetime"}, inplace=True)
            dataFrame.set_index("Datetime", inplace=True)
            dataFrame.sort_index(inplace=True)
            # dataFrame.drop(columns=["sta_id"], inplace=True)

            dataColumn = self.DataFrame2Dict4OBS(dataFrame)
            obsData.update({staId: dataColumn})

        logger.info(f"数据加载完成: {staId} {timestart} {timestop}")

        return obsData

    def NWPLoadPoint(self, staId: str, staLat: float, staLon: float,
                    timelinessList: list[str], dataSources: list[str],
                    dataElements: Union[list[str], None], timestart: dt.datetime, timestop: dt.datetime, 
                    logger: logging.Logger, businessFlag: bool = False, originMeteoFileFlag: bool = False, 
                    isTrain: bool = True) -> Dict[str, Dict[str, Dict[str, Dict[str, pd.DataFrame]]]]:
        """从多个数据源加载数值天气预报(NWP)数据并进行预处理。
        
        该方法支持从多种数据源（数据库、缓存文件、业务文件等）加载气象数据，
        并进行必要的格式转换、时区标准化和特征工程处理。

        Parameters
        ----------
        staId : str
            站点唯一标识符
            
        staLat : float
            站点纬度（度）
            
        staLon : float
            站点经度（度）
            
        timelinessList : list[str]
            时效性列表，指定要加载的数据时效性
            
        dataSources : list[str]
            数据源列表，指定要加载的数据源
            
        dataElements : list[str], optional
            需要加载的数据元素列表，如果为None则加载所有可用元素
            
        timestart : datetime.datetime
            数据开始时间（UTC时区）
            
        timestop : datetime.datetime
            数据结束时间（UTC时区）
            
        logger : logging.Logger
            日志记录器实例
            
        businessFlag : bool, default=False
            是否加载业务数据，为True时尝试从业务文件加载
            
        originMeteoFileFlag : bool, default=False
            是否加载原始气象文件，为True时尝试从原始文件提取数据
            
        isTrain : bool, default=True
            是否为训练模式，影响数据处理方式

        Returns
        -------
        Dict[str, Dict[str, Dict[str, Dict[str, pd.DataFrame]]]]
            嵌套字典结构，包含加载和处理后的数据，格式为：
            {
                'station_id': {
                    'timeliness1': {
                        'data_source1': {
                            'data_element1': pd.DataFrame(...),
                            'data_element2': pd.DataFrame(...),
                            ...
                        },
                        'data_source2': {...},
                        ...
                    },
                    'timeliness2': {...},
                    ...
                },
                ...
            }

        Raises
        ------
        ValueError
            1. 当timeliness参数不在预定义列表中时
            2. 当所有数据源都加载失败时
            
        FileNotFoundError
            当指定的数据文件不存在时

        Notes
        -----
        1. 数据加载优先级：
           - 1. 气象数据库
           - 2. 气象缓存文件
           - 3. 气象业务提取文件
           - 4. 气象原始提取文件
           - 5. 原始气象文件（需要显式启用）
           
        2. 自动计算的特征：
           - 水平辐照度(GHI)、直接辐射(DNI)、散射辐射(DHI)
           - 平面辐照度(POA)
           - 100米高度风速和风向
           
        3. 时区处理：
           - 所有时间戳都转换为UTC时区
           - 确保时间序列按时间排序
           
        4. 数据质量控制：
           - 移除重复的时间戳
           - 确保辐照度非负
           - 处理缺失值

        Examples
        --------
        >>> from datetime import datetime, timezone
        >>> import pandas as pd
        >>> import logging
        >>> 
        >>> # 初始化数据加载器
        >>> loader = CDataLoader()
        >>> 
        >>> # 设置时间范围（UTC时区）
        >>> start = pd.Timestamp('2023-01-01 00:00:00', tz='UTC')
        >>> end = pd.Timestamp('2023-01-02 00:00:00', tz='UTC')
        >>> 
        >>> # 加载数值天气预报数据
        >>> nwp_data = loader.NWPLoadPoint(
        ...     staId='station1',
        ...     staLat=39.9,
        ...     staLon=116.4,
        ...     timelinessList=['00', '12'],
        ...     dataSources=['ECMWF', 'GFS'],
        ...     dataElements=['t2m', 'rh2m', 'tcc'],
        ...     timestart=start,
        ...     timestop=end,
        ...     logger=logging.getLogger(),
        ...     businessFlag=False,
        ...     originMeteoFileFlag=False,
        ...     isTrain=True
        ... )
        >>> 
        >>> # 访问加载的数据
        >>> print(nwp_data['station1']['00']['ECMWF'].keys())  # 查看可用的数据元素
        >>> print(nwp_data['station1']['00']['ECMWF']['ghi'])  # 查看水平辐照度数据
        """

        for timeliness in timelinessList:
            if not timeliness in self.timelinessList:
                raise ValueError(f"timeliness 参数错误: {timeliness}")

        NWPData = dict()
        # TODO 实现多个站点ID以列表形式导入，批量计算
        for timeliness in timelinessList:
            for dataSource in dataSources:
                dataFrame: pd.DataFrame = None
                # TODO 适配起报时间
                dateRange = pd.date_range(timestart, timestop, freq="24h")
                for date in dateRange:
                    fileFlag = False

                    # 1. 尝试加载气象数据库
                    if not fileFlag:
                        logger.info(f"尝试加载数据库")
                        dateStr = date.strftime("%Y-%m-%d %H:%M:%S")
                        db_table = f"weather_{dataSource.lower()}"
                        logger.info(f"SELECT * FROM {db_table} WHERE station_id = '{staId}' AND stime = '{dateStr}'")
                        self.dbcursor.execute(
                            f"SELECT * FROM {db_table} WHERE station_id = '{staId}' AND stime = '{dateStr}'")
                        data = self.dbcursor.fetchall()
                        logger.debug(data)
                        if data:
                            columns = [desc[0] for desc in self.dbcursor.description]
                            dataFrameDatabase = pd.DataFrame(data, columns=columns)
                            dataFrameDatabase["stime"] = pd.to_datetime(dataFrameDatabase["stime"], utc=True)
                            dataFrameDatabase["time"] = pd.to_datetime(dataFrameDatabase["time"], utc=True)
                            dataFrameDatabase.rename(columns={"stime": "departureTime"}, inplace=True)
                            dataFrameDatabase.rename(columns={"time": "forecastTime"}, inplace=True)
                            fileFlag = True

                            if dataFrame is not None:
                                dataFrame = pd.concat([dataFrame, dataFrameDatabase])
                            else:
                                dataFrame = dataFrameDatabase

                        else:
                            logger.warning(f"加载数据库数据失败")

                    # 2. 尝试加载气象缓存文件
                    # if not fileFlag:
                    #     logger.info(f"尝试加载气象缓存文件")
                    #     for meotoCachePath in self.meotoCachePaths:
                    #         cacheDate = date + pd.Timedelta(days=1)
                    #         filePath = meotoCachePath.format(staID=staId, timeliness=timeliness, year=cacheDate.year,
                    #                                          month=cacheDate.month, day=cacheDate.day, hour=cacheDate.hour,
                    #                                          dataSet=dataSource)
                    #         if not os.path.exists(filePath):
                    #             logger.warning(f"数据不存在: {filePath}")
                    #         if os.path.exists(filePath):
                    #             try:
                    #                 logger.info(f"加载数据: {cacheDate} {filePath}")
                    #                 data = pd.read_csv(filePath)
                    #                 data['departureTime'] = pd.to_datetime(data['departureTime'], utc=True)
                    #                 data['time'] = pd.to_datetime(data['time'], utc=True)
                    #                 data.rename(columns={"time": "forecastTime"}, inplace=True)
                    #                 fileFlag = True
                    #                 logger.info(f"数据加载成功: {cacheDate} {filePath}")
                    #                 if dataFrame is not None:
                    #                     dataFrame = pd.concat([dataFrame, data])
                    #                 else:
                    #                     dataFrame = data
                    #             except Exception as e:
                    #                 logger.warning(f"数据加载失败: {e}")
                    #         if fileFlag:
                    #             break

                    # 3. 尝试加载气象业务提取文件
                    if not fileFlag and businessFlag:
                        logger.info(f"尝试加载气象业务提取文件")
                        for meotoBusinessPath in self.meotoBusinessCsvPaths:
                            for meteoDataType in meteoSourceDataType:
                                filePath = meotoBusinessPath.format(staId=staId, timeliness=timeliness,
                                                                    date=date.strftime("%Y%m%d%H"),
                                                                    dataSet=dataSource, dataType=meteoDataType.name)
                                if not os.path.exists(filePath):
                                    logger.warning(f"数据不存在: {filePath}")
                                if os.path.exists(filePath):
                                    try:
                                        logger.info(f"加载数据: {date} {filePath}")
                                        data = pd.read_csv(filePath)
                                        fileFlag = True
                                        logger.info(f"数据加载成功: {date} {filePath}")
                                        data['departureTime'] = pd.to_datetime(data['departureTime'], utc=True)
                                        data['forecastTime'] = pd.to_datetime(data['forecastTime'], utc=True)
                                        if dataFrame is not None:
                                            dataFrame = pd.concat([dataFrame, data])
                                        else:
                                            dataFrame = data
                                    except Exception as e:
                                        logger.error(f"数据加载失败: {e}")
                                if fileFlag:
                                    break

                    # 4. 尝试加载气象原始提取文件
                    if not fileFlag:
                        logger.info(f"尝试加载气象原始提取文件")
                        for meotoOriginalPath in self.meotoOriginalCsvPaths:
                            for meteoDataType in meteoSourceDataType:
                                filePath = meotoOriginalPath.format(staId=staId,
                                                                    date=date.strftime("%Y%m%d%H"),
                                                                    dataSet=dataSource, dataType=meteoDataType.name)
                                if not os.path.exists(filePath):
                                    logger.warning(f"数据不存在: {filePath}")
                                if os.path.exists(filePath):
                                    try:
                                        logger.info(f"加载数据: {date} {filePath}")
                                        data = pd.read_csv(filePath)
                                        data['departureTime'] = pd.to_datetime(data['departureTime'], utc=True)
                                        data['forecastTime'] = pd.to_datetime(data['forecastTime'], utc=True)
                                        fileFlag = True
                                        logger.info(f"数据加载成功: {date} {filePath}")
                                        if dataFrame is not None:
                                            dataFrame = pd.concat([dataFrame, data])
                                        else:
                                            dataFrame = data
                                    except Exception as e:
                                        logger.error(f"数据加载失败: {e}")
                                if fileFlag:
                                    break

                    # 5. 尝试加载气象原始文件
                    # TODO: 加载气象原始文件
                    if not fileFlag and originMeteoFileFlag:
                        try:
                            dataType = "SURF"
                            departureHour = 12
                            logger.info(f"尝试提取气象原始文件")
                            tempRealPath = os.path.realpath(__file__)
                            yamlFilePath = os.path.join(os.path.dirname(tempRealPath),
                                                        "..",
                                                        "utils",
                                                        "GreenPulseIO",
                                                        "config",
                                                        "dataConfig",
                                                        "dataConfig.yaml")
                            dataConfig = readYamlDataConfig(yamlFilePath)
                            for idataSource in dataConfig[dataSource][dataType]:
                                basePath = idataSource["basePath"]
                                departureTime = date.replace(hour=departureHour).to_pydatetime()
                                timePath = idataSource["timePath"].format(date=departureTime)
                                taskInputPath = os.path.join(basePath, timePath)
                                outPath = os.path.dirname(os.path.dirname(self.meotoOriginalCsvPaths[0].format(staId=staId,
                                                                        date=date.strftime("%Y%m%d%H"),
                                                                        dataSet=dataSource, dataType=dataType)))
                                if pd.to_datetime(idataSource["timeStart"]) <= pd.to_datetime(departureTime,
                                                                                            utc=True) <= pd.to_datetime(
                                    idataSource["timeEnd"]):
                                    datasetModel = IO.dataSets.datasetGet(dataSource, logger=logger)
                                    datasetModel.dealDate(
                                        remote=False,
                                        dataClass=datasetModel,
                                        dataType=dataType,
                                        inputPath=taskInputPath,
                                        departureTime=date,
                                        idLatLon=[[staId, staLat, staLon]],
                                        varList=dataElements if dataElements is not None else idataSource["varList"],
                                        expandList=[None],
                                        hourRange=[0, 1104],  # 46 day
                                        outPath=outPath,
                                    )
                                    logger.info(f"再次尝试加载气象原始提取文件")
                                    for meotoOriginalPath in self.meotoOriginalCsvPaths:
                                        for meteoDataType in meteoSourceDataType:
                                            filePath = meotoOriginalPath.format(staId=staId, timeliness=timeliness,
                                                                                date=date.strftime("%Y%m%d%H"),
                                                                                dataSet=dataSource,
                                                                                dataType=meteoDataType.name)
                                            if not os.path.exists(filePath):
                                                logger.warning(f"数据不存在: {filePath}")
                                            if os.path.exists(filePath):
                                                try:
                                                    logger.info(f"加载数据: {date} {filePath}")
                                                    data = pd.read_csv(filePath)
                                                    fileFlag = True
                                                    logger.info(f"数据加载成功: {date} {filePath}")
                                                    if dataFrame is not None:
                                                        dataFrame = pd.concat([dataFrame, data])
                                                    else:
                                                        dataFrame = data
                                                except Exception as e:
                                                    logger.error(f"数据加载失败: {e}")
                                            if fileFlag:
                                                break
                        except Exception as e:
                            logger.error(f"数据加载失败: {e}")

                    if not fileFlag:
                        logger.critical(f"数据不存在: {staId} {timeliness} {dataSource}")

                try:
                    dataFrame.set_index("forecastTime", inplace=True)
                    dataFrame.sort_index(inplace=True)
                    if dataElements is not None:
                        # departureTime 为约定起报时间列名
                        dataElements.append("departureTime")
                        dataFrame = dataFrame[dataElements]
                    if 'ghi' not in dataFrame.columns:
                        model = GFS()
                        model.set_location(dataFrame.index.tz, staLat, staLon)
                        # TODO 此刻的云量转辐照度需要注意 tcc 数据范围，不同数据集的范围不一样，需要统一
                        pv = model.cloud_cover_to_irradiance(dataFrame["tcc"] * 100)
                        ghi = pv['ghi'].to_numpy()  # 转换为 numpy 数组
                        dhi = pv['dhi'].to_numpy()
                        dni = pv['dni'].to_numpy()
                        ghi = np.maximum(ghi, 0)  # 确保辐照度非负
                        dni = np.maximum(dni, 0)
                        dni = np.maximum(dni, 0)
                        dataFrame['ghi'] = ghi
                        dataFrame['dhi'] = dhi
                        dataFrame['dni'] = dni
                        wspd_100, wdir_100 = np.sqrt(dataFrame.loc[:, 'u100']**2 + dataFrame.loc[:, 'v100']**2), (90 - np.degrees(np.arctan2(dataFrame.loc[:, 'v100'], dataFrame.loc[:, 'u100']))) % 360
                        dataFrame.loc[:, 'win100_spd'] = wspd_100 #新增百米风
                        dataFrame.loc[:, 'win100_dir'] = wdir_100

                        poa = cal_poa(staLat, staLon, dataFrame.index, ghi, dni, dhi)
                        dataFrame['poa'] = poa

                    dataColumn = self.DataFrame2Dict(dataFrame, staId, dataSource, timestart, logger, ratio=0.1, isTrain=isTrain, isPower=False)
                    # TODO 优化
                    try:
                        dataColumn = pd.concat([NWPData[staId][timeliness][dataSource], dataColumn])
                    except Exception as e:
                        logger.error(f"数据合并失败: {e}")
                        dataColumn = dataColumn
                    NWPData.update({staId: {timeliness: {dataSource: dataColumn}}})
                except Exception as e:
                    logger.critical(f"数据提取失败: {e}")
                    traceback.print_exc()
                    continue

        if not NWPData:
            raise ValueError("所有数据提取失败")

        return NWPData


    def FCLoadPoint(self, staId: str, staType: str, timelinessList: list[str], timestart: dt.datetime,
                    timestop: dt.datetime, logger: logging.Logger, algoName: Union[str, None] = None, 
                    businessFlag: bool = False) -> Dict[str, Dict[str, Dict[str, Dict[str, pd.DataFrame]]]]:
        """从数据库或本地文件加载预测功率数据点。
        
        该方法支持从多种数据源（数据库、业务文件、本地缓存）加载预测功率数据,
        并进行必要的格式转换、时区标准化和数据质量控制。支持多种时效性（UST/ST/MT/SS）
        和业务场景的数据加载。
        
        Parameters
        ----------
        staId : str
            站点唯一标识符
            
        staType : str
            站点类型，支持的类型包括:
            - 'PV': 光伏电站
            - 'WD': 风电场
            
        timelinessList : List[str]
            时效性列表，支持的时效性:
            - 'UST': 超短期预测
            - 'ST': 短期预测
            - 'MT': 中期预测
            - 'SS': 次季节预测
            
        timestart : datetime.datetime
            数据开始时间（UTC时区）
            
        timestop : datetime.datetime
            数据结束时间（UTC时区）
            
        logger : logging.Logger
            日志记录器实例，用于记录处理过程中的信息、警告和错误
            
        algoName : str, optional
            算法名称，用于指定特定的预测算法。如果为None，则使用默认算法
            
        businessFlag : bool, default=False
            是否加载业务数据，为True时尝试从业务目录加载数据

        Returns
        -------
        Dict[str, Dict[str, Dict[str, Dict[str, pd.DataFrame]]]]
            嵌套字典结构，包含加载和处理后的预测功率数据，格式为:
            {
                'station_id': {
                    'timeliness1': {
                        'Forecast': {
                            'power': pd.DataFrame(...),  # 预测功率数据
                            'capacity': float,           # 装机容量
                            ...
                        }
                    },
                    'timeliness2': {...},
                    ...
                },
                ...
            }
            
            DataFrame 列说明:
            - time: 时间戳 (UTC时区)
            - value: 预测功率值
            - departureTime: 起报时间 (UTC时区)
            - capacity: 装机容量
            - ... 其他元数据

        Raises
        ------
        ValueError
            1. 当staType不在['PV', 'WD']中时
            2. 当timeliness不在['UST', 'ST', 'MT', 'SS']中时
            3. 当数据库连接未初始化时
            4. 当所有数据源都加载失败时
            
        FileNotFoundError
            当指定的数据文件不存在时

        Notes
        -----
        1. 数据加载优先级:
           - 1. 业务数据 (businessFlag=True)
           - 2. 数据库
           - 3. 本地缓存文件
           
        2. 时区处理:
           - 所有时间戳都转换为UTC时区
           - 内部处理时会在UTC和Asia/Shanghai时区之间自动转换
           - 返回数据的时间索引为UTC时区

        3. 数据质量控制:
           - 移除重复的时间戳
           - 确保功率值在合理范围内
           - 处理缺失值

        4. 性能考虑:
           - 大时间范围的数据会被分块加载以优化内存使用
           - 提供日志记录以帮助调试性能问题
        
        >>> # 加载预测功率数据
        >>> start_time = datetime(2023, 1, 1)
        >>> end_time = datetime(2023, 1, 2)
        >>> data = loader.FCLoadPoint(
        ...     staId="S001",
        ...     timelinessList=["ST", "MT"],
        ...     timestart=start_time,
        ...     timestop=end_time,
        ...     logger=logger
        ... )
        """
        for timeliness in timelinessList:
            if not timeliness in self.timelinessList:
                raise ValueError(f"timeliness 参数错误: {timeliness}")

        FCData = dict()
        # TODO 实现多个站点ID以列表形式导入，批量计算
        for timeliness in timelinessList:
                dataFrame: pd.DataFrame = None
                # TODO 适配起报时间
                dateRange = pd.date_range(timestart, timestop, freq="24h")
                for date in dateRange:
                    fileFlag = False

                    # 1. 尝试加载功率数据库
                    if not fileFlag:
                        logger.info(f"尝试加载数据库")
                        dateStr = date.strftime("%Y-%m-%d %H:%M:%S")

                        if staType == "PV":
                            db_table_type = f"solar"
                        elif staType == "WD":
                            db_table_type = f"wind"
                        else:
                            raise ValueError(f"staType 参数错误: {staType}")

                        if timeliness == "UST":
                            db_table = f"{db_table_type}_ushort_power"
                            dataType = "1" # 超短期查询短期
                        elif timeliness == "ST":
                            db_table = f"{db_table_type}_short_power"
                            dataType = "2" # 短期查询中期
                        elif timeliness == "MT":
                            db_table = f"{db_table_type}_short_power"
                            dataType = "3" # 中期查询次季节
                        elif timeliness == "SS":
                            raise NotImplementedError(f"db_table for timeliness[{timeliness}] not implemented!")

                        if algoName:
                            taskConfigAlgo = algoName
                        else:
                            self.dbcursor.execute(
                                f"SELECT algo_name FROM task_configs WHERE station_id = '{staId}' AND data_type = '{dataType}'")
                            taskConfigs = self.dbcursor.fetchall()
                            if not taskConfigs:
                                raise ValueError(f"task_configs for station_id[{staId}] and data_type[{dataType}] not found!")
                            taskConfigAlgo = taskConfigs[0][0]

                        logger.info(f"SELECT * FROM {db_table} WHERE station_id = '{staId}' AND algorithm = '{taskConfigAlgo}' AND filetime = '{dateStr}' AND stime = (SELECT MAX(stime) FROM {db_table} WHERE station_id = '{staId}' AND filetime = '{dateStr}')")
                        self.dbcursor.execute(
                            f"SELECT * FROM {db_table} WHERE station_id = '{staId}' AND algorithm = '{taskConfigAlgo}' AND filetime = '{dateStr}' AND stime = (SELECT MAX(stime) FROM {db_table} WHERE station_id = '{staId}' AND filetime = '{dateStr}')")
                        data = self.dbcursor.fetchall()
                        if data:
                            try:
                                columns = [desc[0] for desc in self.dbcursor.description]
                                dataFrameDatabase = pd.DataFrame(data, columns=columns)
                                dataFrameDatabase["stime"] = pd.to_datetime(dataFrameDatabase["stime"]).dt.tz_localize('UTC')
                                dataFrameDatabase["time"] = pd.to_datetime(dataFrameDatabase["time"]).dt.tz_localize('Asia/Shanghai').dt.tz_convert('UTC')
                                dataFrameDatabase["forecastTime"] = dataFrameDatabase["time"]
                                dataFrameDatabase["filetime"] = pd.to_datetime(dataFrameDatabase["filetime"]).dt.tz_localize('Asia/Shanghai').dt.tz_convert('UTC')
                                dataFrameDatabase.rename(columns={"stime": "departureTime"}, inplace=True)
                                fileFlag = True
                                if dataFrame is not None:
                                    dataFrame = pd.concat([dataFrame, dataFrameDatabase])
                                else:
                                    dataFrame = dataFrameDatabase
                            except Exception as e:
                                traceback.print_exc()
                                logger.error(f"{e}")
                        else:
                            logger.warning(f"加载数据库数据失败")

                    # 2. 尝试加载功率缓存文件
                    if not fileFlag:
                        logger.info(f"尝试加载功率缓存文件")
                        for powerCachePath in self.powerOriginalCsvPaths:
                            filePathDir = pathlib.Path(powerCachePath.format(staID=staId, timeliness=timeliness, year=date.year,
                                                             month=date.month, day=date.day, hour=date.hour, minute=date.minute, algorithm=algoName, version='last'))
                            if not filePathDir.exists():
                                logger.warning(f"功率数据路径不存在: {filePathDir}")
                                continue
                            else:
                                logger.info(f"加载功率数据: {date} {filePathDir}")
                                fileList = filePathDir.glob("*.csv")
                                for filePath in fileList:
                                    fileAlgorithm = filePath.stem.split('_')[0]
                                    fileVersion = filePath.stem.split('_')[1]
                                    try:
                                        data = pd.read_csv(filePath)
                                        # 'algorithm' 列名与数据库记录算法名称的字段需要保持一致
                                        data['algorithm'] = fileAlgorithm
                                        fileFlag = True
                                        logger.info(f"功率数据加载成功: {date} {filePath}")
                                        if dataFrame is not None:
                                            dataFrame = pd.concat([dataFrame, data])
                                        else:
                                            dataFrame = data
                                    except Exception as e:
                                        logger.warning(f"功率数据加载失败: {e}")
                                        continue
                            if fileFlag:
                                break

                    # 3. 尝试加载功率业务提取文件
                    if businessFlag:
                        logger.info(f"尝试加载功率业务提取文件")
                        if timeliness == "UST":
                            duration = 4
                        elif timeliness == "ST":
                            duration = 72
                        elif timeliness == "MT":
                            duration = 240
                        elif timeliness == "SS":
                            duration = 1080
                        else:
                            raise ValueError(f"timeliness <UNK>: {timeliness}")
                        for powerBusinessPath in self.powerBusinessCsvPaths:
                            print(powerBusinessPath)
                            dateE = date + pd.Timedelta(duration, unit='h')
                            filePath = pathlib.Path(powerBusinessPath.format(staID=staId, staType=staType, duration=duration,
                                                     year=date.year, month=date.month,
                                                     yearS=date.year, monthS=date.month, dayS=date.day,
                                                     hourS=date.hour, minuteS=date.minute, secondS=date.second,
                                                     yearE=dateE.year, monthE=dateE.month, dayE=dateE.day, hourE=dateE.hour, minuteE=dateE.minute, secondE=dateE.second,))
                            if filePath.exists():
                                logger.warning(f"功率数据不存在: {filePath}")
                                continue
                            else:
                                try:
                                    logger.info(f"加载功率数据: {date} {filePath}")
                                    data = pd.read_csv(filePath)
                                    data['algorithm'] = "Business"
                                    fileFlag = True
                                    logger.info(f"功率数据加载成功: {date} {filePath}")
                                    if dataFrame is not None:
                                        dataFrame = pd.concat([dataFrame, data])
                                    else:
                                        dataFrame = data
                                except Exception as e:
                                    logger.error(f"功率数据加载失败: {e}")
                                    continue
                            if fileFlag:
                                break


                    if not fileFlag:
                        logger.critical(f"数据不存在: {staId} {timeliness} {date}")

                try:
                    dataFrame.set_index("time", inplace=True)
                    dataFrame.sort_index(inplace=True)
                    dataFrame["departureTime"] = dataFrame['departureTime']
                    # TODO 优化
                    try:
                        dataColumn = pd.concat([FCData[staId][timeliness]["Forecast"], dataColumn])
                    except Exception as e:
                        dataColumn = dataFrame
                    dataColumn = self.DataFrame2Dict(dataColumn)
                    FCData.update({staId: {timeliness: {"Forecast": dataColumn}}})
                except Exception as e:
                    logger.critical(f"功率数据提取失败: {e}")
                    continue

        if not FCData:
            raise ValueError("所有功率数据提取失败")

        return FCData


    def DataFrameInterpolation(self, dataFrame: pd.DataFrame, staId: str, dataSource: str, timestart: dt.datetime,
                           logger: logging.Logger, ratio: float = 0.1, **kwargs) -> pd.DataFrame:
        """根据数据的空值比例，采用多级插补策略处理缺失值。
        
        本方法实现了基于数据缺失情况的多级插补策略，包括线性插值和历史数据插补。
        主要处理逻辑如下：
        1. 如果数据无缺失，直接返回原数据
        2. 如果空值比例小于等于阈值（默认10%），使用线性插值补全
        3. 如果空值比例大于阈值，尝试从数据库加载历史数据补全
        4. 如果数据库不可用，尝试从本地缓存加载历史数据
        5. 如果仍有缺失值，尝试使用前7天同时间点的平均值补全

        Parameters
        ----------
        dataFrame : pandas.DataFrame
            需要进行插补的DataFrame，必须包含时间索引和气象数据列。
            索引应为pandas.DatetimeIndex类型，且按时间升序排列。
        staId : str
            站点唯一标识符，用于从数据库或缓存中查询对应站点的历史数据。
            格式示例: 'S001', 'W1234'等。
        dataSource : str
            数据源标识符，指定从哪个数据表查询历史数据。
            示例: 'EC_C1D', 'GFS'等。
        timestart : datetime.datetime
            数据开始时间，用于计算历史数据查询的时间范围。
            应为带有时区信息的datetime对象。
        logger : logging.Logger
            日志记录器实例，用于记录插补过程中的关键信息和警告。
        ratio : float, optional
            空值比例阈值，默认为0.1（10%）。
            当空值比例小于等于此值时使用线性插值，否则使用历史数据插值。
        **kwargs : dict, optional
            其他可选参数，当前版本未使用，为未来扩展保留。

        Returns
        -------
        pandas.DataFrame
            插补处理后的DataFrame，与输入DataFrame具有相同的列和索引。
            所有缺失值（NaN）将尽可能被插补值替换。

        Raises
        ------
        ValueError
            当输入数据不满足要求时抛出，如：
            - dataFrame为空
            - dataFrame索引不是时间类型
            - 无法从任何数据源获取插补数据

        See Also
        --------
        pandas.DataFrame.interpolate : pandas内置插值方法
        NWPLoadPoint : 数值天气预报数据加载类

        Notes
        -----
        1. 函数会直接修改输入的DataFrame，建议在调用前使用.copy()创建副本。
        2. 历史数据查询最多尝试3天前的数据。
        3. 对于时间序列末尾的缺失值，会尝试使用前7天同时间点的平均值进行插补。
        4. 如果所有插补策略都失败，原始数据中的NaN值将保留。

        Examples
        --------
        >>> import pandas as pd
        >>> import numpy as np
        >>> from datetime import datetime, timezone
        >>> import logging
        >>> 
        >>> # 创建测试数据
        >>> idx = pd.date_range('2023-01-01 00:00', periods=24, freq='H')
        >>> data = {
        ...     'ghi': [100, 120, np.nan, 150, 180, np.nan, 200, 220,
        ...             240, np.nan, 280, 300, 320, 340, 360, 380,
        ...             400, 420, 440, 460, 480, 500, 520, 540],
        ...     'dhi': [50, 60, 70, np.nan, 90, 100, 110, 120,
        ...             130, 140, 150, 160, 170, 180, 190, 200,
        ...             210, 220, 230, 240, 250, 260, 270, 280]
        ... }
        >>> df = pd.DataFrame(data, index=idx)
        >>> 
        >>> # 初始化日志记录器
        >>> logger = logging.getLogger(__name__)
        >>> logger.setLevel(logging.INFO)
        >>> 
        >>> # 调用插值方法
        >>> interpolated_df = self.DataFrameInterpolation(
        ...     df, 'S001', 'EC_C1D', 
        ...     datetime(2023, 1, 1, tzinfo=timezone.utc),
        ...     logger,
        ...     ratio=0.1
        ... )
        >>> print(interpolated_df.isnull().sum())  # 检查是否还有缺失值
        """
        if dataFrame.isnull().sum().sum() == 0:
            logger.info(f"{staId}-{dataSource}-{dataFrame.name} 数据无缺失，无需插补")
            return dataFrame

        # >> 计算空值比例
        null_ratio = dataFrame.isnull().sum().sum() / len(dataFrame)

        # >> 空值比例小于等于 10%，使用线性插值，但是首尾的空值不处理
        if null_ratio <= ratio:
            logger.info(
                f"{staId}-{dataSource}-{dataFrame.name} 空值比例小于等于 {ratio * 100}%，使用线性插值{null_ratio}")
            dataFrame = dataFrame.interpolate()

        # >> 空值比例大于 10%，或者线性插值后仍然存在nan值，尝试从数据库加载前一天的数据
        max_query = 1
        while max_query <= 3 and dataFrame.isnull().sum().sum() > 0:
            yesterday = timestart - dt.timedelta(days=max_query)
            logger.info(f"{staId}-{dataSource}-{dataFrame.name} 尝试加载前 {max_query} 天的数据进行数据插补...")
            if dataFrame.isnull().sum().sum() > 0:
                logger.info(
                    f"空值比例大于 {ratio * 100}%，或者线性插值后仍然存在nan值，尝试从数据库加载前{max_query}天的数据")
                try:
                    self.dbcursor.execute(
                        f"SELECT * FROM weather_{dataSource.lower()} WHERE station_id = '{staId}' AND stime = '{yesterday.strftime('%Y-%m-%d %H:%M:%S')}'"
                    )
                    data = self.dbcursor.fetchall()
                    if data:
                        columns = [desc[0] for desc in self.dbcursor.description]
                        yesterday_data = pd.DataFrame(data, columns=columns)
                        yesterday_data["stime"] = pd.to_datetime(yesterday_data["stime"], utc=True)
                        yesterday_data["time"] = pd.to_datetime(yesterday_data["time"], utc=True)
                        yesterday_data.rename(columns={"stime": "departureTime"}, inplace=True)
                        yesterday_data.rename(columns={"time": "forecastTime"}, inplace=True)
                        yesterday_data.set_index("forecastTime", inplace=True)

                        # 使用前一天的数据补全
                        for col in [dataFrame.name]:
                            if col in yesterday_data.columns:
                                nan_mask = dataFrame.isna()
                                nan_times = dataFrame.index[nan_mask]
                                replacement = yesterday_data[col].reindex(nan_times)
                                dataFrame[nan_mask] = replacement
                    logger.info(f"数据库插补结束！")
                except Exception as e:
                    logger.error(f"数据库连接失败，尝试从本地缓存加载: {e}")

            # >> 如果仍然存在缺失数据，或者数据库失败，从本地缓存中加载前一天的数据
            if dataFrame.isnull().sum().sum() > 0:
                logger.info(f"数据库插补结束, 仍然存在空值, 尝试从本地缓存加载前{max_query}天的数据...")
                for meotoCachePath in self.meotoCachePaths:
                    cacheDate = yesterday
                    filePath = meotoCachePath.format(staID=staId, timeliness="UST", year=cacheDate.year,
                                                     month=cacheDate.month, day=cacheDate.day, hour=cacheDate.hour,
                                                     dataSet=dataSource)
                    if os.path.exists(filePath):
                        try:
                            logger.info(f"加载本地缓存数据: {filePath}")
                            yesterday_data = pd.read_csv(filePath)
                            yesterday_data['departureTime'] = pd.to_datetime(yesterday_data['departureTime'], utc=True)
                            yesterday_data['time'] = pd.to_datetime(yesterday_data['time'], utc=True)
                            yesterday_data.rename(columns={"time": "forecastTime"}, inplace=True)
                            yesterday_data.set_index("forecastTime", inplace=True)

                            # 将 yesterday_data 的时间索引调整为与 dataFrame 一致
                            yesterday_data = yesterday_data.reindex(dataFrame.index)

                            # 使用前一天的数据补全
                            for col in [dataFrame.name]:
                                if col in yesterday_data.columns:
                                    nan_mask = dataFrame.isna()
                                    nan_times = dataFrame.index[nan_mask]
                                    replacement = yesterday_data[col].reindex(nan_times)
                                    dataFrame[nan_mask] = replacement
                            logger.info("本地缓存数据插补结束！")
                        except Exception as e:
                            logger.warning(f"本地缓存数据加载失败: {e}")
                    else:
                        logger.warning(f"本地缓存数据不存在: {filePath}")
            max_query += 1

        if dataFrame.isnull().sum().sum() > 0:
            logger.warning(f"{staId}-{dataSource}-{dataFrame.name} 经过插补策略, 仍然存在空值, 尝试使用线性插值补全...")
            dataFrame = dataFrame.interpolate(method='linear', limit_direction='both')
        return dataFrame
