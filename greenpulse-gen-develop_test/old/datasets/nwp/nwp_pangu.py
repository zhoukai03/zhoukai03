import os
import sys
import pandas as pd

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from nwp_base import Cbase

class nwp_pangu(Cbase):

    def __init__(self, mode="SURF"):
        """
        mode: 'SURF'
        """
        self.mode = mode
        self.root_data = "data/PanGu"
        self.input_dir = os.path.join(self.root_data, self.mode)
        if self.mode == "SURF":
            self.input_col_time = ["forecastTime", "departureTime"]
            self.input_col_feat = ["u10", "v10", "pre_1h", "t2", "msl"]
            self.input_col_stat = ["lat", "lon"]
        else:
            raise ValueError("mode should be 'SURF'")


if __name__ == '__main__':
    # test
    test = nwp_pangu()
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
