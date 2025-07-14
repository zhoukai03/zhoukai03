from enum import Enum, IntEnum, unique

@unique
class TaskType(IntEnum):
    """
    任务类型枚举
    """
    FC   = 1     # 预测任务
    HFC  = 2     # 算法回算
    FT   = 3     # 全新训练
    RFC  = 4     # 重新预测
    UPT  = 5     # 增量更新
    MPB  = 6     # 气象源选优
    PFC  = 7     # 后处理预测
    PT   = 8     # 后处理训练
    PHFC = 9     # 后处理历史预测

@unique
class AccRule(IntEnum):
    """
    考核细则对应表
    """
    huazhong  = 1 # 华中细则
    huabei    = 2 # 华北细则
    huadong   = 3 # 华东细则
    xibei2023 = 4 # 西北 2023 细则
    nanwang   = 5 # 南网细则
    nbtacc    = 6 # 电力行业细则
    shanxi    = 7 # 山西细则
    shandong  = 8 # 山东细则
    jiangsu   = 9 # 江苏细则


@unique
class TimeLiness(Enum):
    """
    时效类型枚举
    """
    UST = 1
    ST  = 2
    MT  = 3
    SS  = 4

class TimeLinessFcHour(IntEnum):
    """
    时效预测时长类型枚举
    """
    UST = 4
    ST  = 312
    MT  = 312
    SS  = 1080

@unique
class meteoSourceDataType(IntEnum):
    SURF = 1
    UPAR = 2
