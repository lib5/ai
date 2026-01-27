# 自动化评估流水线使用说明

## 🎯 概述

本流水线实现了**一键自动化评估流程**，无需手动修改文件或指定文件名。智能文件识别机制会自动找到上一步生成的输出文件作为下一步的输入。

## 工作路径 运行前执行以下命令
source /home/libo/chatapi/venv_mcp/bin/activate 

cd /home/libo/chatapi/test_dataset_quantity

## 修改环境以及数据集

### 修改环境 
定位 **test_all_cases.py**    查找“环境地址"定位到**base_url**  (28000、8000)修改后运行下面方式1命令即可


### 修改数据集
定位 test_all_cases.py  查找 **"--input"** 定位到参数设置 修改raw_data/{*.json} 可以替换raw_data目录下任意json文件

- v1 final_cast.json：44用例（单轮17、多轮27、图像9）
- v2 final_cast_v2.json：74用例（单轮47、多轮27、图像39）
- v3 final_cast_v3-101.json：101用例（单轮47、多轮54、图像41）

## 🚀 快速开始

### 方式1: 运行完整流水线（推荐）

```bash
# 运行完整流水线（测试全部74个用例）默认使用final_cast_v2.json  
python run_evaluation_pipeline.py

# 运行完整流水线（只测试前5个用例，用于快速验证）
python run_evaluation_pipeline.py --limit 5
```


### 方式3: 单步执行

```bash
# 步骤1: 运行测试脚本
python test_all_cases.py --limit 5 --output test_results.json 

# 步骤2: 合并流式数据（必须指定输入文件）
python convert_stream_data.py --input test_results.json --output merged_results.json

# 步骤3: 评估结果脚本（必须指定输入文件）
python validate_test_gemini_results.py --input merged_results.json --output validation_report.json
```

**默认输出文件说明**:
- **步骤1**: 不指定 `--output` 时，默认输出 `test_results_all_44_{timestamp}.json`  输入修改数据集查看第十八行
- **步骤2**: 不指定 `--output` 时，默认输出 `test_results_merged_{timestamp}.json`
- **步骤3**: 不指定 `--output` 时，默认输出 `validation_reports/validation_report_{timestamp}.json`

## 📊 输出文件

流水线会在 `pipline_results/runs_{timestamp}` 目录下生成以下文件：

```
pipline_results/runs_20260122_110900/
├── logs/
│   └── pipeline_20260122_110900.log              # 完整执行日志
├── test_results_all_44_20260122_110900.json     # 原始测试结果
├── test_results_merged_20260122_110900.json     # 流式合并后的结果
├── validation_report_20260122_110900.json       # 验证报告
└── pipeline_summary_20260122_110900.json        # 汇总报告
```



