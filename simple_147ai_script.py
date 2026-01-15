import http.client
import json
import time
import base64
import requests

# 1. 将图片文件编码为Base64字符串
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# 本地图片路径
image_path = "/Users/xiejiayu/Desktop/头像照片.jpg"

# 获取Base64字符串
base64_image = encode_image(image_path)


def generate():
    base_url = "wsa.147ai.cn"
    api_key = "sk-i1OxltYB6g1sc4WFeLeqg088af7tDhiWFBrqbyvlDB30hmKF"
    model = "gemini-3-flash-preview-low"

    # 记录开始时间
    start_time = time.time()
    first_token_time = None
    total_tokens = 0
    has_started_output = False

    print("开始生成...", flush=True)

    # 构建请求数据
    # 注意：147ai可能使用不同的流式配置方式
    # 如果流式不工作，请尝试：
    # 1. 移除 generationConfig.stream
    # 2. 或使用 stream=True（而非stream: True）
    # 3. 或添加不同的流式参数x
    payload = json.dumps({
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"type": "text", "text": "描述一下这个图片"},
                    {
                        "inline_data": {
                            "mimeType": "image/png",
                            "data": f"{base64_image}"
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "thinkingConfig": {
                "thinkingBudget": 1
            }
        }
    })

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    conn = http.client.HTTPSConnection(base_url)

    try:
        # 发送请求
        conn.request("POST", f"/v1beta/models/{model}:generateContent", payload, headers)
        res = conn.getresponse()

        # 处理流式响应
        buffer = ""

        while True:
            chunk = res.read(1024)
            if not chunk:
                break

            try:
                chunk_text = chunk.decode('utf-8')
                buffer += chunk_text

                # 按行分割处理
                lines = buffer.split('\n')
                buffer = lines[-1]  # 保留最后一行（可能不完整）

                for line in lines[:-1]:
                    line = line.strip()
                    if not line:
                        continue

                    # 处理SSE格式
                    if line.startswith('data: '):
                        line = line[6:]

                    # 跳过[DONE]标记
                    if line == '[DONE]':
                        continue

                    # 尝试解析JSON
                    if line:
                        try:
                            data = json.loads(line)

                            # 提取生成的内容
                            if 'candidates' in data and len(data['candidates']) > 0:
                                candidate = data['candidates'][0]
                                if 'content' in candidate and 'parts' in candidate['content']:
                                    content_parts = candidate['content']['parts']

                                    for part in content_parts:
                                        if 'text' in part:
                                            chunk_text = part['text']

                                            # 记录首token返回时间
                                            if not has_started_output and chunk_text.strip():
                                                first_token_time = time.time()
                                                has_started_output = True
                                                first_token_latency = (first_token_time - start_time) * 1000
                                                print(f"\n首token延迟: {first_token_latency:.2f}ms", flush=True)

                                            # 统计token数
                                            total_tokens += len(chunk_text)
                                            print(chunk_text, end="")

                        except json.JSONDecodeError:
                            # 忽略无法解析的行
                            pass

            except UnicodeDecodeError:
                continue

        # 处理缓冲区中剩余的数据
        if buffer.strip():
            buffer = buffer.strip()
            if buffer.startswith('data: '):
                buffer = buffer[6:]
            if buffer and buffer != '[DONE]':
                try:
                    data = json.loads(buffer)
                    if 'candidates' in data and len(data['candidates']) > 0:
                        candidate = data['candidates'][0]
                        if 'content' in candidate and 'parts' in candidate['content']:
                            content_parts = candidate['content']['parts']
                            for part in content_parts:
                                if 'text' in part:
                                    chunk_text = part['text']
                                    if not has_started_output and chunk_text.strip():
                                        first_token_time = time.time()
                                        has_started_output = True
                                        first_token_latency = (first_token_time - start_time) * 1000
                                        print(f"\n首token延迟: {first_token_latency:.2f}ms", flush=True)
                                    total_tokens += len(chunk_text)
                                    print(chunk_text, end="")
                except json.JSONDecodeError:
                    pass

    except Exception as e:
        print(f"请求失败: {e}")

    finally:
        conn.close()

    # 计算总时间和token每秒
    end_time = time.time()
    total_time = end_time - start_time

    if total_time > 0:
        tokens_per_second = total_tokens / total_time
    else:
        tokens_per_second = 0

    print(f"\n\n=== 统计信息 ===")
    print(f"总耗时: {total_time:.2f}秒")
    print(f"总token数: {total_tokens}")
    print(f"Token每秒: {tokens_per_second:.2f}")
    print(f"首token延迟: {((first_token_time - start_time) * 1000):.2f}ms" if first_token_time else "N/A")

generate()