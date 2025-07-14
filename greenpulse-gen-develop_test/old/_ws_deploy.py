import os
import pandas as pd
from . import params as pp
import logging
from . import message as mq
from .datasets import dataDump as dataDump


import os, warnings
import os.path as osp
warnings.filterwarnings("ignore")
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from types import SimpleNamespace
from datetime import datetime

# >> custom modules
from . import accuracy as sr
from .utils.evaluate_utils import dynamic_import_function, obtain_file_list_from_tmr, obtain_dataframe_from_filelist


def deploy(params: pp.CParams, logger: logging.Logger, messageQueueProducer: mq.Cproducer):
    logger.info("部署开始")
    
    if params.task.dateRange[0] and params.task.dateRange[1]:
        taskDateList = pd.date_range(start=params.task.dateRange[0], end=params.task.dateRange[1], freq="D", tz="UTC")
    elif params.task.date:
        taskDateList = [params.task.date]
    else:
        raise ValueError("日期参数传输错误")

    for staTaskId, staParam in params.staParams.items():
        logger.info(f"部署站点: {staParam.staId}")
        for timeliness in staParam.timeLiness:
            for algorithm, versions in staParam.algorithm.items():
                for version in versions:
                    for taskDate in taskDateList:
                        taskDate = pd.to_datetime(taskDate)
                        logger.info(f"部署站点: {staParam.staId} 时效: {timeliness} 算法: {algorithm} 版本: {version} 日期: {taskDate}")
                        outputPaths = params.path.setOutputPath(staParam.staId, staParam.dataset, timeliness, taskDate, algorithm, version)
                        fileFlag = False
                        for outputPath in outputPaths['power']:
                            try:
                                data = pd.read_csv(outputPath)
                                fileFlag = True
                            except Exception as e:
                                logger.warning(f"读取文件失败: {outputPath}")
                                logger.warning(e)
                                continue

                        if not fileFlag:
                            raise FileNotFoundError(f"部署文件不存在")
                        
                        taskDateStart = pd.to_datetime(data.iloc[0]['time']).replace(hour=0, minute=0, second=0, microsecond=0) + pd.Timedelta(days=1)
                        if timeliness == "UST":
                            taskDateEnd = taskDateStart + pd.Timedelta(hours=4) - pd.Timedelta(minutes=15)
                        elif timeliness == "ST":
                            taskDateEnd = taskDateStart + pd.Timedelta(hours=72) - pd.Timedelta(minutes=15)
                        elif timeliness == "LT":
                            taskDateEnd = taskDateStart + pd.Timedelta(hours=240) - pd.Timedelta(minutes=15)
                        elif timeliness == "SS":
                            taskDateEnd = taskDateStart + pd.Timedelta(hours=1080) - pd.Timedelta(minutes=15)
                        else:
                            raise ValueError(f"时效: {timeliness} 不支持")
                        deployPaths = params.path.setDeploymentPath(staParam.staId, staParam.staType, taskDateStart, taskDateEnd)
                        for deployPath in deployPaths['power']:
                            try:
                                # 将时间转换为 UTC 时间
                                data['time'] = pd.to_datetime(data['time'])
                                data['time'] = data['time'].dt.tz_convert(None)
                                dataDump.powerDump(staParam.staId, data, deployPath, timeliness, taskDate, logger, messageQueueProducer)
                            except Exception as e:
                                logger.warning(f"部署文件发生意外: {deployPath} {e}")
                                continue
    logger.info("部署结束")


