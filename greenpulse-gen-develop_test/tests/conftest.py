import os
import time
import pytest
import logging
from typing import List, Dict, Any, Generator, Optional

# 条件性地导入Docker和Kafka
KAFKA_DOCKER_AVAILABLE = False
try:
    import docker
    from kafka import KafkaProducer, KafkaConsumer
    KAFKA_DOCKER_AVAILABLE = True
except ImportError:
    # 记录导入错误但继续执行
    pass


# 配置日志
@pytest.fixture(scope="session")
def logger():
    """返回一个配置好的日志记录器"""
    logger = logging.getLogger("kafka_test")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


@pytest.fixture(scope="session")
def kafka_bootstrap_servers() -> List[str]:
    """获取Kafka服务器连接信息，优先使用环境变量"""
    return os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(",")


@pytest.fixture(scope="session")
def kafka_topic() -> str:
    """获取Kafka测试主题名称，优先使用环境变量"""
    return os.environ.get("KAFKA_TOPIC", "test-topic")


# 条件性的Docker Kafka容器
@pytest.fixture(scope="session")
def kafka_docker_container(logger) -> Optional[Generator]:
    """
    启动Kafka Docker容器用于测试

    只有在以下情况下才会启动:
    1. 标记为"with_kafka_docker"的测试
    2. docker和kafka库可用
    3. KAFKA_BOOTSTRAP_SERVERS环境变量未设置(表明没有外部Kafka可用)
    """
    if not KAFKA_DOCKER_AVAILABLE:
        logger.info("跳过Kafka Docker容器: docker或kafka库不可用")
        yield None
        return

    if "KAFKA_BOOTSTRAP_SERVERS" in os.environ:
        logger.info("跳过Kafka Docker容器: 使用环境变量中的Kafka服务器")
        yield None
        return

    # 启动Docker容器
    try:
        # 确认docker模块已导入
        if 'docker' not in globals():
            import docker
            
        client = docker.from_env()
        
        # 拉取镜像
        logger.info("拉取Kafka Docker镜像...")
        client.images.pull("bitnami/kafka:latest")
        
        # 启动Kafka容器
        logger.info("启动Kafka Docker容器...")
        container = client.containers.run(
            "bitnami/kafka:latest",
            detach=True,
            auto_remove=True,
            environment={
                "KAFKA_CFG_NODE_ID": "0",
                "KAFKA_CFG_PROCESS_ROLES": "controller,broker",
                "KAFKA_CFG_CONTROLLER_QUORUM_VOTERS": "0@localhost:9093",
                "KAFKA_CFG_LISTENERS": "PLAINTEXT://:9092,CONTROLLER://:9093",
                "KAFKA_CFG_ADVERTISED_LISTENERS": "PLAINTEXT://localhost:9092",
                "KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP": "CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT",
                "KAFKA_CFG_CONTROLLER_LISTENER_NAMES": "CONTROLLER",
                "ALLOW_PLAINTEXT_LISTENER": "yes",
                "KAFKA_KRAFT_CLUSTER_ID": "MkU3OEVBNTcwNTJENDM2Qk"
            },
            ports={
                "9092/tcp": 9092,
            },
        )

        # 等待Kafka启动
        logger.info("等待Kafka容器启动...")
        time.sleep(10)  # 给Kafka足够的启动时间

        # 设置环境变量供测试使用
        os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"

        logger.info(f"Kafka容器已启动: {container.name}, ID: {container.id}")

        # 返回容器引用
        yield container

        # 测试结束后清理
        logger.info(f"停止Kafka容器: {container.name}")
        container.stop()
        logger.info("Kafka容器已停止")

    except Exception as e:
        logger.error(f"启动Kafka Docker容器时出错: {str(e)}")
        yield None


# 用于测试的Kafka主题创建
@pytest.fixture(scope="session")
def ensure_kafka_topic(kafka_bootstrap_servers, kafka_topic, logger, kafka_docker_container):
    """确保测试主题存在"""
    if not KAFKA_DOCKER_AVAILABLE:
        logger.info(f"跳过Kafka主题创建: kafka库不可用")
        return

    try:
        try:
            from kafka.admin import KafkaAdminClient, NewTopic
        except ImportError:
            logger.warning("KafkaAdminClient 不可用，无法创建主题")
            return
                
        # 等待kafka可用
        retry_count = 0
        admin_client = None
        while retry_count < 5:
            try:
                # 尝试创建管理客户端
                admin_client = KafkaAdminClient(
                    bootstrap_servers=kafka_bootstrap_servers,
                    client_id='test-admin'
                )
                break
            except Exception as e:
                logger.warning(f"尝试连接Kafka失败 (尝试 {retry_count+1}/5): {str(e)}")
                retry_count += 1
                time.sleep(5)
            
        # 如果无法创建客户端，直接返回
        if admin_client is None:
            logger.warning("无法创建Kafka管理客户端，跳过主题创建")
            return
                    
        # 检查主题是否已存在
        existing_topics = admin_client.list_topics()
        if kafka_topic in existing_topics:
            logger.info(f"Kafka主题 '{kafka_topic}' 已存在")
        else:
            # 创建主题
            topic_list = [
                NewTopic(
                    name=kafka_topic,
                    num_partitions=1,
                    replication_factor=1
                )
            ]
            admin_client.create_topics(new_topics=topic_list, validate_only=False)
            logger.info(f"已创建Kafka主题 '{kafka_topic}'")
                
        admin_client.close()
    except Exception as e:
        logger.error(f"确保Kafka主题存在时出错: {str(e)}")
