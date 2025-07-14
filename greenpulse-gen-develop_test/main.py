"""
GreenPulse 功率预测系统主程序

模块: main.py
描述: 新能源功率预测系统的主入口模块，负责系统初始化、任务调度和资源管理。

主要功能:
    1. 系统初始化（参数解析、日志配置）
    2. 消息队列设置
    3. Ray 集群初始化（可选）
    4. 任务分发与执行
    5. 预测结果部署
    6. 资源清理与释放

组件依赖:
    - src.logger: 日志记录模块
    - src.params: 参数配置模块
    - src.task: 任务处理模块
    - src.repair: 数据修复模块
    - src.message: 消息队列模块
    - src.deploy: 部署模块

使用示例:
    python main.py --taskID TASK123 --config config.ini --logLevel INFO

注意事项:
    1. 确保配置文件中的路径和参数正确配置
    2. 使用 Ray 集群时确保网络连接正常
    3. 确保有足够的磁盘空间存储预测结果
    4. 定期清理日志文件以防止磁盘空间不足

"""

import ray
import traceback

import src.logger as lg
import src.params as pp
import src.task as task
import src.repair as repair
import src.message as message
from src.deploy import deploy


def main():
    logPath = "log"
    status = True
    try:
        params = pp.CParams()
        arg = pp.Arg()
        args = arg.arg_parse()
        logger = lg.setRootLogger(logPath, args.taskID)
        logger.info("新能源功率预测初始化")
        params.paramsParse(args, logger)
    except Exception as e:
        status = False
        logger.error("新能源功率预测初始化失败: %s." % e)
        logger.error(traceback.format_exc())
    logger.info("新能源功率预测初始化完成")

    try:
        if params.init.messageQueue and params.init.messageQueueURL:
            logger.debug("设置消息队列生产者: %s." % params.init.messageQueueURL)
            producer = message.Cproducer(messageQueueURL=params.init.messageQueueURL)
            producer.setTopic(params.init.messageQueueTopic)
            logger.info("设置消息队列生产者成功: %s." % params.init.messageQueueURL)
        else:
            producer = message.CNullKafkaProducer()
            logger.info("未设置消息队列生产者.")
    except Exception as e:
        status = False
        logger.error("新能源功率预测消息队列初始化失败: %s." % e)
        logger.error(traceback.format_exc())

    logger.info("初始化站点列表及参数")
    try:
        params.setStaParams(logger)
    except Exception as e:
        status = False
        logger.error("新能源功率预测初始化站点列表及参数失败: %s." % e)
        logger.error(traceback.format_exc())
    logger.info("站点列表及参数初始化完成")

    try:
        if params.init.ray:
            logger.info("设置 Ray 集群")
            logger.info("初始化调度器")
            ray.init(num_cpus=params.res.CPU, logging_level=params.init.logLevel)
            logger.info("调度器初始化完成")
            logger.info("Ray 集群设置完成")
    except Exception as e:
        status = False
        logger.error("新能源功率预测 Ray 集群设置失败: %s." % e)
        logger.error(traceback.format_exc())

    ##################################################################################
    ##################################  checkpoint  ##################################
    ##################################################################################
    if status:
        producer.send_checkpoint(params.task.taskID, 1, status = status)
    else:
        producer.send_checkpoint(params.task.taskID, 1, status = status)
        producer.send_checkpoint(params.task.taskID, 5, status = False)
        raise Exception("新能源功率预测初始化失败")

    logger.info("启动任务分配")
    try:
        checkpoint = task.taskDeal(params=params, logger=logger, messageQueueProducer=producer)
    except Exception as e:
        status = False
        logger.error("新能源功率预测任务失败: %s." % e)
        logger.error(traceback.format_exc())
    logger.info("任务分配完成")

    ##################################################################################
    ##################################  checkpoint  ##################################
    ##################################################################################
    if status:
        producer.send_checkpoint(params.task.taskID, 2, status = status)
    else:
        producer.send_checkpoint(params.task.taskID, 2, status = status)
        producer.send_checkpoint(params.task.taskID, 5, status=False)
        raise Exception("新能源功率预测任务失败")

    logger.info("新能源功率预测文件部署")
    try:
        deploy(params=params, checkpoint=checkpoint, logger=logger, messageQueueProducer=producer)
    except Exception as e:
        status = False
        logger.error("新能源功率预测文件部署失败: %s." % e)
        logger.error(traceback.format_exc())
    logger.info("新能源功率预测文件部署完成")

    ##################################################################################
    ##################################  checkpoint  ##################################
    ##################################################################################
    if status:
        producer.send_checkpoint(params.task.taskID, 3, status = status)
    else:
        producer.send_checkpoint(params.task.taskID, 3, status = status)
        producer.send_checkpoint(params.task.taskID, 5, status=False)
        raise Exception("新能源功率预测文件部署失败")

    try:
        pass
        #logger.info("新能源功率预测失败结果插补")
        ##### repair(params=params, logger=logger, messageQueueProducer=producer)
        #logger.info("新能源功率预测失败结果插补完成")
    except Exception as e:
        status = False
        logger.error("新能源功率预测失败结果插补失败: %s." % e)
        logger.error(traceback.format_exc())

    ##################################################################################
    ##################################  checkpoint  ##################################
    ##################################################################################
    if status:
        producer.send_checkpoint(params.task.taskID, 4, status = status)
    else:
        producer.send_checkpoint(params.task.taskID, 4, status = status)
        producer.send_checkpoint(params.task.taskID, 5, status=False)
        raise Exception("新能源功率预测失败结果插补失败")

    try:
        logger.info("清理资源")
        if params.init.ray:
            logger.info("Ray 集群关闭")
            ray.shutdown()
            logger.info("Ray 集群关闭完成")
        logger.info("清理数据库连接")
        params.clean()
        logger.info("数据库连接清理完成")

        ##################################################################################
        ##################################  checkpoint  ##################################
        ##################################################################################
        if status:
            producer.send_checkpoint(params.task.taskID, 5, status=status)
        else:
            producer.send_checkpoint(params.task.taskID, 5, status=status)
            raise Exception("新能源功率预测最终状态失败")

        logger.info("清理消息队列")
        producer.close()
        logger.info("消息队列清理完成")

        # 目前有一个问题：历史预测任务会被立刻清理，需要有一个逻辑判断
        logger.info("清理陈旧日志")
        lg.rmRootLogger(logPath, logger)
        lg.rmTaskLogger(params.path.outPath['root'], logger)
        logger.info("清理陈旧日志完成")
    except Exception as e:
        logger.error("新能源功率预测清理资源失败: %s." % e)
        logger.error(traceback.format_exc())

    logger.info("程序正常退出")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        raise e
