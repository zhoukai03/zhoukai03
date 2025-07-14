"""精度评估模块。

该模块提供了风光功率预测的精度评估功能，支持多种评估标准和地区规范。
模块采用插件式架构，可以方便地扩展新的评估算法和规范。

主要功能
--------
- 提供统一的评估接口，支持不同时间尺度的预测评估
- 支持多种地区性评估规范
- 支持自定义评估指标和权重
- 提供评估结果的可视化和报告生成

支持的评估规范
-------------
- `xibei2019`: 西北地区2019版评估规范
- `xibei2023`: 西北地区2023版评估规范
- `huazhong`: 华中地区评估规范
- `huadong`: 华东地区评估规范
- `huabei`: 华北地区评估规范
- `nanwang`: 南网评估规范

使用示例
-------
```python
# 导入评估模块
from accuracy import huazhong  # 导入华中地区评估规范

# 执行评估
result = huazhong.ust_day(
    pred={
        pd.Timestamp("2023-01-01"): pd.Series([1, 2, 3]),
        pd.Timestamp("2023-01-02"): pd.Series([4, 5, 6]),
    },
    obs=pd.Series([1, 2, 3, 4, 5, 6]),
    logger=logging.getLogger(__name__),
)

# 打印评估结果
print(result)
```

模块结构
-------
- `base.py`: 定义基础评估类和接口
- `xibei2019.py`: 西北地区2019版评估实现
- `xibei2023.py`: 西北地区2023版评估实现
- `huazhong.py`: 华中地区评估实现
- `huadong.py`: 华东地区评估实现
- `huabei.py`: 华北地区评估实现
- `nanwang.py`: 南网评估实现

注意事项
-------
- 输入数据应包含时间序列的功率数据
- 预测数据和实测数据的时间分辨率应一致
- 评估结果包含多种指标，具体指标因评估规范而异
- 建议使用绝对路径指定数据文件位置
"""

import importlib
from typing import Any


def __getattr__(algorithm: str) -> Any:
    """动态导入评估模块。
    
    允许通过属性访问方式动态导入评估模块。
    
    Parameters
    ----------
    algorithm : str
        评估算法或规范名称，如 'huazhong'、'xibei2019' 等。
        
    Returns
    -------
    module
        导入的评估模块。
        
    Raises
    ------
    AttributeError
        当指定的评估算法不存在时引发。
        
    Examples
    --------
    >>> from accuracy import huazhong  # 动态导入华中地区评估模块
    >>> result = huazhong.ust_day(...)
    """
    try:
        return importlib.import_module("." + algorithm, __name__)
    except ModuleNotFoundError as e:
        raise AttributeError(
            f"module {__name__!r} has no attribute {algorithm!r}. "
            f"Available modules: ['xibei2019', 'xibei2023', 'huazhong', 'huadong', 'huabei', 'nanwang', 'nbtacc']"
        ) from e
