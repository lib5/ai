#!/usr/bin/env python3
"""展示响应格式"""

import asyncio
import aiohttp
import json

async def show_response():
    request_data = {
        "user_id": "demo",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "hello"}
                ]
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:8000/api/chat", json=request_data) as response:
            full_data = ""
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    try:
                        event = json.loads(line[6:])
                        if event.get('event') == 'chunk' and 'data' in event:
                            full_data += event['data']
                    except:
                        pass

            result = json.loads(full_data)
            print("响应格式:")
            print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(show_response())
