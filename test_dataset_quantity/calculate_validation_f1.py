#!/usr/bin/env python3
"""
计算三个完整验证报告的F1分数
基于模型判断和真实错误案例
"""

import json
import os
from datetime import datetime
from pathlib import Path

def calculate_f1_from_reports():
    """计算三个验证报告的F1分数"""
    print("📊 计算三个验证报告的F1分数")
    print("="*100)

    # 定义三个验证报告 - 使用动态查找
    script_dir = Path(__file__).parent

    def find_latest_report(pattern_name):
        """查找最新的验证报告"""
        import glob
        pattern = str(script_dir / "validation_reports" / pattern_name)
        files = glob.glob(pattern)
        if files:
            return max(files, key=os.path.getmtime)
        return None

    def find_error_file(error_name):
        """查找错误文件"""
        error_path = script_dir / "act_erro" / error_name
        return str(error_path) if error_path.exists() else None

    reports = [
        {
            "name": "Gemini验证报告",
            "report_path": find_latest_report("validation_report_*gemini*.json"),
            "error_path": find_error_file("gemini_act_erro.json")
        },
        {
            "name": "Doubao验证报告",
            "report_path": find_latest_report("validation_report_*doubao*.json"),
            "error_path": find_error_file("doubao_act_erro.json")
        },
        {
            "name": "Qwem验证报告",
            "report_path": find_latest_report("validation_report_*qwen*.json"),
            "error_path": find_error_file("qwen_act_err.json")
        }
    ]

    results = []

    for report_info in reports:
        print(f"\n{'='*100}")
        print(f"分析: {report_info['name']}")
        print(f"{'='*100}")

        # 加载验证报告
        with open(report_info['report_path'], 'r', encoding='utf-8') as f:
            validation_data = json.load(f)

        # 加载真实错误案例
        try:
            with open(report_info['error_path'], 'r', encoding='utf-8') as f:
                error_data = json.load(f)
            real_error_ids = {case['test_case_id'] for case in error_data}
            print(f"真实错误案例数: {len(real_error_ids)}")
        except Exception as e:
            real_error_ids = set()
            print(f"无法加载错误数据: {e}")

        # 获取验证报告摘要
        summary = validation_data['validation_summary']
        print(f"总案例数: {summary['total_cases']}")
        print(f"模型预测正确: {summary['correct_count']}")
        print(f"模型预测错误: {summary['wrong_count']}")
        print(f"准确率: {summary['accuracy_rate']:.2f}%")

        # 计算混淆矩阵
        tp = fp = tn = fn = 0

        for case in validation_data['validation_details']:
            case_id = case['test_case_id']
            model_prediction = case['is_correct']  # 模型的预测
            is_actually_error = case_id in real_error_ids  # 实际情况

            if is_actually_error:
                # 实际上错误的案例
                if model_prediction == '错误':
                    tn += 1  # 真负例：模型预测错误，且确实是错误
                else:
                    fp += 1  # 假正例：模型预测正确，但实际是错误
            else:
                # 实际上正确的案例
                if model_prediction == '正确':
                    tp += 1  # 真正例：模型预测正确，且确实是正确
                else:
                    fn += 1  # 假负例：模型预测错误，但实际是正确的

        total_cases = len(validation_data['validation_details'])

        # 计算指标
        accuracy = (tp + tn) / total_cases if total_cases > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        # 保存结果
        result = {
            "name": report_info['name'],
            "total_cases": total_cases,
            "true_positive": tp,
            "false_positive": fp,
            "true_negative": tn,
            "false_negative": fn,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "real_error_count": len(real_error_ids)
        }
        results.append(result)

        # 打印结果
        print(f"\n📈 F1分数计算结果:")
        print(f"混淆矩阵:")
        print(f"  TP (真正例): {tp}")
        print(f"  FP (假正例): {fp}")
        print(f"  TN (真负例): {tn}")
        print(f"  FN (假负例): {fn}")
        print(f"核心指标:")
        print(f"  F1分数: {f1_score:.4f} ({f1_score*100:.2f}%)")
        print(f"  准确率: {accuracy:.4f} ({accuracy*100:.2f}%)")
        print(f"  精确率: {precision:.4f} ({precision*100:.2f}%)")
        print(f"  召回率: {recall:.4f} ({recall*100:.2f}%)")

    # 对比分析
    print(f"\n{'='*100}")
    print("📊 三个验证报告对比")
    print(f"{'='*100}")

    if len(results) >= 2:
        gemini_result = results[0]
        doubao_result = results[1]
        qwen_result = results[2]

        print(f"\n📋 对比表格:")
        print(f"{'指标':<12} | {'Gemini':<15} | {'Doubao':<15} | {'Qwen':<15} | {'最佳':<10}")
        print("-" * 85)

        # F1分数
        f1_scores = [gemini_result['f1_score'], doubao_result['f1_score'], qwen_result['f1_score']]
        best_f1 = max(f1_scores)
        best_model = ['Gemini', 'Doubao', 'Qwen'][f1_scores.index(best_f1)]
        print(f"{'F1分数':<12} | {gemini_result['f1_score']:<15.4f} | {doubao_result['f1_score']:<15.4f} | {qwen_result['f1_score']:<15.4f} | {best_model:<10}")

        # 准确率
        acc_scores = [gemini_result['accuracy'], doubao_result['accuracy'], qwen_result['accuracy']]
        best_acc = max(acc_scores)
        best_acc_model = ['Gemini', 'Doubao', 'Qwen'][acc_scores.index(best_acc)]
        print(f"{'准确率':<12} | {gemini_result['accuracy']:<15.4f} | {doubao_result['accuracy']:<15.4f} | {qwen_result['accuracy']:<15.4f} | {best_acc_model:<10}")

        # 精确率
        prec_scores = [gemini_result['precision'], doubao_result['precision'], qwen_result['precision']]
        best_prec = max(prec_scores)
        best_prec_model = ['Gemini', 'Doubao', 'Qwen'][prec_scores.index(best_prec)]
        print(f"{'精确率':<12} | {gemini_result['precision']:<15.4f} | {doubao_result['precision']:<15.4f} | {qwen_result['precision']:<15.4f} | {best_prec_model:<10}")

        # 召回率
        recall_scores = [gemini_result['recall'], doubao_result['recall'], qwen_result['recall']]
        best_recall = max(recall_scores)
        best_recall_model = ['Gemini', 'Doubao', 'Qwen'][recall_scores.index(best_recall)]
        print(f"{'召回率':<12} | {gemini_result['recall']:<15.4f} | {doubao_result['recall']:<15.4f} | {qwen_result['recall']:<15.4f} | {best_recall_model:<10}")

        # 计算平均F1（三个模型）
        avg_f1 = (gemini_result['f1_score'] + doubao_result['f1_score'] + qwen_result['f1_score']) / 3
        print(f"\n🎯 三个模型的平均F1分数: {avg_f1:.4f} ({avg_f1*100:.2f}%)")
        print(f"   Gemini F1: {gemini_result['f1_score']:.4f} ({gemini_result['f1_score']*100:.2f}%)")
        print(f"   Doubao F1: {doubao_result['f1_score']:.4f} ({doubao_result['f1_score']*100:.2f}%)")
        print(f"   Qwen F1:   {qwen_result['f1_score']:.4f} ({qwen_result['f1_score']*100:.2f}%)")

        # 分析最佳模型
        print(f"\n🏆 性能排名:")
        sorted_results = sorted(zip(['Gemini', 'Doubao', 'Qwen'], f1_scores), key=lambda x: x[1], reverse=True)
        for i, (model, score) in enumerate(sorted_results, 1):
            print(f"   {i}. {model}: {score:.4f} ({score*100:.2f}%)")

        # 性能差异分析
        f1_range = max(f1_scores) - min(f1_scores)
        if f1_range < 0.01:
            print(f"   ✅ 三个模型性能接近 (F1范围: {f1_range:.4f})")
        else:
            best_model_name = sorted_results[0][0]
            print(f"   📈 {best_model_name}性能最佳，领先 {f1_range:.4f}")

    # 创建f1_score目录
    f1_score_dir = script_dir / "f1_score"
    os.makedirs(f1_score_dir, exist_ok=True)

    # 保存结果
    output_file = f1_score_dir / f"validation_f1_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "average_f1": avg_f1 if len(results) >= 3 else None,
            "description": "三个验证报告的F1分数分析"
        }, f, ensure_ascii=False, indent=2)

    print(f"\n💾 结果已保存到: {output_file}")

if __name__ == "__main__":
    calculate_f1_from_reports()
