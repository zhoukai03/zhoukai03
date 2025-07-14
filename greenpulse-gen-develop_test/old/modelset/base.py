"""
该模块定义模型基类

模型基类定义了一个通用的模型接口，任何具体的模型都可以继承该基类并实现其中的抽象方法，
以便在不同的应用场景中进行模型训练、预测、保存和加载操作。
"""

from abc import ABC, abstractmethod

class BaseModel(ABC):
    """
    模型基类的使用方法:
    1. 继承模型基类，并实现其中的抽象方法。
    2. 使用子类对象进行模型的初始化、训练、预测、保存和加载操作。

    注意事项:
    1. 所有的子类必须实现基类中定义的所有抽象方法，否则会抛出异常。
    2. 在子类中可以根据具体需求添加额外的方法和属性。
    3. 在使用模型时，务必确保传入的数据格式和参数与模型的要求一致。
    """

    @abstractmethod
    def __init__(self, params, **kwargs):
        """
        - 参数：
          - `params`: 模型初始化所需的参数。
          - `**kwargs`: 其他可选参数。
        - 功能：初始化模型。
        """

    @abstractmethod
    def train(self, train_data, val_data, **kwargs):
        """
        - 参数：
          - `train_data`: 用于模型训练的训练数据。
          - `val_data`: 用于模型训练的验证数据。
          - `**kwargs`: 其他可选参数。
        - 功能：对模型进行训练。
        """

    @abstractmethod
    def predict(self, data, **kwargs):
        """
        - 参数：
          - `data`: 待预测的数据。
          - `**kwargs`: 其他可选参数。
        - 功能：对输入数据进行预测。
        """

    @abstractmethod
    def dump(self, file_path, **kwargs):
        """
        - 参数：
          - `file_path`: 保存模型的文件路径。
          - `**kwargs`: 其他可选参数。
        - 功能：将模型保存到指定文件路径。
        """

    @abstractmethod
    def load(self, file_path, **kwargs):
        """
        - 参数：
          - `file_path`: 加载模型的文件路径。
          - `**kwargs`: 其他可选参数。
        - 功能：从指定文件路径加载模型。
        """
