'''
author:        Yongpeng Zhang <zhangyp6603@outlook.com>
date:          2024-10-21 14:12:01
Copyright © cnpresky All rights reserved
'''

import os
from abc import ABC, abstractmethod
import pandas as pd

class Cbase(ABC):

    @abstractmethod
    def __init__(self, mode):
        self.root_data = ""
        self.input_dir = os.path.join(self.root_data, mode)

    def get_date_sta(self, date:pd.Timestamp, sta_id: str) -> dict:
        date_data = dict()
        data = dict()
        sta_data = pd.read_csv(os.path.join(self.input_dir, date.strftime("%Y%m%d%H"), sta_id + ".csv"))
        sta_data["id"] = sta_data["id"].ffill()
        try:
            sta_data["id"] = sta_data["id"].astype("int")
        except Exception as e:
            print(sta_id, " : ", e)
        date_data.update({sta_id: sta_data})
        data.update({date: date_data})

        return data

    # @abstractmethod
    # def get_date_area(self, date, area_id) -> dict:
    #    pass

    def get_sta(self, sta_id: str) -> dict:
        date_paths = os.listdir(self.input_dir)
        date_paths.sort()

        data = dict()
        for date in date_paths:
            date_data = dict()
            sta_files = os.listdir(os.path.join(self.input_dir, date))
            sta_files.sort()
            for sta in sta_files:
                sta_id = sta.split(".")[0]
                sta_data = pd.read_csv(os.path.join(self.input_dir, date, sta))
                sta_data["id"] = sta_data["id"].ffill()
                try:
                    sta_data["id"] = sta_data["id"].astype("int")
                except Exception as e:
                    print(sta_id, " : ", e)
                date_data.update({sta_id: sta_data})
            data.update({date: date_data})

        return data

    # @abstractmethod
    # def get_area(self, area_id) -> dict:
    #    pass

    # @abstractmethod
    # def get_all(self) -> dict:
    #    pass

    def json2df(self, json_data, sta_id):
        df = pd.DataFrame()
        for key, value in json_data.items():
            temp_df = pd.DataFrame(value[sta_id])
            df = pd.concat([df, temp_df], axis=0)

        return df