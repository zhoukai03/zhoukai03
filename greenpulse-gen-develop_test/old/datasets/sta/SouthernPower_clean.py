import os, sys
import pandas as pd

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

class SouthernPower_clean:

    input_dir = "data/data_clean/output"
    input_col_time = ['Datetime']
    input_col_stat = ['lat','lon']
    input_col_feat = ['HubSpeed','HubDirection','cap','clean_pw','clean_ws','clean_interp_pw', 'clean_interp_ws']

    def __init__(self):
        self.data = dict()

    def get_sta(self, type, area, sta_id):
        sta_data = pd.read_csv(os.path.join(self.input_dir, type, area, 'clean_data', sta_id + '_clean.csv'))
        sta_data['PlantID'] = sta_data['PlantID'].ffill()
        try:
            sta_data['PlantID'] = sta_data['PlantID'].astype('int')
        except Exception as e:
            print(sta_id, " : ", e)
        return sta_data

    def get_area(self, type, area):
        area_data = dict()
        sta_files = os.listdir(os.path.join(self.input_dir, type, area, 'clean_data'))
        sta_files.sort()
        for sta in sta_files:
            sta_id = sta[0:4]
            sta_data = pd.read_csv(os.path.join(self.input_dir, type, area, 'clean_data', sta))
            sta_data['PlantID'] = sta_data['PlantID'].ffill()
            try:
                sta_data['PlantID'] = sta_data['PlantID'].astype('int')
            except Exception as e:
                print(sta_id, " : ", e)
            area_data.update({sta_id : sta_data})
        return area_data


    def get_all(self):
        type_paths = os.listdir(self.input_dir)
        type_paths.sort()
        for type in type_paths:
            type_data = dict()
            area_paths = os.listdir(os.path.join(self.input_dir, type))
            area_paths.sort()
            for area in area_paths:
                area_data = dict()
                sta_files = os.listdir(os.path.join(self.input_dir, type, area, 'clean_data'))
                sta_files.sort()
                for sta in sta_files:
                    sta_id = sta[0:4]
                    sta_data = pd.read_csv(os.path.join(self.input_dir, type, area, 'clean_data', sta))
                    sta_data['PlantID'] = sta_data['PlantID'].ffill()
                    try:
                        sta_data['PlantID'] = sta_data['PlantID'].astype('int')
                    except Exception as e:
                        print(sta_id, " : ", e)
                    area_data.update({sta_id : sta_data})
                type_data.update({area : area_data})
            self.data.update({type : type_data})

if __name__ == '__main__':
    # test
    test = SouthernPower_clean()
    print(test.data['73']['1001']['1578'].head())
    print(test.get_sta('73', '1001', '1578').head())
    print(test.get_area('73', '1001')['1578'].head())
