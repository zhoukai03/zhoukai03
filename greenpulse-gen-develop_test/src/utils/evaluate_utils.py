""" This module contains some helper functions about evaluate. """

import os, re
import pandas as pd
import importlib
from functools import partial


def dynamic_import_function(package, module_name, function_name, *args, **kwargs):
    """Dynamic import function from package and module.

    Args:
        package (str): package name.
        module_name (str): module name.
        function_name (str): function name.
        *args (tuple): args.
        **kwargs (dict): kwargs.

    Returns:
        function: function.
    
    """

    try:
        module = getattr(package, module_name, None)
        if module is None:
            full_module_path = f"{package}.{module_name}"
            module = importlib.import_module(full_module_path)
        function = getattr(module, function_name, None)
        if function is None:
            raise ValueError(f"Function {function_name} not found in module {module_name}")
        return partial(function, *args, **kwargs)
    except ModuleNotFoundError:
        raise ModuleNotFoundError(f"Module '{module_name}' does not exist in package '{package}'.")
    except AttributeError as e:
        raise e
    
def obtain_file_list_from_tmr(path, time_range, pattern, verbose=False):
    """Obtain a list of files from a given path and time range.

    Args:
        path (str): The path of the directory.
        time_range (list): The time range of the files.
        # pattern 必须是一个正则表达式，匹配所有文件名，并将时间戳提取出来，例如 r'(\d{8})_power.csv'
        pattern (str): The pattern of the files, it must be a regular expression that match all file name and extract the timestamp. e.g., r'(\d{8})_power.csv'

    Returns:
        list: A list of files.
    
    Example:
    >>> obtain_file_list_from_tmr('/home/user/data', ['2020-01-01', '2020-01-31'], r'data_(\d{2}-\d{2}-\d{2}).csv')
    ['/home/user/data/data_2020-01-01.csv', '/home/user/data/data_2020-01-02.csv', ...]
    """

    file_list = []
    for tm in time_range:
        sub_path = os.path.join(path, f"{tm.strftime('%Y%m')}")
        try:
            file = [f for f in os.listdir(sub_path) if re.match(pattern, f) and re.match(pattern, f).group(1) == tm.strftime('%Y%m%d')][0]
            file_list.append(os.path.join(sub_path, file))
        except Exception as e:
            if verbose:
                print(f"Error: {e}")
            else:
                pass
    return file_list

def obtain_dataframe_from_filelist(file_list, time_col='time', day=0, *args, **kwargs):
    """
    Obtain a list of dataframes from a list of files.

    Args:
        file_list (list): A list of files.
        time_col (str): The name of the column that contains the time.
        day (int): which day choose to evaluate, 0 for day-ahead.
        *args: Additional arguments to pass to pd.read_csv.
        **kwargs: Additional keyword arguments to pass to pd.read_csv.

    Returns:
        list: concate dataframe.

    Example:
        df_list = obtain_dataframe_from_filelist(file_list, time_col='time', day=0)
    """

    df_list = []
    for file in file_list:
        df_one = pd.read_csv(file, index_col=time_col, parse_dates=True)
        df_choose = df_one[df_one.index.date == df_one.index.date[0] + pd.Timedelta(days=day)]
        df_list.append(df_choose)
    df = pd.concat(df_list)
    return df