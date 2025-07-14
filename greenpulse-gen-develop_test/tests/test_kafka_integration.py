import os
import time
import pytest
import json
import logging
import datetime as dt
import pandas as pd
from unittest.mock import MagicMock, patch
from typing import Union, List, Dict, Any

try:
    from kafka import KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

from src.message import Cproducer, CNullKafkaProducer, check_timeliness, FileType


# 标记为集成测试，需要实际的Kafka环境才能运行
# 使用pytest.mark.skipif来跳过如果kafka库不可用的情况
@pytest.mark.skipif(not KAFKA_AVAILABLE, reason="Kafka library not available")
@pytest.mark.integration
class TestKafkaIntegration:
    """
    Kafka集成测试

    这些测试需要一个正在运行的Kafka实例。
    在CI/CD环境中，可以使用Docker容器提供临时Kafka服务。
    """

    KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(",")
    KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "test-topic")

    @pytest.fixture(scope="class")
    def logger(self):
        """返回一个配置好的日志记录器"""
        logger = logging.getLogger("kafka_integration_test")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    @pytest.fixture(scope="class")
    def kafka_producer(self):
        """创建并返回Kafka生产者"""
        producer = Cproducer(self.KAFKA_BOOTSTRAP_SERVERS)
        producer.setTopic(self.KAFKA_TOPIC)
        yield producer
        producer.close()

    @pytest.fixture(scope="class")
    def kafka_consumer(self):
        """创建并返回Kafka消费者"""
        # 确保KafkaConsumer已导入
        if KAFKA_AVAILABLE:
            from kafka import KafkaConsumer
            consumer = KafkaConsumer(
                self.KAFKA_TOPIC,
                bootstrap_servers=self.KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id='test-group',
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            yield consumer
            consumer.close()
        else:
            yield None

    def test_send_and_receive_simple_message(self, kafka_producer, kafka_consumer, logger):
        """测试发送和接收简单消息"""
        # 生成唯一的消息ID以便于识别
        message_id = f"test-message-{int(time.time())}"
        test_message = {
            "id": message_id,
            "content": "This is a test message"
        }

        # 发送消息
        logger.info(f"发送消息: {test_message}")
        kafka_producer.send(test_message)

        # 接收消息 (设置超时以防测试挂起)
        received = False
        max_attempts = 10
        for _ in range(max_attempts):
            for msg in kafka_consumer:
                if 'id' in msg.value and msg.value['id'] == message_id:
                    logger.info(f"接收到消息: {msg.value}")
                    assert msg.value['content'] == "This is a test message"
                    received = True
                    break

            if received:
                break

            time.sleep(1)

        assert received, f"未在{max_attempts}秒内接收到消息"

    def test_send_and_receive_checkpoint_message(self, kafka_producer, kafka_consumer, logger):
        """测试发送和接收检查点消息"""
        # 生成唯一的任务ID
        task_id = f"task-{int(time.time())}"
        checkpoint = 42

        # 发送检查点消息
        logger.info(f"发送检查点消息: taskId={task_id}, checkpoint={checkpoint}")
        kafka_producer.send_checkpoint(task_id, checkpoint)

        # 接收消息
        received = False
        max_attempts = 10
        for _ in range(max_attempts):
            for msg in kafka_consumer:
                if 'taskid' in msg.value and msg.value['taskid'] == task_id:
                    logger.info(f"接收到检查点消息: {msg.value}")
                    assert msg.value['checkpoint'] == checkpoint
                    assert 'status' in msg.value
                    received = True
                    break

            if received:
                break

            time.sleep(1)

        assert received, f"未在{max_attempts}秒内接收到检查点消息"

    def test_send_and_receive_log_message(self, kafka_producer, kafka_consumer, logger):
        """测试发送和接收日志文件消息"""
        # 生成唯一的任务ID
        task_id = f"task-{int(time.time())}"
        timeliness = "ST"
        file_path = "test_log.txt"

        # 发送日志文件消息
        logger.info(f"发送日志文件消息: taskId={task_id}, timeliness={timeliness}, filePath={file_path}")
        kafka_producer.send_log(task_id, timeliness, file_path)

        # 接收消息
        received = False
        max_attempts = 10
        for _ in range(max_attempts):
            for msg in kafka_consumer:
                if 'taskid' in msg.value and msg.value['taskid'] == task_id and msg.value['checkpoint'] == 90:
                    logger.info(f"接收到日志文件消息: {msg.value}")
                    assert msg.value['file']['filePath'] == file_path
                    received = True
                    break

            if received:
                break

            time.sleep(1)

        assert received, f"未在{max_attempts}秒内接收到日志文件消息"

    def test_send_and_receive_power_message(self, kafka_producer, kafka_consumer, logger):
        """测试发送和接收功率预测文件消息"""
        # 生成唯一的任务ID
        task_id = f"task-{int(time.time())}"
        timeliness = "ST"
        file_path = "test_power.csv"
        stime = dt.datetime(2023, 1, 1, 12, 0, 0)

        # 发送功率预测文件消息
        logger.info(f"发送功率预测文件消息: taskId={task_id}, timeliness={timeliness}, filePath={file_path}")
        kafka_producer.send_power(task_id, timeliness, file_path, stime)

        # 接收消息
        received = False
        max_attempts = 10
        for _ in range(max_attempts):
            for msg in kafka_consumer:
                if 'taskid' in msg.value and msg.value['taskid'] == task_id and msg.value['checkpoint'] == 91:
                    logger.info(f"接收到功率预测文件消息: {msg.value}")
                    assert msg.value['file']['filePath'] == file_path
                    assert msg.value['stime'] == "2023-01-01 12:00:00"
                    received = True
                    break

            if received:
                break

            time.sleep(1)

        assert received, f"未在{max_attempts}秒内接收到功率预测文件消息"

    def test_multiple_messages(self, kafka_producer, kafka_consumer, logger):
        """测试发送和接收多个不同类型的消息"""
        # 生成唯一的任务ID前缀
        task_id_prefix = f"multi-{int(time.time())}"
        messages_to_send = 3

        # 发送多条消息
        for i in range(messages_to_send):
            task_id = f"{task_id_prefix}-{i}"
            logger.info(f"发送检查点消息 {i+1}/{messages_to_send}: taskId={task_id}")
            kafka_producer.send_checkpoint(task_id, i)

        # 给Kafka一些时间来处理消息
        time.sleep(2)

        # 接收消息
        received_count = 0
        received_tasks = set()
        max_attempts = 15

        for _ in range(max_attempts):
            for msg in kafka_consumer:
                if 'taskid' in msg.value and msg.value['taskid'].startswith(task_id_prefix):
                    task_id = msg.value['taskid']
                    if task_id not in received_tasks:
                        logger.info(f"接收到消息: {msg.value}")
                        received_tasks.add(task_id)
                        received_count += 1

                    if received_count >= messages_to_send:
                        break

            if received_count >= messages_to_send:
                break

            time.sleep(1)

        assert received_count == messages_to_send, f"预期接收{messages_to_send}条消息，实际接收到{received_count}条"


@pytest.mark.skipif(not KAFKA_AVAILABLE, reason="Kafka library not available")
class TestCProducerWithMockedKafka:
    """使用模拟的Kafka测试Cproducer类"""

    @pytest.fixture
    def mock_kafka_producer(self):
        """提供一个模拟的KafkaProducer"""
        with patch('src.message.KafkaProducer') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def cproducer(self, mock_kafka_producer):
        """创建一个带有模拟KafkaProducer的Cproducer实例"""
        producer = Cproducer(["localhost:9092"])
        producer.setTopic("test-topic")
        return producer

    def test_message_serialization(self, cproducer, mock_kafka_producer):
        """测试消息序列化"""
        test_message = {"key": "value", "nested": {"data": 123}}
        cproducer.send(test_message)

        # 验证send被调用且值已正确传递
        mock_kafka_producer.send.assert_called_once()
        args, kwargs = mock_kafka_producer.send.call_args
        assert kwargs["topic"] == "test-topic"
        assert kwargs["value"] == test_message

    def test_error_handling(self, cproducer, mock_kafka_producer):
        """测试错误处理"""
        # 模拟KafkaProducer.send引发异常
        mock_kafka_producer.send.side_effect = Exception("Connection error")

        # 应该捕获异常并正常继续
        with pytest.raises(Exception):
            cproducer.send({"key": "value"})

    def test_custom_serialization(self):
        """测试自定义序列化"""
        with patch('src.message.KafkaProducer') as mock_kafka_producer_class:
            # 获取KafkaProducer初始化调用时的value_serializer参数
            Cproducer(["localhost:9092"])
            args, kwargs = mock_kafka_producer_class.call_args

            # 提取value_serializer函数并测试
            value_serializer = kwargs.get('value_serializer')
            assert callable(value_serializer)

            # 测试序列化函数
            test_data = {"test": "data"}
            serialized = value_serializer(test_data)
            assert isinstance(serialized, bytes)
            assert json.loads(serialized.decode('utf-8')) == test_data


# 一个简单的测试，验证CNullKafkaProducer不发送任何实际消息
def test_null_producer_does_not_send_messages():
    """验证CNullKafkaProducer不发送任何实际消息"""
    null_producer = CNullKafkaProducer()
    null_producer.setTopic("any-topic")

    # 这些操作应该都不会引发异常
    null_producer.send({"key": "value"})
    null_producer.send_checkpoint("task123", 1)
    null_producer.send_log("task123", "ST", "file.txt")
    null_producer.close()


if __name__ == "__main__":
    pytest.main(["-v", "test_kafka_integration.py"])
