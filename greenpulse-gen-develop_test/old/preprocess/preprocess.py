import datetime as dt
import os, sys
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
import traceback, glob
import logging

import config
import src.main as luncher
import src.modelset.helper as helper


def main(cfg_file, base_path, date=None):
    class_ids = helper.get_subdir(base_path)
    for class_id in class_ids:
        class_dir = os.path.join(base_path, class_id)
        area_ids = helper.get_subdir(class_dir)
        for area_id in area_ids:
            area_dir = os.path.join(class_dir, area_id)
            date_list = helper.get_subdir(area_dir)
            for date in date_list:
                date_dir = os.path.join(area_dir, date)
                in_dir = os.path.join(date_dir, "IN")
                sta_ids = helper.get_subdir(in_dir)
                for sta in sta_ids:
                    try:
                        if "similar_days" in args.methods:
                            import similar_days
                            save_dataset_path = (
                                cfg_file.find("preprocess")
                                .findtext("prep_similar_path")
                                .format(
                                    area_id=class_id,
                                    area_id=area_id,
                                    st=dt.datetime.strptime(date, "%Y-%m-%d"),
                                    sta_id=sta,
                                )
                            )
                            base_train_file = os.path.join(
                                cfg_file.find("input")
                                .findtext("base_input")
                                .format(
                                    area_id=class_id,
                                    area_id=area_id,
                                    st=dt.datetime.strptime(date, "%Y-%m-%d"),
                                    sta_id=sta,
                                ),
                                "0",
                                "DQYC_IN_FORECAST_WEATHER.txt",
                            )
                            base_train_file_H = os.path.join(
                                cfg_file.find("input")
                                .findtext("base_input")
                                .format(
                                    area_id=class_id,
                                    area_id=area_id,
                                    st=dt.datetime.strptime(date, "%Y-%m-%d"),
                                    sta_id=sta,
                                ),
                                "0",
                                "DQYC_IN_FORECAST_WEATHER_H.txt",
                            )
                            helper.check_dir(save_dataset_path)
                            similar_days.similar(
                                base_train_file, base_train_file_H, save_dataset_path
                            )
                    except:
                        logging.warning(traceback.format_exc())
                        # raise Exception
                        pass


if __name__ == "__main__":
    logger = luncher.set_logger()

    try:
        arg = luncher.Arg()
        args = arg.arg_parse()

        cfg_path_file = config.config(args.xml_path)

        main(
            cfg_path_file.root,
            cfg_path_file.root.find("input").findtext("base_path"),
            args.date,
        )

    except Exception as e:
        logger.exception(e)
        exit(1)
