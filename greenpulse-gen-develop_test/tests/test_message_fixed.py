import unittest
import pytest
import json
import datetime as dt
import pandas as pd
from unittest.mock import MagicMock, patch
from typing import Union, Any

from src.message import Cproducer, CNullKafkaProducer, check_timeliness, FileType


class TestCheckTimeliness:
    """测试 check_timeliness 函数"""

    def test_ust_timeliness(self):
        """测试 UST 时间尺度"""
        assert check_timeliness("UST") == 1

    def test_st_timeliness(self):
        """测试 ST 时间尺度"""
        assert check_timeliness("ST") == 2

    def test_mt_timeliness(self):
        """测试 MT 时间尺度"""
        assert check_timeliness("MT") == 3

    def test_ss_timeliness(self):
        """测试 SS 时间尺度"""
        assert check_timeliness("SS") == 4

    def test_invalid_timeliness(self):
        """测试无效的时间尺度"""
        with pytest.raises(ValueError):
            check_timeliness("INVALID")


class TestCNullKafkaProducer:
    """测试 CNullKafkaProducer 类"""

    def test_init(self):
        """测试初始化"""
        producer = CNullKafkaProducer()
        assert isinstance(producer, CNullKafkaProducer)

    def test_set_topic(self):
        """测试设置主题"""
        producer = CNullKafkaProducer()
        producer.setTopic("test-topic")
        assert producer.topic == "test-topic"

    def test_send(self):
        """测试发送消息（空操作）"""
        producer = CNullKafkaProducer()
        # 空操作不应抛出异常
        producer.send({"key": "value"})

    def test_send_methods(self):
        """测试各种发送方法"""
        producer = CNullKafkaProducer()
        # 测试所有发送方法
        producer.send_checkpoint("task123", 1)
        producer.send_log("task123", "ST", "log.txt")
        producer.send_power("task123", "ST", "power.csv", dt.datetime.now())
        producer.send_acc("task123", "ST", "acc.csv")
        producer.send_key("task123", "ST", "key.txt")
        producer.send_model("task123", "ST", "model.pkl")
        producer.send_hash("task123", "ST", "hash.txt")
        # CNullKafkaProducer.send_meteo 方法不需要 stime 参数
        producer.send_meteo("task123", "ST", "meteo.csv")
        
    def test_close(self):
        """测试关闭生产者（空操作）"""
        producer = CNullKafkaProducer()
        # 空操作不应抛出异常
        producer.close()


