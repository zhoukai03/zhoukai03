import importlib


__sta__ = ["longyuan", "SouthernPower_clean", "qihui"]
__nwp___ = ["nwp_ec_c1d", "nwp_ec_c3e","nwp_ufs", "nwp_pangu"]


__all__ = []
__all__.extend(__nwp___)
__all__.extend(__sta__)


def __getattr__(name):
    if name in __all__:
        if name in __nwp___:
            return importlib.import_module(".nwp." + name, __name__)
        elif  name in __sta__:
            return importlib.import_module(".sta." + name, __name__)
        else:
            raise NotImplementedError
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return __all__


def dataLoader(dataset_name: str, version = None, **kwargs):
    print("Get dataset: ", dataset_name)
    dataset_module = __getattr__(dataset_name)
    if version is None:
        version = dataset_name
    dataset_class = getattr(dataset_module, version)
    dataset_class_instance = dataset_class(**kwargs)
    return dataset_class_instance
