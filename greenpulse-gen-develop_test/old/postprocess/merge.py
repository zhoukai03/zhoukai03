'''
author:        Yongpeng Zhang <zhangyp6603@outlook.com>
date:          2024-11-18 14:55:49
Copyright © cnpresky All rights reserved
'''

import os
import sys
import logging, traceback
import pandas as pd
import argparse

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import src.main as luncher


def merge_main(model, outpath, method, model_class, sta_id: str, dataset: str, version: str):

    try:
        config = readDataConfig()
    except Exception as e:
        logging.error(f"{e} {traceback.format_exc()}")
        exit(1)

    try:
        Cdata = config[dataset][model_class]
        train_df_dir = os.path.join(input_path, sta_id, dataset)
        train_df = pd.read_csv(os.path.join(train_df_dir, f"{version}.csv"))

        train_feat = train_df[Cdata["input_col_feat"]]

        from sklearn.preprocessing import MinMaxScaler

        scaler = MinMaxScaler()

        train_feat[Cdata["input_col_feat"]] = scaler.fit_transform(train_feat[Cdata["input_col_feat"]].to_numpy())

        model.load(f"{model_path}/{sta_id}/{method}/{dataset}/{version}.pth")
        target = model.predict(train_feat)

        out_df = pd.DataFrame({"Datetime": train_df[Cdata["input_col_time"]], "power": target})

        target_outpath = os.path.join(outpath, sta_id, model.__class__.__name__)
        helper.check_dir(target_outpath)
        out_df.to_csv(os.path.join(target_outpath, str(version) + ".csv"), index=False)
    except Exception as e:
        logging.error(f"{e} {traceback.format_exc()}")


def main(outpath, methods, model_classes, sta_ids: str, datesets: str, versions: str):
    """
    主函数，根据传入的配置文件和参数进行模型训练
    :param cfg_file: 配置文件对象
    :param args: 命令行参数对象
    """
    logger.info("start train: ")

    for method in methods:
        for dateset in datesets:
            for model_class in model_classes:
                for sta_id in sta_ids:
                    for version in versions:
                        logger.info(f"start train: {method}")
                        params = config.config(method)
                        model = modelset.modelget(method, params)
                        train_main(model, outpath, method, model_class, sta_id, dateset, version)


class Arg(argparse.ArgumentParser):

    def __init__(self, description=""):
        super().__init__(description=description)
        self.add_argument("-ds", "--datesets", default=["nwp_ec_c1d"], help="指定数据集, 默认值为 nwp_ec_c1d", nargs="*")
        self.add_argument("-id", "--sta_ids", default=["1000"], help="指定站点 id, 默认值为 1000")
        self.add_argument("-v", "--versions", default=["nwp_ec_c1d"], help="指定数据集版本, 默认值为 v1")
        self.add_argument("-c", "--model_class", default=["GV"], help="指定类别, 默认值为 GV")
        self.add_argument("-m", "--methods", default=["regressor"], help="指定方法, 默认值为 regressor")
        self.add_argument("-o", "--outpath", default="output/result", help="指定输出路径, 默认值为 output/result")

    def arg_parse(self, args_list=None):
        args = self.parse_args(args_list)
        return args


if __name__ == "__main__":
    logger = luncher.set_logger()
    try:
        arg = Arg()
        args = arg.parse_args()

        main(args.outpath, args.methods, args.model_class, args.sta_ids, args.datesets, args.versions)

    except Exception as e:
        logger.exception(e)
        exit(1)