class TestCproducer:
    """测试 Cproducer 类"""

    @patch('src.message.KafkaProducer')
    def test_init(self, mock_kafka_producer):
        """测试初始化"""
        mock_kafka_producer.return_value = MagicMock()
        producer = Cproducer(["localhost:9092"])
        assert isinstance(producer, Cproducer)
        mock_kafka_producer.assert_called_once()

    @patch('src.message.KafkaProducer')
    def test_close(self, mock_kafka_producer):
        """测试关闭生产者"""
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        producer = Cproducer(["localhost:9092"])
        producer.close()
        mock_producer.flush.assert_called_once()
        mock_producer.close.assert_called_once()

    @patch('src.message.KafkaProducer')
    def test_send(self, mock_kafka_producer):
        """测试发送消息"""
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        producer = Cproducer(["localhost:9092"])
        producer.topic = "test-topic"
        message = {"key": "value"}
        producer.send(message)
        mock_producer.send.assert_called_once_with(topic="test-topic", value=message)

    @patch('src.message.KafkaProducer')
    def test_send_checkpoint_with_str_taskid(self, mock_kafka_producer):
        """测试发送检查点消息（字符串任务ID）"""
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        producer = Cproducer(["localhost:9092"])
        producer.topic = "test-topic"
        producer.send_checkpoint("task123", 1)
        mock_producer.send.assert_called_once()
        args, kwargs = mock_producer.send.call_args
        assert kwargs["topic"] == "test-topic"
        assert kwargs["value"]["taskid"] == "task123"
        assert kwargs["value"]["checkpoint"] == 1

    @patch('src.message.KafkaProducer')
    def test_send_checkpoint_with_list_taskid(self, mock_kafka_producer):
        """测试发送检查点消息（列表任务ID）"""
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        producer = Cproducer(["localhost:9092"])
        producer.topic = "test-topic"
        producer.send_checkpoint(["task123", "task456"], 1)
        mock_producer.send.assert_called_once()
        args, kwargs = mock_producer.send.call_args
        assert kwargs["topic"] == "test-topic"
        assert kwargs["value"]["taskid"] == "task123"
        assert kwargs["value"]["checkpoint"] == 1

    @patch('src.message.KafkaProducer')
    def test_send_checkpoint_with_invalid_taskid(self, mock_kafka_producer):
        """测试发送检查点消息（无效任务ID）"""
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        producer = Cproducer(["localhost:9092"])
        producer.topic = "test-topic"
        with pytest.raises(ValueError):
            producer.send_checkpoint(None, 1)

    @patch('src.message.KafkaProducer')
    def test_send_log(self, mock_kafka_producer):
        """测试发送日志文件相关的消息"""
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        producer = Cproducer(["localhost:9092"])
        producer.topic = "test-topic"
        producer.send_log("task123", "ST", "log.txt")
        mock_producer.send.assert_called_once()
        args, kwargs = mock_producer.send.call_args
        assert kwargs["topic"] == "test-topic"
        assert kwargs["value"]["taskid"] == "task123"
        assert kwargs["value"]["checkpoint"] == 90
        assert kwargs["value"]["file"]["filePath"] == "log.txt"
        assert kwargs["value"]["status"] == "true"

    @patch('src.message.KafkaProducer')
    def test_send_log_with_list(self, mock_kafka_producer):
        """测试发送多个日志文件相关的消息"""
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        producer = Cproducer(["localhost:9092"])
        producer.topic = "test-topic"
        producer.send_log("task123", "ST", ["log1.txt", "log2.txt"])
        assert mock_producer.send.call_count == 2
        call_args_list = mock_producer.send.call_args_list
        assert call_args_list[0][1]["value"]["file"]["filePath"] == "log1.txt"
        assert call_args_list[1][1]["value"]["file"]["filePath"] == "log2.txt"

    @patch('src.message.KafkaProducer')
    def test_send_power(self, mock_kafka_producer):
        """测试发送功率预测文件相关的消息"""
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        producer = Cproducer(["localhost:9092"])
        producer.topic = "test-topic"
        stime = dt.datetime(2023, 1, 1, 12, 0, 0)
        producer.send_power("task123", "ST", "power.csv", stime)
        mock_producer.send.assert_called_once()
        args, kwargs = mock_producer.send.call_args
        assert kwargs["topic"] == "test-topic"
        assert kwargs["value"]["taskid"] == "task123"
        assert kwargs["value"]["checkpoint"] == 91
        assert kwargs["value"]["stime"] == "2023-01-01 12:00:00"
        assert kwargs["value"]["file"]["filePath"] == "power.csv"

    @patch('src.message.KafkaProducer')
    def test_send_acc(self, mock_kafka_producer):
        """测试发送准确率文件相关的消息"""
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        producer = Cproducer(["localhost:9092"])
        producer.topic = "test-topic"
        producer.send_acc("task123", "ST", "acc.csv")
        mock_producer.send.assert_called_once()
        args, kwargs = mock_producer.send.call_args
        assert kwargs["topic"] == "test-topic"
        assert kwargs["value"]["taskid"] == "task123"
        assert kwargs["value"]["checkpoint"] == 92
        assert kwargs["value"]["file"]["filePath"] == "acc.csv"

    @patch('src.message.KafkaProducer')
    def test_send_key(self, mock_kafka_producer):
        """测试发送密钥文件相关的消息"""
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        producer = Cproducer(["localhost:9092"])
        producer.topic = "test-topic"
        producer.send_key("task123", "ST", "key.txt")
        mock_producer.send.assert_called_once()
        args, kwargs = mock_producer.send.call_args
        assert kwargs["topic"] == "test-topic"
        assert kwargs["value"]["taskid"] == "task123"
        assert kwargs["value"]["checkpoint"] == 93
        assert kwargs["value"]["file"]["filePath"] == "key.txt"

    @patch('src.message.KafkaProducer')
    def test_send_model(self, mock_kafka_producer):
        """测试发送模型文件相关的消息"""
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        producer = Cproducer(["localhost:9092"])
        producer.topic = "test-topic"
        producer.send_model("task123", "ST", "model.pkl")
        mock_producer.send.assert_called_once()
        args, kwargs = mock_producer.send.call_args
        assert kwargs["topic"] == "test-topic"
        assert kwargs["value"]["taskid"] == "task123"
        assert kwargs["value"]["checkpoint"] == 94
        assert kwargs["value"]["file"]["filePath"] == "model.pkl"

    @patch('src.message.KafkaProducer')
    def test_send_hash(self, mock_kafka_producer):
        """测试发送哈希文件相关的消息"""
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        producer = Cproducer(["localhost:9092"])
        producer.topic = "test-topic"
        producer.send_hash("task123", "ST", "hash.txt")
        mock_producer.send.assert_called_once()
        args, kwargs = mock_producer.send.call_args
        assert kwargs["topic"] == "test-topic"
        assert kwargs["value"]["taskid"] == "task123"
        assert kwargs["value"]["checkpoint"] == 95
        assert kwargs["value"]["file"]["filePath"] == "hash.txt"

    @patch('src.message.KafkaProducer')
    def test_send_meteo_with_datetime(self, mock_kafka_producer):
        """测试发送气象文件相关的消息（使用datetime）"""
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        producer = Cproducer(["localhost:9092"])
        producer.topic = "test-topic"
        
        # 创建一个日期时间对象
        dt_obj = dt.datetime(2023, 1, 1, 12, 0, 0)
        # 传入日期时间对象而不是pd.Timestamp
        producer.send_meteo("task123", "ST", "meteo.csv", dt_obj)
        
        mock_producer.send.assert_called_once()
        args, kwargs = mock_producer.send.call_args
        assert kwargs["topic"] == "test-topic"
        assert kwargs["value"]["taskid"] == "task123"
        assert kwargs["value"]["checkpoint"] == 96
        assert "stime" in kwargs["value"]
        assert kwargs["value"]["file"]["filePath"] == "meteo.csv"

    @patch('src.message.KafkaProducer')
    def test_send_pick_best_meoto(self, mock_kafka_producer):
        """测试发送最佳气象模型选择的消息"""
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        producer = Cproducer(["localhost:9092"])
        producer.topic = "test-topic"
        producer.send_pick_best_meoto("task123", "ST")
        mock_producer.send.assert_called_once()
        args, kwargs = mock_producer.send.call_args
        assert kwargs["topic"] == "test-topic"
        assert kwargs["value"]["taskid"] == "task123"
        assert kwargs["value"]["checkpoint"] == 80
        assert "sources" in kwargs["value"]

    @patch('src.message.KafkaProducer')
    def test_send_pick_best_algorithm(self, mock_kafka_producer):
        """测试发送最佳算法选择的消息"""
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        producer = Cproducer(["localhost:9092"])
        producer.topic = "test-topic"
        sources = {
            "algo1": {"order": 1, "acc": 90.5},
            "algo2": {"order": 2, "acc": 85.0}
        }
        producer.send_pick_best_algorithm("task123", "ST", sources)
        mock_producer.send.assert_called_once()
        args, kwargs = mock_producer.send.call_args
        assert kwargs["topic"] == "test-topic"
        assert kwargs["value"]["taskid"] == "task123"
        assert kwargs["value"]["checkpoint"] == 81
        assert kwargs["value"]["sources"] == sources