class Evaluator:
    """ The main class for evaluating the model. """

    def __init__(self, params, logger, messageQueueProducer):
        """ Initialize the evaluator. 
        
        Args:
            params (dict): The options for the evaluator.
            logger (logging.Logger): The logger for the evaluator.
            messageQueueProducer (message.Cproducer): The message queue producer for the evaluator.
            pred_dict (dict): The dictionary to save the predict results and record, easy to return the optimal result path late.
            data (pd.DataFrame): The data contains label and model pred, which are ready to evaluate.
            acc_func (dict): The chosen scoring rules functions, which are used to evaluate the model.
            evaluate_df (pd.DataFrame): The dataframe to save the evaluation results.
            best_model (str): The path of the best model saved.
            acc_dict (dict): The dictionary to save the accuracy results.
        """
        self.opt = SimpleNamespace(**params)
        self.logger = logger
        self.messageQueueProducer = messageQueueProducer

        self.pred_dict = {}
        self.data = None
        self.acc_func = {}
        self.evaluate_df = None
        self.acc_dict = None
        self._load_and_merge_data()
        self._obtain_acc_function()

        # >> 如果保存中间结果，则创建文件夹
        if self.opt.save:
            self.opt.outpath = os.path.join(self.opt.outpath, f"{self.opt.end_date.strftime("%Y%m%d")}", f"{self.opt.farm}")

        self.logger.info(f"模型选优模块，评估模块初始化完成，开始评估...")
    def __call__(self):
        return fr"power prediction evluation, farm cap: %s, label path: %s, compare path: %s" % (self.opt.cap, self.opt.label_path, self.opt.pred_path_list)
    
    __repr__ = __call__

    def _load_and_merge_data(self):
        """ Load and merge the data. """
        # create evaluate time range
        if self.opt.start_date is None:
            tmr = pd.date_range(end=self.opt.end_date, periods=self.opt.days, freq='D')
        else:
            tmr = pd.date_range(self.opt.start_date, self.opt.end_date, freq='D')

        # create predict time range
        if self.opt.day_num == 0:
            pred_tmr = tmr
        else:
            pred_tmr = tmr - pd.Timedelta(days=self.opt.day_num)
        
        # load the data
        label_file_list = obtain_file_list_from_tmr(self.opt.label_path, tmr, self.opt.label_pattern)
        label_data = obtain_dataframe_from_filelist(label_file_list, self.opt.label_time_col)
        label_data = label_data[[self.opt.label_power_col]]
        for i, pred_path in enumerate(self.opt.pred_path_list):
            pred_data_one = {}
            
            if self.opt.product == 'short':
                pred_file_list = obtain_file_list_from_tmr(pred_path, pred_tmr, self.opt.online_pattern)
                pred_data = obtain_dataframe_from_filelist(pred_file_list, self.opt.pred_time_col, self.opt.day_num)
            elif self.opt.product == 'supershort':
                # >> 超短期预报数据读取
                pass
            else:
                raise ValueError("product type error!")
            pred_data_one[pred_path] = pred_data[[self.opt.pred_power_col]]
            self.pred_dict[f"{i+1}"] = pred_data_one

        # merge the data
        for key, inner_dict in self.pred_dict.items():
            for _, pred_data in inner_dict.items():
                if self.data is None:
                    self.data = label_data
                self.data = self.data.join(pred_data, how='inner', rsuffix=f'_{key}')
        
        # save the data
        if self.opt.save:
            self.data.to_csv(osp.join(self.opt.outpath, 'data.csv'), index=True)
    
    def _obtain_acc_function(self):
        """ Obtain the accuracy function dict. """
        for acc_name in self.opt.acc_pick:
            self.acc_func[acc_name] = dynamic_import_function('accuracy', acc_name, f'{acc_name}_{self.opt.product}_acc')

    def _calculate_and_sort(self):
        """ Log the print and save the result. """
        # return the optimeized predict data path

        # if pick more than one accuracy function, group the result and mean, otherwise, just mean
        if len(self.opt.acc_pick) == 1:
            mean_acc_score = self.evaluate_df.mean()
        else:
            mean_acc_score = self.evaluate_df.mean().groupby(lambda x: x.split('-')[1]).sum()
        
        if self.opt.standard.lower() == 'max':
            mean_acc_score = mean_acc_score.sort_values(ascending=False)
        elif self.opt.standard.lower() == 'min':
            mean_acc_score = mean_acc_score.sort_values(ascending=True)

        key_by_acc = mean_acc_score.index[0].split('-')[-1]
        pre_path = list(self.pred_dict[key_by_acc].keys())[0]
        self.best_model = pre_path

        # >> 将评估结果转换为字典格式，方便后续使用
        self.acc_dict = self.dict_format_convert(mean_acc_score.to_dict(), self.opt.pred_path_list)
        
        if self.opt.verbose:
            self.logger.info(f"==============mean acc===========")
            self.logger.info(f"mean acc: {mean_acc_score}")
            self.logger.info(f"==============best model===========")
            self.logger.info(f"best model: {key_by_acc}")
            self.logger.info(f"==============best model===========")
            self.logger.info(f"best model path: {pre_path}")

    def _map_plot(self):
        """ Plot the map. """
        # plt.rcParams['font.sans-serif'] = ['Time News Roman']  
        plt.rcParams['axes.unicode_minus'] = False  
        ax = self.data.plot(kind='line', figsize=(int(len(self.data)/96)*2, 5), xlabel='Time', ylabel='Power', fontsize=15)
        ax.set_xlabel('Time', fontsize=16)  
        ax.set_ylabel('Power', fontsize=16) 
        ax.legend(fontsize=16) 
        plt.savefig(os.path.join(self.opt.output, 'map.png'), bbox_inches='tight')
        plt.close()

        # for single day
        # for tm in self.time: 
        #     data_one = self.data[self.data.index.date == tm]
        #     ax = data_one.plot(kind='line', figsize=(10, 5), xlabel='Time', ylabel='Power', fontsize=12)
        #     ax.set_xlabel('Time', fontsize=16)  
        #     ax.set_ylabel('Power', fontsize=16)  
        #     ax.legend(fontsize=16) 
        #     plt.savefig(os.path.join(self.opt.outpath, f'map-{tm}.png'), bbox_inches='tight')
        #     plt.clf()
        # plt.close() 


    def evaluate(self):
        """ Evaluate the model. """
        cols = [col + '-' + f"{key}" 
                for col,_ in self.acc_func.items() 
                for key, _ in self.pred_dict.items()]
        self.evaluate_df = pd.DataFrame(columns=['time'] + cols)
        res_list = []

        self.time = np.unique(self.data.index.date)
        for tm in self.time:
            row_dict = {'time': tm}
            for acc_name, acc_func in self.acc_func.items():
                for key, _ in self.pred_dict.items():
                    pred_col = f"{self.opt.pred_power_col}_{key}"
                    da = self.data[self.data.index.date == tm]
                    da.reset_index(inplace=True)
                    row_dict[f'{acc_name}-{key}'] = acc_func(da, label_column=self.opt.label_power_col, pred_column=pred_col, cap=self.opt.cap, r=0.20 if self.opt.mode == 'solar' else 0.25)
            res_list.append(row_dict)
        self.evaluate_df = pd.DataFrame(res_list, columns=['time'] + cols)
        self.evaluate_df.set_index('time', inplace=True)

        if self.opt.save:
            self.evaluate_df.to_csv(osp.join(self.opt.outpath, 'eval.csv'), index=True)

        # print and save log, plot map
        self._calculate_and_sort()
        if self.opt.map_plot:
            self._map_plot()
        
        return self.acc_dict
    
    def dict_format_convert(self, old_dict, new_keys):
        new_dict = {}
        for old_key, value in old_dict.items():
            index = int(old_key.split('-')[-1]) - 1  
            
            # 检查索引是否有效
            if 0 <= index < len(new_keys):
                new_key = new_keys[index]
                new_dict[new_key] = value
            else:
                self.logger.warning(f"警告：索引 {index + 1} 超出列表范围，键 {old_key} 未处理")
        return new_dict


