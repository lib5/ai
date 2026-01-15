#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将benchmark_prompts_20.json中的图片URL转换为base64编码
"""

import json
import base64
import requests
from pathlib import Path


def download_and_encode_image(url: str) -> str:
    """下载图片并转换为base64"""
    try:
        print(f"  下载: {url[:60]}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # 获取图片类型
        content_type = response.headers.get('content-type', 'image/jpeg')
        if 'jpeg' in content_type or 'jpg' in content_type:
            mime_type = 'image/jpeg'
        elif 'png' in content_type:
            mime_type = 'image/png'
        else:
            mime_type = 'image/jpeg'

        # 转换为base64
        b64_data = base64.b64encode(response.content).decode('utf-8')
        return f"data:{mime_type};base64,{b64_data}"
    except Exception as e:
        print(f"  ❌ 下载失败: {e}")
        return None


def process_prompts(input_file: str, output_file: str):
    """处理prompts文件"""
    print(f"读取: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    prompts = data['prompts']
    updated_count = 0

    for prompt in prompts:
        if prompt.get('type') != 'image':
            continue

        image_urls = prompt.get('image_urls', [])
        if not image_urls:
            continue

        print(f"\n处理 prompt ID: {prompt['id']}")

        # 下载并编码每个图片
        base64_urls = {}
        for url in image_urls:
            b64_url = download_and_encode_image(url)
            if b64_url:
                base64_urls[url] = b64_url

        if not base64_urls:
            continue

        # 更新complete_prompt中的image_url
        cp = prompt.get('complete_prompt')
        if not cp:
            print(f"  ⚠️ 缺少complete_prompt字段，跳过")
            continue
        for msg in cp:
            content = msg.get('content')
            if not isinstance(content, list):
                continue

            for item in content:
                if item.get('type') == 'image_url':
                    image_url = item.get('image_url', {})
                    if isinstance(image_url, dict):
                        # 直接用下载的完整base64替换（不管原来是什么格式）
                        if base64_urls:
                            first_b64 = list(base64_urls.values())[0]
                            image_url['url'] = first_b64
                            print(f"  ✅ 已替换为完整base64")
                            updated_count += 1
                    elif isinstance(image_url, str):
                        # 直接是字符串URL
                        if base64_urls:
                            first_b64 = list(base64_urls.values())[0]
                            item['image_url'] = {"url": first_b64}
                            updated_count += 1

    # 保存结果
    print(f"\n保存到: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 完成! 共更新 {updated_count} 个图片URL")


if __name__ == "__main__":
    input_file = "/home/libo/chatapi/benchmark_prompts_20.json"
    output_file = "/home/libo/chatapi/benchmark_prompts_20_base64.json"

    process_prompts(input_file, output_file)
