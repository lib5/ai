#!/usr/bin/env python3
"""
自动化评估流水线主控脚本

一键自动化评估流程，无需手动修改文件或指定文件名。
智能文件识别机制会自动找到上一步生成的输出文件作为下一步的输入。

Usage:
    python run_evaluation_pipeline.py
    python run_evaluation_pipeline.py --limit 5
    python run_evaluation_pipeline.py --dry-run
    python run_evaluation_pipeline.py --step 1
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime
from pathlib import Path


class EvaluationPipeline:
    """评估流水线主控类"""

    def __init__(self, work_dir=None, timestamp=None):
        # 默认使用脚本所在目录
        self.work_dir = Path(work_dir) if work_dir else Path(__file__).parent
        self.timestamp = timestamp or datetime.now().strftime('%Y%m%d_%H%M%S')
        # 统一将结果和日志保存在 pipline_results 目录下
        self.pipeline_root_dir = self.work_dir / "pipline_results"
        self.run_dir = self.pipeline_root_dir / f"runs_{self.timestamp}"
        self.log_dir = self.run_dir / "logs"
        self.log_file = self.log_dir / f"pipeline_{self.timestamp}.log"

        # 创建必要的目录
        self.pipeline_root_dir.mkdir(exist_ok=True)
        self.run_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)

    def log(self, message, level="INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [{level}] {message}\n"
        print(message)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg)

    def run_command(self, command, dry_run=False):
        """执行命令"""
        self.log(f"🚀 执行命令: {command}")

        if dry_run:
            self.log("⚠️  试运行模式，不执行命令")
            return True

        try:
            # 对于Python命令，添加 -u 参数强制非缓冲输出
            if command.strip().startswith('python '):
                command = command.replace('python ', 'python -u ', 1)

            # 使用 Popen 实现实时输出
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.work_dir,
                bufsize=1,
                universal_newlines=True
            )

            # 实时输出到控制台
            for line in process.stdout:
                print(line.rstrip(), flush=True)  # 强制刷新输出

            # 等待进程完成
            process.wait()

            if process.returncode == 0:
                self.log(f"✅ 命令执行成功")
                return True
            else:
                self.log(f"❌ 命令执行失败，返回码: {process.returncode}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ 命令执行异常: {str(e)}", "ERROR")
            return False

    def find_latest_file(self, pattern, exclude_timestamp=None):
        """查找最新匹配的文件"""
        files = list(self.work_dir.glob(pattern))

        if exclude_timestamp:
            files = [f for f in files if exclude_timestamp not in f.name]

        if not files:
            return None

        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return files[0]

    def get_input_file_for_step(self, step, exclude_timestamp=None):
        """获取步骤的输入文件"""
        if step == 2:
            # 步骤2需要步骤1的输出
            pattern = "test_results_all_44_*.json"
        elif step == 3:
            # 步骤3需要步骤2的输出
            pattern = "test_results_merged_*.json"
        else:
            return None

        file = self.find_latest_file(pattern, exclude_timestamp)
        if file:
            self.log(f"📥 自动发现输入文件: {file}")
        return file

    def step1_run_tests(self, limit=None, dry_run=False):
        """步骤1: 运行测试用例"""
        self.log("\n" + "="*80)
        self.log("📌 开始执行: 运行测试")
        self.log("🔄 步骤1: 运行测试用例")
        self.log("="*80)

        output_file = self.run_dir / f"test_results_all_44_{self.timestamp}.json"

        # 构建命令
        cmd_parts = [
            "python", "test_all_cases.py",
            "--output", str(output_file),
            "--timestamp", self.timestamp
        ]

        if limit:
            cmd_parts.extend(["--limit", str(limit)])

        command = " ".join(cmd_parts)

        self.log(f"📁 输出文件: {output_file}")
        self.log(f"🚀 执行命令: {command}")

        success = self.run_command(command, dry_run)

        if not dry_run and success and output_file.exists():
            self.log(f"✅ 测试完成: {output_file}")
            return str(output_file)
        elif dry_run:
            self.log(f"✅ 测试命令已准备: {output_file}")
            return str(output_file)
        else:
            self.log(f"❌ 测试失败", "ERROR")
            return None

    def step2_merge_stream_data(self, input_file, dry_run=False):
        """步骤2: 合并流式数据"""
        self.log("\n" + "="*80)
        self.log("📌 开始执行: 合并流式数据")
        self.log("🔄 步骤2: 合并流式数据")
        self.log("="*80)

        output_file = self.run_dir / f"test_results_merged_{self.timestamp}.json"

        command = f"python convert_stream_data.py --input {input_file} --output {output_file}"

        self.log(f"📥 输入文件: {input_file}")
        self.log(f"📁 输出文件: {output_file}")
        self.log(f"🚀 执行命令: {command}")

        success = self.run_command(command, dry_run)

        if not dry_run and success and output_file.exists():
            self.log(f"✅ 合并完成: {output_file}")
            return str(output_file)
        elif dry_run:
            self.log(f"✅ 合并命令已准备: {output_file}")
            return str(output_file)
        else:
            self.log(f"❌ 合并失败", "ERROR")
            return None

    def step3_validate_results(self, input_file, dry_run=False):
        """步骤3: 验证测试结果"""
        self.log("\n" + "="*80)
        self.log("📌 开始执行: 验证结果")
        self.log("🔄 步骤3: 验证测试结果")
        self.log("="*80)

        output_file = self.run_dir / f"validation_report_{self.timestamp}.json"

        command = f"python validate_test_gemini_results.py --input {input_file} --output {output_file}"

        self.log(f"📥 输入文件: {input_file}")
        self.log(f"📁 输出文件: {output_file}")
        self.log(f"🚀 执行命令: {command}")

        success = self.run_command(command, dry_run)

        if not dry_run and success and output_file.exists():
            self.log(f"✅ 验证完成: {output_file}")
            return str(output_file)
        elif dry_run:
            self.log(f"✅ 验证命令已准备: {output_file}")
            return str(output_file)
        else:
            self.log(f"❌ 验证失败", "ERROR")
            return None

    def generate_summary_report(self, step_results, dry_run=False):
        """生成汇总报告"""
        self.log("\n" + "="*80)
        self.log("📊 生成汇总报告")
        self.log("="*80)

        summary_file = self.run_dir / f"pipeline_summary_{self.timestamp}.json"

        summary = {
            "timestamp": self.timestamp,
            "pipeline_status": "completed" if all(step_results.values()) else "partial",
            "steps": {
                "step1_run_tests": {
                    "status": "completed" if step_results.get(1) else "failed",
                    "output_file": step_results.get(1, "N/A")
                },
                "step2_merge_stream_data": {
                    "status": "completed" if step_results.get(2) else "failed",
                    "input_file": step_results.get(1, "N/A"),
                    "output_file": step_results.get(2, "N/A")
                },
                "step3_validate_results": {
                    "status": "completed" if step_results.get(3) else "failed",
                    "input_file": step_results.get(2, "N/A"),
                    "output_file": step_results.get(3, "N/A")
                }
            },
            "output_directory": str(self.run_dir),
            "summary": {
                "raw_response": step_results.get(1, "N/A"),
                "merged_response": step_results.get(2, "N/A"),
                "validation_report": step_results.get(3, "N/A")
            },
            "statistics": self._calculate_statistics(step_results)
        }

        if not dry_run:
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            self.log(f"✅ 汇总报告已生成: {summary_file}")
        else:
            self.log(f"✅ 汇总报告已准备: {summary_file}")

        return str(summary_file)

    def _calculate_statistics(self, step_results):
        """计算统计信息"""
        stats = {
            "success_rate": 0.0,
            "completed_steps": 0,
            "total_steps": 3
        }

        completed = sum(1 for v in step_results.values() if v)
        stats["completed_steps"] = completed
        stats["success_rate"] = (completed / stats["total_steps"]) * 100

        return stats

    def print_banner(self, limit=None, step=None, dry_run=False):
        """打印启动横幅"""
        self.log("\n" + "="*80)
        self.log("🚀 自动化评估流水线启动")
        self.log("="*80)
        self.log(f"⏰ 时间戳: {self.timestamp}")
        self.log(f"📁 工作目录: {self.work_dir}")
        self.log(f"📁 流水线根目录: {self.pipeline_root_dir}")
        self.log(f"📁 输出目录: {self.run_dir}")
        self.log(f"📁 日志目录: {self.log_dir}")
        if limit:
            self.log(f"🔢 限制测试数量: {limit}")
        if step:
            self.log(f"🎯 执行步骤: {step}")
        if dry_run:
            self.log(f"🔍 试运行模式: 启用")
        self.log("="*80)

    def print_completion(self, step_results):
        """打印完成信息"""
        self.log("\n" + "="*80)
        self.log("🎉 流水线执行完成!")
        self.log("="*80)
        self.log(f"⏰ 时间戳: {self.timestamp}")
        self.log(f"📁 流水线根目录: {self.pipeline_root_dir}")
        self.log(f"📁 输出目录: {self.run_dir}")
        self.log(f"📁 日志目录: {self.log_dir}")
        self.log("📄 生成文件:")

        for key, value in step_results.items():
            if value:
                if key == 1:
                    self.log(f"   - raw_response: {Path(value).name}")
                elif key == 2:
                    self.log(f"   - merged_response: {Path(value).name}")
                elif key == 3:
                    self.log(f"   - validation_report: {Path(value).name}")

        stats = self._calculate_statistics(step_results)
        self.log(f"📊 成功率: {stats['success_rate']:.1f}%")
        self.log("="*80)

    def run_full_pipeline(self, limit=None, dry_run=False):
        """运行完整流水线"""
        step_results = {}

        # 步骤1: 运行测试
        result1 = self.step1_run_tests(limit, dry_run)
        step_results[1] = result1

        # 步骤2: 合并流式数据
        if step_results[1] or dry_run:
            result2 = self.step2_merge_stream_data(step_results[1] or "dry_run_input.json", dry_run)
            step_results[2] = result2

            # 步骤3: 验证结果
            if step_results[2] or dry_run:
                result3 = self.step3_validate_results(step_results[2] or "dry_run_input.json", dry_run)
                step_results[3] = result3

        # 生成汇总报告
        self.generate_summary_report(step_results, dry_run)

        # 打印完成信息
        if not dry_run:
            self.print_completion(step_results)

        return all(step_results.values())


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='自动化评估流水线')
    parser.add_argument('--work-dir', type=str, default=None,
                      help='工作目录 (默认: 脚本所在目录)')
    parser.add_argument('--limit', type=int, help='限制测试用例数量')
    parser.add_argument('--dry-run', action='store_true', help='试运行模式（显示将要执行的命令但不实际执行）')
    parser.add_argument('--step', type=int, choices=[1, 2, 3], help='只执行特定步骤')
    parser.add_argument('--timestamp', type=str, help='指定时间戳（可选）')

    args = parser.parse_args()

    # 创建流水线实例
    pipeline = EvaluationPipeline(work_dir=args.work_dir, timestamp=args.timestamp)

    # 打印启动横幅
    pipeline.print_banner(limit=args.limit, step=args.step, dry_run=args.dry_run)

    # 执行流水线
    if args.step:
        # 单步执行
        if args.step == 1:
            result = pipeline.step1_run_tests(limit=args.limit, dry_run=args.dry_run)
        elif args.step == 2:
            # 需要步骤1的输出文件
            input_file = pipeline.get_input_file_for_step(2, exclude_timestamp=pipeline.timestamp)
            if not input_file and not args.dry_run:
                pipeline.log("❌ 找不到步骤1的输出文件，请先执行步骤1", "ERROR")
                sys.exit(1)
            input_file = input_file or "dry_run_input.json"
            result = pipeline.step2_merge_stream_data(input_file, dry_run=args.dry_run)
        elif args.step == 3:
            # 需要步骤2的输出文件
            input_file = pipeline.get_input_file_for_step(3, exclude_timestamp=pipeline.timestamp)
            if not input_file and not args.dry_run:
                pipeline.log("❌ 找不到步骤2的输出文件，请先执行步骤2", "ERROR")
                sys.exit(1)
            input_file = input_file or "dry_run_input.json"
            result = pipeline.step3_validate_results(input_file, dry_run=args.dry_run)

        # 生成汇总报告
        step_results = {args.step: result}
        pipeline.generate_summary_report(step_results, dry_run=args.dry_run)

        if not args.dry_run and result:
            pipeline.log(f"✅ 步骤{args.step}执行完成")
            sys.exit(0)
        elif args.dry_run:
            pipeline.log(f"✅ 步骤{args.step}命令已准备")
            sys.exit(0)
        else:
            pipeline.log(f"❌ 步骤{args.step}执行失败", "ERROR")
            sys.exit(1)
    else:
        # 执行完整流水线
        success = pipeline.run_full_pipeline(limit=args.limit, dry_run=args.dry_run)

        if not args.dry_run:
            sys.exit(0 if success else 1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main()
