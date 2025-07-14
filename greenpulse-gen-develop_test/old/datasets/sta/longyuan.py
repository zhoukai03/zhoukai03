import os, sys
import datetime as dt
import pandas as pd

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
import src.modelset.helper as helper


class DataSet:

    def __init__(self, config, date) -> None:
        """
        初始化函数
        :param config: 配置信息, 通常包含路径和其它设置
        :return: None
        """
        self.cfg = config
        self.input_dir, self.train_dir, self.model_dir, self.modify_ds = self.get_path()
        self.columns = "时间,短期预测功率,超短期预测功率,实际功率,短期预测风速,超短期预测风速,实际风速,测风塔风速,短期预测风向,短期预测温度,开机容量,短期预测气压,短期预测湿度".split(
            ","
        )
        self.input_features = "时间,实际功率,实际风速,测风塔风速".split(
            ","
        )
        self.date = date
        self.target_features = "实际功率"
        self.data = self.get_data()

    def get_path(self):
        """
        从配置文件中读取各数据路径
        :return: 返回一个包含原始数据路径、训练数据路径、模型路径、预处理的预报数据路径和单站预报结果路径的元组
        """
        self.root = self.cfg.root
        # 从配置文件中获取各路径
        input_dir = self.root.find("input").find("base_path").text  # 原始数据
        modify_ds = self.root.find("input").find("base_prep").text  # 预处理的预报数据
        train_dir = self.root.find("output").find("base_train").text  # 训练数据
        model_dir = self.root.find("output").find("base_model").text  # 模型输出路径

        return input_dir, train_dir, model_dir, modify_ds

    def get_data(self, date) -> pd.DataFrame:
        """
        获取数据。
            :param da_type: 数据类型, 可以是"train"、"val"或"test"。
            :return: 返回一个DataFrame对象, 包含场站数据。
        """
        file_name = self.train_dir.format(date)
        print("开始获取数据: {}".format(file_name))
        data = pd.read_csv(file_name)

        return data

    @staticmethod
    def get_data_list(base_path):
        """
        生成数据列表。

        参数:
        base_path: 基础路径, 函数将从这个路径开始搜索数据结构。

        返回值:
        data_list: 包含数据详细路径的列表, 每个元素都是一个列表, 包含类ID、区域ID和站ID。
        """
        data_list = []
        # 获取基础路径下的所有子目录（类ID）
        class_ids = helper.get_subdir(base_path)
        for class_id in class_ids:
            # 拼接类目录路径并获取类目录下的所有子目录（区域ID）
            class_dir = os.path.join(base_path, class_id)
            area_ids = helper.get_subdir(class_dir)
            for area_id in area_ids:
                # 拼接区域目录路径并获取区域目录下的所有文件（站ID）
                area_dir = os.path.join(class_dir, area_id)
                sta_ids = helper.get_subfile(area_dir)
                # 从文件名中提取站ID，并确保格式一致
                sta_ids = [x[4:8] for x in sta_ids]
                for sta_id in sta_ids:
                    # 将类ID、区域ID和站ID组合成一个列表，并添加到数据列表中
                    data_list.append([class_id, area_id, sta_id])
        return data_list