if __name__ == '__main__':
    params = {
        'verbose': True,   # 日志记录  
        'save': False,     # 是否保存结果，包括数据、评分、绘图
        'outpath': './',   # 如果保存评估生产结果，则保存到该路径下
        'map_plot': False, # 是否绘制地图
        'farm': '6325210200000000', # 电站编码
        'mode': 'solar',   # solar or wind, 会影响评估细则的参数
        'product': 'short',# 评估方式，short or supershort
        'cap': 1000.,      # 电站容量
        'acc_pick': ['xibei2023'], # 评估指标列表
        'day_num': 0,              # 评估日前
        'start_date': None,        # 评估起始日期
        'end_date': datetime.now().strftime('%Y%m%d'), # 评估结束日期
        'days': 7,                 # 评估天数
        'hours': 1,                # 超短期预报时效 

        'label_path': '/mnt/PRESKY/project/bgdb/photo_electric/qrcode/data/4',  # 标签数据路径
        'pred_path_list': ["/mnt/PRESKY/project/FGGLYC/power_prediction_data/6325210200000000/FCST/F_PV_FARM_WHOLE",
                           "/mnt/PRESKY/project/FGGLYC/power_prediction_code/6325210200000000/Version0.3/test/F_PV_FARM_WHOLE"], # 预测数据路径列表
        'label_time_col': 'time',  # 标签时间列
        'label_power_col': 'power',# 标签功率列 
        'pred_time_col': 'time',   # 预测时间列
        'pred_power_col': 'power', # 预测功率列
        'label_pattern': r'(\d{8})_power.csv',                                # 标签文件名正则表达式, re.group(1)是日期
        'online_pattern': r'F_PV_FARM_WHOLE_240H_(\d{8})\d{4}_\d{12}.csv',    # 预测文件名正则表达式，re.group(1)是日期
        'standard': 'max', # max or min，是按照最大值还是最小值来评估，eg. 西北2023，越小越好， 南网acc，越大越好.

    }

    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    evaluator = Evaluator(params, logger, messageQueueProducer=None)
    print(evaluator.evaluate())
