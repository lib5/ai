#!/usr/bin/env python3
"""
流式数据转换脚本

将原始测试数据中的流式markdown片段合并为完整响应，
生成合并后的测试数据文件。

支持命令行参数:
--input: 输入文件路径
--output: 输出文件路径
--timestamp: 时间戳(可选)

输入: test_results_all_44_20260119_195143-qwen.json
输出: test_results_merged_20260119_195143.json

Usage:
    python convert_stream_data.py --input input.json --output output.json
    python convert_stream_data.py --input input.json  # 自动生成输出文件名
"""

import json
import sys
import argparse
from datetime import datetime
from collections import defaultdict


def merge_consecutive_markdown(raw_data):
    """
    合并连续的markdown数据

    合并规则：
    1. 只合并连续的、具有相同message_id的markdown片段
    2. 被tool、card等分隔符隔开的markdown片段不会被合并
    3. 只合并content字段，其他字段保持第一个片段的值

    Args:
        raw_data: 原始数据列表

    Returns:
        合并后的数据列表
    """
    if not raw_data:
        return raw_data

    print(f"    原始数据条数: {len(raw_data)}")

    # 按timestamp排序
    try:
        sorted_data = sorted(raw_data, key=lambda x: x.get('timestamp', 0))
    except:
        sorted_data = raw_data

    merged_data = []
    i = 0
    markdown_merge_count = 0

    # 统计各种类型的数量
    task_id_count = sum(1 for item in sorted_data if item.get('type') == 'task_id')
    markdown_count = sum(1 for item in sorted_data if item.get('role') == 'assistant' and item.get('type') == 'markdown')
    tool_count = sum(1 for item in sorted_data if (item.get('type') == 'tool') or (item.get('role') == 'assistant' and item.get('type') == 'tool'))
    card_count = sum(1 for item in sorted_data if item.get('type') == 'card')

    print(f"    统计信息:")
    print(f"      - task_id: {task_id_count}")
    print(f"      - markdown: {markdown_count}")
    print(f"      - tool: {tool_count}")
    print(f"      - card: {card_count}")

    while i < len(sorted_data):
        current_item = sorted_data[i]

        # 检查是否是markdown片段
        if (current_item.get('role') == 'assistant' and
            current_item.get('type') == 'markdown'):

            current_message_id = current_item.get('message_id', '')

            # 找到所有具有相同message_id且连续的markdown片段
            # 遇到tool、card或其他非markdown项时停止
            markdown_group = [current_item]
            j = i + 1

            while j < len(sorted_data):
                next_item = sorted_data[j]
                # 检查是否是连续且具有相同message_id的markdown片段
                # 只允许连续的markdown，中间不能有tool或card等分隔符
                if (next_item.get('role') == 'assistant' and
                    next_item.get('type') == 'markdown' and
                    next_item.get('message_id', '') == current_message_id):
                    markdown_group.append(next_item)
                    j += 1
                else:
                    # 遇到分隔符（tool、card等）或不同message_id，停止
                    break

            # 合并markdown片段
            if len(markdown_group) > 1:
                markdown_merge_count += 1
                print(f"    🔗 发现连续markdown组 (message_id: {current_message_id}, {len(markdown_group)}个片段)")

                # 按timestamp排序片段
                markdown_group.sort(key=lambda x: x.get('timestamp', 0))

                # 合并content（只合并content字段）
                merged_content = ""
                for fragment in markdown_group:
                    content = fragment.get('content', '')
                    merged_content += content

                # 使用第一个片段作为模板（保持其他字段不变）
                merged_item = markdown_group[0].copy()
                merged_item['content'] = merged_content
                merged_item['is_merged'] = True
                merged_item['original_fragments'] = len(markdown_group)

                merged_data.append(merged_item)

                print(f"      ✅ 合并完成，内容长度: {len(merged_content)} 字符")
                print(f"      合并前: {''.join([f.get('content', '') for f in markdown_group])}")
                print(f"      合并后: {merged_content}")
                i = j  # 跳过已合并的片段
            else:
                # 单片段，不需要合并
                current_item['is_merged'] = False
                current_item['original_fragments'] = 1
                merged_data.append(current_item)
                i += 1
        else:
            # 非markdown项（task_id, tool, card等），直接添加
            current_item['is_merged'] = False
            current_item['original_fragments'] = 1
            merged_data.append(current_item)
            i += 1

    print(f"    ✅ 连续markdown合并完成:")
    print(f"      - 合并的组数: {markdown_merge_count}")
    print(f"      - 原始数据条数: {len(raw_data)}")
    print(f"      - 合并后数据条数: {len(merged_data)}")
    print(f"      - 减少了 {len(raw_data) - len(merged_data)} 个数据项")
    print(f"    📋 合并规则:")
    print(f"      - 只合并连续的、具有相同message_id的markdown片段")
    print(f"      - 被tool、card等分隔符隔开的markdown片段不会被合并")
    print(f"      - 只合并content字段，其他字段保持第一个片段的值")

    return merged_data


