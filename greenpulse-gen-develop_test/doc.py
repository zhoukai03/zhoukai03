"""
GreenPulse 项目文档生成工具

模块: doc.py
描述: 使用 pdoc 自动生成项目的 HTML 格式 API 文档。

功能概述:
    1. 自动扫描项目源代码中的文档字符串
    2. 生成美观的 HTML 格式 API 文档
    3. 支持 NumPy 风格的文档字符串格式
    4. 可配置的输入输出路径

依赖项:
    - pdoc3 库 (pip install pdoc3)

使用方法:
    1. 直接运行脚本: `python doc.py`
    2. 默认会在项目根目录下创建 doc/html 目录并生成文档

配置说明:
    - inputPath: 源代码目录，默认为项目根目录下的 src 目录
    - outputPath: 文档输出目录，默认为项目根目录下的 doc/html 目录
    - docformat: 文档字符串格式，默认为 'numpy' 风格

示例:
    # 生成文档
    python doc.py

注意事项:
    1. 确保源代码中的文档字符串格式正确
    2. 生成文档前请确保已安装所有依赖项
    3. 文档生成后可以通过浏览器打开 index.html 查看
"""

import os
import sys
import argparse
import pdoc
import pathlib

def main():
    """
    主函数
    """
    # 获取当前目录
    root = os.path.dirname(__file__)

    # 设置输入和输出路径
    inputPath  = pathlib.Path(f"{root}/src")
    outputPath = pathlib.Path(f"{root}/doc/html")

    # 打印信息
    print(f"制作中（{inputPath}）...")

    # 生成文档
    pdoc.render.configure(docformat = 'numpy')
    doc = pdoc.pdoc(inputPath, output_directory=outputPath)

    # 打印完成信息
    print(f"已完成，输出于 {outputPath}")

if __name__ == "__main__":
    main()
