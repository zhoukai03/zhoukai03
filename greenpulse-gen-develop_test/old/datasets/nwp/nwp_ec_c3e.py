import os
import sys
import pandas as pd

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from nwp_base import Cbase


class nwp_ec_c3e(Cbase):

    def __init__(self, mode="SURF"):
        self.mode = mode
        self.root_data = "data/EC_C3E"
        self.input_dir = os.path.join(self.root_data, self.mode)
        if self.mode == "SURF":
            self.input_col_time = ["forecastTime", "departureTime"]
            self.input_col_feat = ["tcc", "u100", "v100", "u10", "v10", "win10_spd", "win10_dir", "rhu", "skt", "t2", "d2"]
            self.input_col_stat = ["lat", "lon"]
        elif self.mode == "GV":
            self.input_col_time = ["forecastTime", "departureTime"]
            self.input_col_feat = ["tcc", "rhu", "t2", "d2"]
            self.input_col_stat = ["lat", "lon"]
        else:
            raise ValueError("mode should be 'SURF' or 'GV'.")


if __name__ == "__main__":
    test = nwp_ec_c1d()
    print("--------get_date_sta--------")
    temp = test.get_date_sta("2024060312", "qihui")
    print(temp.keys())
    print(temp["2024060312"].keys())
    print(temp["2024060312"]["qihui"].keys())
    print(temp["2024060312"]["qihui"].head())

    print("--------get_sta--------")
    temp = test.get_sta("qihui")
    print(temp.keys())
    print(temp["2024060312"].keys())
    print(temp["2024060312"]["qihui"].keys())
    print(temp["2024060312"]["qihui"].head())
    print("----------------")

    print("--------json 2 pandas--------")
    temp = test.get_sta("qihui")
    temp = test.json2df(temp, "qihui")
    print(temp)
