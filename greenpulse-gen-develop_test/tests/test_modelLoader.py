import os
import logging
import hashlib
import pytest
from cryptography.fernet import Fernet

from src.message import CNullKafkaProducer
from src.datasets.modelDump import modelDump
from src.datasets.modelLoad import modelLoad


# 设置临时目录和文件路径
TEMP_DIR = 'temp_test_dir'
MODEL_PATH = os.path.join(TEMP_DIR, 'model.pkl')
HASH_PATH = os.path.join(TEMP_DIR, 'hash.txt')
KEY_PATH = os.path.join(TEMP_DIR, 'key.key')

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown():
    # 在所有测试开始前创建临时目录
    os.makedirs(TEMP_DIR, exist_ok=True)
    print("\nCreate temporary directory: ", os.path.realpath(TEMP_DIR))

    yield

    # 在所有测试结束后删除临时目录及其内容
    # for root, dirs, files in os.walk(TEMP_DIR, topdown=False):
    #     for name in files:
    #         os.remove(os.path.join(root, name))
    #     for name in dirs:
    #         os.rmdir(os.path.join(root, name))
    print("\nDelete temporary directory: ", os.path.realpath(TEMP_DIR))
    os.rmdir(TEMP_DIR)

def test_modelDump():
    # 创建一个简单的模型对象
    model = {'key': 'value'}
    taskId = '1234567890'
    timeliness = 'ST'

    logger =  logging.getLogger()

    # 调用 modelDump 函数
    modelDump(taskId, model, timeliness, MODEL_PATH, HASH_PATH, KEY_PATH, logger, CNullKafkaProducer())

    # 验证文件是否正确创建
    assert os.path.exists(MODEL_PATH)
    assert os.path.exists(HASH_PATH)
    assert os.path.exists(KEY_PATH)

def test_modelLoad():
    # 创建一个简单的模型对象
    model = {'key': 'value'}
    taskId = '1234567890'
    timeliness = 'ST'

    logger = logging.getLogger()

    # 调用 modelDump 函数以生成必要的文件
    modelDump(taskId, model, timeliness, MODEL_PATH, HASH_PATH, KEY_PATH, logger, CNullKafkaProducer())

    # 调用 modelLoad 函数
    loaded_model = modelLoad(MODEL_PATH, HASH_PATH, KEY_PATH, logger)

    # 验证加载的模型是否与原始模型相同
    assert loaded_model == model

def test_modelLoad_with_invalid_hash():
    # 创建一个简单的模型对象
    model = {'key': 'value'}
    taskId = '1234567890'
    timeliness = 'ST'

    logger = logging.getLogger()

    # 调用 modelDump 函数以生成必要的文件
    modelDump(taskId, model, timeliness, MODEL_PATH, HASH_PATH, KEY_PATH, logger, CNullKafkaProducer())

    # 修改哈希文件以模拟哈希不匹配的情况
    hashVal = hashlib.sha256(b'encrypted').hexdigest()
    with open(HASH_PATH, 'w') as f:
        f.write(hashVal)

    # 预期 modelLoad 函数会抛出 ValueError 异常
    with pytest.raises(ValueError) as excinfo:
        modelLoad(MODEL_PATH, HASH_PATH, KEY_PATH, logger)
    assert '模型文件损坏' in str(excinfo.value)

def test_modelLoad_with_invalid_key():
    # 创建一个简单的模型对象
    model = {'key': 'value'}
    taskId = '1234567890'
    timeliness = 'ST'

    logger = logging.getLogger()

    # 调用 modelDump 函数以生成必要的文件
    modelDump(taskId, model, timeliness, MODEL_PATH, HASH_PATH, KEY_PATH, logger, CNullKafkaProducer())

    # 修改密钥文件以模拟密钥不匹配的情况
    key = Fernet.generate_key()
    with open(KEY_PATH, 'wb') as f:
        f.write(key)

    # 预期 modelLoad 函数会抛出异常
    with pytest.raises(Exception) as excinfo:
        modelLoad(MODEL_PATH, HASH_PATH, KEY_PATH, logger)
    assert '模型解密失败' in str(excinfo.value)

def test_modelDump_with_complex_model():
    # 创建一个复杂的模型对象
    model = {
        'nested': {'a': 1, 'b': [1, 2, 3]},
        'list': [1, 2, {'x': 'y'}],
        'none': None,
        'bool': True
    }
    taskId = '1234567890'
    timeliness = 'ST'
    logger = logging.getLogger()

    # 调用 modelDump 函数
    modelDump(taskId, model, timeliness, MODEL_PATH, HASH_PATH, KEY_PATH, logger, CNullKafkaProducer())
    
    # 加载并验证复杂模型
    loaded_model = modelLoad(MODEL_PATH, HASH_PATH, KEY_PATH, logger)
    assert loaded_model == model

def test_modelDump_with_empty_model():
    # 测试空模型
    model = {}
    taskId = '1234567890'
    timeliness = 'ST'
    logger = logging.getLogger()

    modelDump(taskId, model, timeliness, MODEL_PATH, HASH_PATH, KEY_PATH, logger, CNullKafkaProducer())
    loaded_model = modelLoad(MODEL_PATH, HASH_PATH, KEY_PATH, logger)
    assert loaded_model == model

def test_modelDump_with_different_timeliness():
    model = {'test': 'data'}
    taskId = '1234567890'
    logger = logging.getLogger()

    # 测试不同的时效性参数
    for timeliness in ['ST', 'LT', 'RT']:
        modelDump(taskId, model, timeliness, MODEL_PATH, HASH_PATH, KEY_PATH, logger, CNullKafkaProducer())
        loaded_model = modelLoad(MODEL_PATH, HASH_PATH, KEY_PATH, logger)
        assert loaded_model == model

def test_modelLoad_file_not_found():
    logger = logging.getLogger()
    non_existent_path = os.path.join(TEMP_DIR, 'non_existent.pkl')

    # 测试模型文件不存在的情况
    with pytest.raises(FileNotFoundError):
        modelLoad(non_existent_path, HASH_PATH, KEY_PATH, logger)

def test_modelDump_with_large_model():
    # 创建一个较大的模型对象
    model = {f'key_{i}': [i] * 1000 for i in range(1000)}
    taskId = '1234567890'
    timeliness = 'ST'
    logger = logging.getLogger()

    modelDump(taskId, model, timeliness, MODEL_PATH, HASH_PATH, KEY_PATH, logger, CNullKafkaProducer())
    loaded_model = modelLoad(MODEL_PATH, HASH_PATH, KEY_PATH, logger)
    assert loaded_model == model

def test_modelDump_invalid_timeliness():
    model = {'test': 'data'}
    taskId = '1234567890'
    invalid_timeliness = 'INVALID'
    logger = logging.getLogger()

    # 测试无效的时效性参数
    with pytest.raises(ValueError):
        modelDump(taskId, model, invalid_timeliness, MODEL_PATH, HASH_PATH, KEY_PATH, logger, CNullKafkaProducer())
