# 流水线结果目录

## 目录结构

```
pipline_results/
├── README.md                    # 本说明文件
├── runs_YYYYMMDD_HHMMSS/       # 每次运行的目录
│   ├── logs/                   # 日志文件目录
│   │   └── pipeline_YYYYMMDD_HHMMSS.log
│   ├── test_results_all_44_YYYYMMDD_HHMMSS.json    # 步骤1输出：原始测试结果
│   ├── test_results_merged_YYYYMMDD_HHMMSS.json   # 步骤2输出：合并后的流式数据
│   ├── validation_report_YYYYMMDD_HHMMSS.json     # 步骤3输出：验证报告
│   └── pipeline_summary_YYYYMMDD_HHMMSS.json      # 汇总报告
└── ...
```

## 目录说明

### `pipline_results/` - 流水线根目录
所有流水线运行的结果都保存在这个目录下，每个运行实例会创建一个带时间戳的子目录。

### `runs_YYYYMMDD_HHMMSS/` - 运行目录
每次执行流水线时都会创建一个新的目录，目录名包含执行的时间戳：
- `YYYYMMDD`：年、月、日
- `HHMMSS`：时、分、秒

### `logs/` - 日志目录
包含所有执行过程中的日志文件：
- `pipeline_YYYYMMDD_HHMMSS.log`：完整的流水线执行日志

### 输出文件
每个运行目录包含以下文件：

1. **test_results_all_44_YYYYMMDD_HHMMSS.json**
   - 来源：步骤1（运行测试用例）
   - 内容：原始测试结果数据
   - 大小：通常较大，包含完整的原始响应

2. **test_results_merged_YYYYMMDD_HHMMSS.json**
   - 来源：步骤2（合并流式数据）
   - 内容：处理和合并后的流式响应数据
   - 大小：中等，结构化的数据

3. **validation_report_YYYYMMDD_HHMMSS.json**
   - 来源：步骤3（验证结果）
   - 内容：验证分析报告，包含评分和统计信息
   - 大小：通常较小，主要包含分析结果

4. **pipeline_summary_YYYYMMDD_HHMMSS.json**
   - 来源：流水线自动生成
   - 内容：整个流水线的汇总信息，包括步骤状态、文件路径和统计信息
   - 大小：小，主要包含元数据

## 使用方式

### 运行流水线
```bash
# 运行完整流水线
python run_evaluation_pipeline.py

# 限制测试数量
python run_evaluation_pipeline.py --limit 10

# 试运行（不实际执行命令）
python run_evaluation_pipeline.py --dry-run

# 执行特定步骤
python run_evaluation_pipeline.py --step 1
python run_evaluation_pipeline.py --step 2
python run_evaluation_pipeline.py --step 3
```

### 查看结果
```bash
# 查看最新的运行结果
ls -la pipline_results/runs_*/

# 查看特定运行的日志
cat pipline_results/runs_*/logs/pipeline_*.log

# 查看汇总报告
cat pipline_results/runs_*/pipeline_summary_*.json
```

### 清理旧结果
```bash
# 删除所有旧的运行结果（谨慎使用）
rm -rf pipline_results/runs_*/

# 删除指定时间戳之前的运行结果
find pipline_results/ -name "runs_*" -type d -mtime +7 -exec rm -rf {} +
```

## 优势

1. **统一管理**：所有结果和日志都在同一个目录下
2. **时间戳隔离**：每次运行的结果不会相互覆盖
3. **易于追溯**：通过时间戳可以精确找到特定运行的记录
4. **结构清晰**：目录结构直观，便于查找和分析
5. **日志完整**：所有执行过程都记录在日志文件中

## 注意事项

- 每个运行目录在创建后会自动创建 `logs/` 子目录
- 日志文件会同时输出到控制台和日志文件
- 建议定期清理旧的运行结果以节省磁盘空间
- 重要结果请及时备份到其他位置
