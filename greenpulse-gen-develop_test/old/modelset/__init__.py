import importlib

__all__ = ["regressor", "LSTM", "transformer", "tide", "Baseline"]


def __getattr__(name):
    if name in __all__:
        return importlib.import_module("." + name, __name__)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return __all__


def modelget(model_name: str, version: str = None, **kwargs):
    print("Get model: ", model_name)
    model_module = __getattr__(model_name)
    if version is None:
        version = model_name
    print("Get version: ", version)
    model_class = getattr(model_module, version)
    print("Init model: [{}] with version: [{}]".format(model_name, version))
    model = model_class(**kwargs)

    return model
