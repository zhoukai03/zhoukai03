# GreenPulse测试套件

本目录包含用于测试GreenPulse各模块功能的测试套件。

## 测试模块说明

### Kafka消息队列测试

- `test_message.py` - 针对消息模块的单元测试，使用模拟对象测试生产者行为
- `test_kafka_integration.py` - Kafka集成测试，需要真实的Kafka环境
- `conftest.py` - 包含测试所需的Pytest fixtures，可以自动创建Docker测试容器

### 准确率评估测试

- `test_accuracy.py` - 针对准确率评估模块的基本单元测试
- `test_accuracy_parametrized.py` - 参数化测试不同情况下的准确率计算
- `test_accuracy_integration.py` - 准确率模块与任务工作流的集成测试
- `accuracy_test_utils.py` - 准确率测试的辅助工具和函数

## 依赖项

运行这些测试需要以下依赖：

```bash
pip install pytest pytest-mock pytest-timeout pytest-cov pandas numpy kafka-python
```

如果要使用Docker自动化测试，还需要：

```bash
pip install docker
```

## 运行测试

### 运行所有测试

```bash
# 运行所有测试
pytest -v tests/

# 运行并生成覆盖率报告
pytest -v --cov=src tests/
```

### 运行Kafka消息队列测试

单元测试不需要实际的Kafka环境：

```bash
pytest -v tests/test_message.py
```

集成测试需要连接到实际的Kafka服务器：

#### 使用现有Kafka服务器

```bash
# 设置Kafka服务器地址和主题
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export KAFKA_TOPIC=test-topic

# 运行集成测试
pytest -v -m integration tests/test_kafka_integration.py
```

#### 使用自动Docker容器

如果安装了Docker和docker-py库，可以让测试自动创建临时Kafka容器：

```bash
# 确保未设置KAFKA_BOOTSTRAP_SERVERS环境变量
unset KAFKA_BOOTSTRAP_SERVERS

# 运行集成测试
pytest -v -m integration tests/test_kafka_integration.py
```

### 运行准确率评估测试

```bash
# 运行基本准确率测试
pytest -v tests/test_accuracy.py

# 运行参数化准确率测试
pytest -v tests/test_accuracy_parametrized.py

# 运行准确率集成测试
pytest -v tests/test_accuracy_integration.py

# 运行所有准确率相关测试
pytest -v tests/test_accuracy*.py
```

## 测试标记

- `integration` - 标记需要实际Kafka环境的测试

## CI/CD集成

在CI/CD环境中，可以通过以下方式设置：

```yaml
# 在GitLab CI中
kafka_tests:
  stage: test
  services:
    - name: bitnami/kafka:latest
      alias: kafka
      variables:
        KAFKA_CFG_NODE_ID: "0"
        KAFKA_CFG_PROCESS_ROLES: "controller,broker"
        KAFKA_CFG_CONTROLLER_QUORUM_VOTERS: "0@localhost:9093"
        KAFKA_CFG_LISTENERS: "PLAINTEXT://:9092,CONTROLLER://:9093" 
        KAFKA_CFG_ADVERTISED_LISTENERS: "PLAINTEXT://kafka:9092"
        KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP: "CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT"
        KAFKA_CFG_CONTROLLER_LISTENER_NAMES: "CONTROLLER"
        ALLOW_PLAINTEXT_LISTENER: "yes"
        KAFKA_KRAFT_CLUSTER_ID: "MkU3OEVBNTcwNTJENDM2Qk"
  variables:
    KAFKA_BOOTSTRAP_SERVERS: "kafka:9092"
    KAFKA_TOPIC: "test-topic"
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-mock pytest-timeout kafka-python
    - pytest -v tests/test_message.py tests/test_kafka_integration.py

accuracy_tests:
  stage: test
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-mock pytest-cov pandas numpy
    - pytest -v tests/test_accuracy*.py
```

## 故障排除

### Kafka测试相关

1. 如果测试卡住，可能是由于无法连接到Kafka。检查服务器是否在运行，端口是否正确。

2. 如果使用Docker但容器未能正确启动，检查Docker服务是否在运行，以及是否有足够权限。

3. 如果消息发送了但消费者未收到，检查主题名称是否一致，以及消费者组ID。

### 准确率测试相关

1. 如果准确率测试出现NaN或无限值错误，检查测试数据中是否存在零值或极端值。

2. 在测试MAPE指标时，如果观测值包含零，可能会出现除零警告或错误。

3. 参数化测试需要较长时间运行，可以使用`-k`参数选择性运行部分测试：
   ```bash
   pytest -v tests/test_accuracy_parametrized.py -k "test_accuracy_calculation"
   ```
