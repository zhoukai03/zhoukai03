import os
import xml.etree.ElementTree as ET


# 输入参数 str 需要判断的字符串
# 返回值   True：该字符串为浮点数；False：该字符串不是浮点数。
def IsFloatNum(s: str):
    try:
        float(s)
        return True
    except ValueError:
        return False


def IsBool(s: str):
    if s == "true" or s == "TRUE" or s == "True":
        return True
    elif s == "false" or s == "FALSE" or s == "False":
        return True
    else:
        return False


def str2bool(s: str):
    if s == "true" or s == "TRUE" or s == "True":
        return True
    elif s == "false" or s == "FALSE" or s == "False":
        return False


class BaseCfg:

    class params:

        def __init__(self, file: str, version: str = None):
            self.path = os.path.join(os.path.abspath(os.path.dirname(__file__)), file)
            self.root = ET.parse(self.path).getroot()
            if version is not None:
                self.set_version(version)

        def __getattr__(self, name: str):
            attr = self.root.findtext(name).strip()
            if attr.isdigit():
                attr = int(attr)
            elif IsFloatNum(attr):
                attr = float(attr)
            elif IsBool(attr):
                attr = str2bool(attr)
            return attr

        def set_version(self, version: str):
            self.root = self.root.find(version)
            return self

        def reset_root(self):
            self.root = ET.parse(self.path).getroot()


__params__ = ["LSTM", "regressor", "transformer", "tide", "Baseline"]


def __getattr__(name):
    if name in __params__:
        attr = BaseCfg.params("params_{}.xml".format(name))
        return attr
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def config(name, version: str = None):
    cfg = __getattr__(name)
    if name in __params__:
        if version is None:
            version = name
        cfg.set_version(version)
    return cfg
