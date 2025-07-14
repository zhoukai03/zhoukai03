# 新能源发电功率预测系统 (GreenPulse)

[![pipeline status](http://1.119.169.101:10005/GreenPulse/greenpulse-gen/badges/main/pipeline.svg)](http://1.119.169.101:10005/GreenPulse/greenpulse-gen/-/commits/main)
[![coverage report](http://1.119.169.101:10005/GreenPulse/greenpulse-gen/badges/main/coverage.svg)](http://1.119.169.101:10005/GreenPulse/greenpulse-gen/-/commits/main)
[![Latest Release](http://1.119.169.101:10005/GreenPulse/greenpulse-gen/-/badges/release.svg)](http://1.119.169.101:10005/GreenPulse/greenpulse-gen/-/releases)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)


新能源发电功率预测（GreenPulse）是一个用于预测新能源发电功率的先进系统，支持超短期(UST)、短期(ST)、中期(MT)和次季节(SS)等多种时间尺度的预测。本系统采用模块化设计，集成了多种先进的机器学习算法，为新能源发电场提供高精度的功率预测服务。

## ✨ 项目特点

- **多时间尺度预测**：支持超短期(UST)、短期(ST)、中期(MT)和次季节(SS)多种预测模式
- **高精度模型**：集成多种先进机器学习算法，提供高精度预测结果
- **模块化架构**：组件解耦，便于功能扩展和定制化开发
- **完整工作流**：包含数据预处理、特征工程、模型训练、预测和评估全流程
- **高性能计算**：支持GPU加速，优化大规模数据处理
- **分布式支持**：可扩展的分布式部署方案
- **全面监控**：完善的日志记录和性能监控系统
- **持续集成**：自动化测试和部署流水线

## 目录结构

```
.
├── config/             # 配置文件
├── doc/                # 文档
├── src/                # 源代码
│   ├── accuracy/       # 精度评估模块
│   ├── config/         # 配置管理
│   ├── datasets/       # 数据集处理
│   ├── modelset/       # 模型实现
│   │   ├── ST/         # 短期模型
│   │   ├── UST/        # 超短期模型
│   │   ├── base.py     # 模型基类
│   │   └── __init__.py # 模型加载器
│   ├── task.py         # 任务调度
│   ├── utils/          # 工具函数
│   ├── deploy.py       # 部署工具
│   ├── logger.py       # 日志模块
│   ├── message.py      # 消息队列
│   └── params.py       # 参数配置
├── tests/              # 单元测试
└── main.py             # 主程序入口
```

## 🚀 快速开始

### 环境要求

- **操作系统**：Linux
- **Python**：3.12 或更高版本
- **CUDA**：11.8（如需GPU加速）

### 1. 获取代码

```bash
# 克隆仓库
git clone http://221.122.67.135:8005/zhangyongpeng/greenpulse-gen.git
cd greenpulse-gen
```

### 2. 设置环境

```bash
# 创建并激活虚拟环境（conda）
conda create -n greenpulse python=3.12
conda activate greenpulse

# 或者使用 venv
# python -m venv venv
# source venv/bin/activate  # Linux/macOS
# .\venv\Scripts\activate  # Windows

# 安装PyTorch (根据CUDA版本选择)
# CUDA 11.8
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia

# 或者CPU版本
# conda install pytorch torchvision torchaudio cpuonly -c pytorch

# 安装项目依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install -r requirements-dev.txt
```

## 📋 使用方法

### 1. 配置设置

1. 复制示例配置文件：
   ```bash
   cp config/GreenPulse.develop.yaml config/GreenPulse.yaml
   ```

2. 编辑配置文件 `config/GreenPulse.yaml`，根据需求修改以下参数：
   - 数据源配置
   - 模型参数
   - 训练参数
   - 预测参数
   - 日志设置

### 2. 运行预测

```bash
# 查看帮助
python main.py -h

# 运行超短期预测
python main.py --mode predict --model ust --config config/GreenPulse.yaml

# 训练短期模型
python main.py --mode train --model st --config config/GreenPulse.yaml

# 评估模型性能
python main.py --mode evaluate --model st --config config/GreenPulse.yaml
```

### 3. 查看结果

预测结果默认保存在 `output/` 目录下，包括：

- 预测结果CSV文件
- 评估报告
- 可视化图表

## 🛠️ 开发指南

### 代码规范

- 使用类型注解提高代码可读性
- 为所有公共API添加详细的文档字符串

### 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_models.py
# 生成覆盖率报告
pytest --cov=src tests/
# 生成HTML格式的覆盖率报告
pytest --cov=src --cov-report=html tests/
```

### 代码质量检查

```bash
# 代码风格检查
flake8 src/
# 类型检查
mypy src/
# 代码复杂度检查
radon cc src/
```

### 提交规范

我们遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

常用提交类型：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

### 分支管理

- `main`: 主分支，稳定版本
- `develop`: 开发分支，集成最新开发功能
- `feature/*`: 功能开发分支
- `bugfix/*`: bug修复分支

## 🚀 部署指南

### 1. 本地部署

```bash
# 安装生产环境依赖
pip install -r requirements.txt --no-deps
```

### 2. 监控与日志

- 使用 Prometheus + Grafana 监控系统性能
- 日志文件保存在 `logs/` 目录下
- 使用 Sentry 进行错误追踪

## 📚 文档

- [开发文档](./doc/开发文档.md) - 项目架构和开发指南
- [API参考](./doc/html/index.html) - 详细的API接口说明
- [用户手册](./doc/用户手册.md) - 用户操作指南

### API文档

启动本地文档服务器：

```bash
# 构建文档
python doc.py

# 启动文档服务器
python -m http.server 8000 --directory doc/html
```

访问 http://localhost:8000 查看API文档。

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 报告问题

如果您发现任何问题或有功能建议，请[提交Issue](http://1.119.169.101:10005/GreenPulse/greenpulse-gen/-/issues/new)。

### 提交代码

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 开发流程

1. 从 `develop` 分支拉取最新代码
2. 在特性分支上开发
3. 编写单元测试
4. 确保所有测试通过
5. 提交代码并创建合并请求

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

## 🔍 已知问题

- [ ] 在极端天气条件下预测精度可能下降
- [ ] 大数据集上训练时间较长
- [ ] 内存占用优化空间

## 📞 联系方式

- 项目主页: [GreenPulse Homepage](http://example.com)
- 问题追踪: [Issue Tracker](http://1.119.169.101:10005/GreenPulse/greenpulse-gen/-/issues)

## 🙏 致谢

- 感谢所有贡献者的辛勤付出

---

<p align="center">
  <a href="http://example.com">
    <img src="docs/logo.png" alt="Logo" width="200" height="200">
  </a>
  <h3 align="center">GreenPulse - 新能源发电功率预测系统</h3>
  <p align="center">
    精准预测，智享绿色能源
    <br />
    <a href="http://1.119.169.101:10095/greenpulse-gen/src.html"><strong>探索文档 »</strong></a>
    <br />
    <br />
    <a href="http://1.119.169.101:10005/GreenPulse/greenpulse-gen/-/issues/new">报告问题</a>
    ·
    <a href="http://1.119.169.101:10005/GreenPulse/greenpulse-gen/-/merge_requests/new">提交功能</a>
  </p>
</p>