class TestKafkaIntegration:
    """Kafka集成测试"""

    @pytest.fixture
    def mock_kafka_config(self):
        """模拟Kafka配置"""
        return {
            "bootstrap_servers": ["localhost:9092"],
            "topic": "test-topic"
        }

    @pytest.mark.integration
    @patch('src.message.KafkaProducer')
    def test_producer_consumer_integration(self, mock_kafka_producer, mock_kafka_config):
        """测试生产者和消费者集成"""
        # 这个测试需要在有标记为integration的情况下运行
        # 在实际环境中，可能需要使用真实的Kafka服务器
        mock_producer = MagicMock()
        mock_kafka_producer.return_value = mock_producer
        
        # 创建生产者
        producer = Cproducer(mock_kafka_config["bootstrap_servers"])
        producer.topic = mock_kafka_config["topic"]
        
        # 发送消息
        test_message = {
            "taskid": "integration_test",
            "data": "test_data"
        }
        producer.send(test_message)
        
        # 验证消息是否发送
        mock_producer.send.assert_called_once_with(topic=mock_kafka_config["topic"], value=test_message)
        
        # 关闭生产者
        producer.close()
        mock_producer.flush.assert_called_once()
        mock_producer.close.assert_called_once()


if __name__ == "__main__":
    pytest.main(["-v", "test_message_fixed.py"])