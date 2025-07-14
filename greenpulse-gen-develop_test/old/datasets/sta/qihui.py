import os, sys
import pandas as pd

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))


class qihui:

    def __init__(self) -> None:
        """
        初始化函数
        :param config: 配置信息, 通常包含路径和其它设置
        :return: None
        """
        self.input_dir = "data/OBS/QiHui"
        self.columns = "Datetime,radi,Power".split(",")
        self.input_features = "Datetime,radi".split(",")
        self.target_features = "Power"

    def get_data(self):
        """
        获取数据
        :return: pd.DataFrame
        """

        data = pd.read_csv(f"{self.input_dir}/qihui_obs.csv")
        data["Datetime"] = pd.to_datetime(data["Datetime"])

        return data


if __name__ == "__main__":
    
    data = qihui().get_data()
    print(data.head())