def process_test_case(test_case):
    """处理单个测试用例"""
    test_case_id = test_case.get('test_case_id', 'unknown')
    print(f"\n处理测试用例: {test_case_id}")

    # 深拷贝测试用例，避免修改原始数据
    processed_case = test_case.copy()

    # 处理turn_results
    if 'turn_results' in processed_case:
        for turn_index, turn_result in enumerate(processed_case['turn_results']):
            print(f"  ── 第{turn_index + 1}轮对话 ──")

            if 'execution_result' in turn_result and 'raw_data' in turn_result['execution_result']:
                original_raw_data = turn_result['execution_result']['raw_data']
                print(f"  原始raw_data条数: {len(original_raw_data)}")

                # 合并markdown数据
                merged_raw_data = merge_consecutive_markdown(original_raw_data)

                # 替换原始raw_data
                turn_result['execution_result']['raw_data'] = merged_raw_data
                turn_result['execution_result']['is_merged'] = True

                # 更新response_analysis
                if 'response_analysis' in turn_result['execution_result']:
                    turn_result['execution_result']['response_analysis']['is_merged'] = True
                    turn_result['execution_result']['response_analysis']['original_count'] = len(original_raw_data)
                    turn_result['execution_result']['response_analysis']['merged_count'] = len(merged_raw_data)

    return processed_case


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='流式数据转换脚本 - 合并markdown片段')
    parser.add_argument('--input', '-i', type=str, required=True, help='输入文件路径')
    parser.add_argument('--output', '-o', type=str, help='输出文件路径 (可选，将自动生成)')
    parser.add_argument('--timestamp', '-t', type=str, help='时间戳 (可选，用于生成文件名)')
    args = parser.parse_args()

    # 输入和输出文件
    input_file = args.input
    timestamp = args.timestamp or datetime.now().strftime('%Y%m%d_%H%M%S')

    # 自动生成输出文件名
    if args.output:
        output_file = args.output
    else:
        # 从输入文件名提取时间戳
        import os
        input_basename = os.path.basename(input_file)
        output_file = input_basename.replace('test_results_all_44_', 'test_results_merged_')
        if not output_file.endswith('.json'):
            output_file += '.json'

        # 如果没有找到时间戳，添加当前时间戳
        if 'merged_' not in output_file:
            output_file = f"test_results_merged_{timestamp}.json"

    print("="*80)
    print("流式数据转换脚本 - 合并markdown片段")
    print("="*80)
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")
    print()

    # 读取原始数据
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
    except FileNotFoundError:
        print(f"错误: 输入文件不存在: {input_file}")
        return
    except Exception as e:
        print(f"错误: 读取输入文件失败: {e}")
        return

    print(f"读取到 {len(test_cases)} 个测试用例")

    # 处理每个测试用例
    processed_cases = []
    total_merges = 0

    for i, test_case in enumerate(test_cases):
        print(f"\n[{i+1}/{len(test_cases)}] ", end="")
        processed_case = process_test_case(test_case)
        processed_cases.append(processed_case)

        # 统计合并信息
        if 'turn_results' in processed_case:
            for turn_result in processed_case['turn_results']:
                if 'execution_result' in turn_result and 'raw_data' in turn_result['execution_result']:
                    original_count = turn_result['execution_result'].get('response_analysis', {}).get('original_count', 0)
                    merged_count = turn_result['execution_result'].get('response_analysis', {}).get('merged_count', 0)
                    if original_count > 0 and merged_count > 0:
                        total_merges += (original_count - merged_count)

    print(f"\n" + "="*80)
    print("转换完成!")
    print(f"="*80)
    print(f"处理了 {len(test_cases)} 个测试用例")
    print(f"总共减少了 {total_merges} 个数据项")

    # 保存合并后的数据
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_cases, f, ensure_ascii=False, indent=2)
        print(f"合并后的数据已保存到: {output_file}")
    except Exception as e:
        print(f"错误: 保存输出文件失败: {e}")
        return

    print(f"\n✅ 转换成功完成!")
    print(f"📁 输出文件: {output_file}")
    print(f"📊 合并统计:")
    print(f"   - 总测试用例: {len(processed_cases)}")
    print(f"   - 减少数据项: {total_merges}")
    print(f"   - 压缩率: {(total_merges / sum(len(tc.get('turn_results', [{}])[0].get('execution_result', {}).get('raw_data', [])) for tc in test_cases) * 100):.1f}%" if test_cases else "0%")

    print(f"\n💡 接下来您可以:")
    print(f"   1. 使用合并后的数据文件运行验证: python validate_test_results.py")
    print(f"   2. 或修改验证脚本读取合并后的数据文件")


if __name__ == '__main__':
    main()