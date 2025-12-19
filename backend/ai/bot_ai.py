# backend/ai/bot_ai.py

import os
import httpx

API_KEY = os.getenv("PERPLEXITY_API_KEY")  # ← փոխած տարբերակ

if not API_KEY:
    raise RuntimeError("PERPLEXITY_API_KEY is not set")

BASE_URL = "https://api.perplexity.ai/chat/completions"


async def ask_city_bot(question: str) -> str:
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sonar-small-chat",  # կամ ով որ օգտագործում ես
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты помощник для жителей и гостей Мадрида. "
                    "Отвечай кратко и по делу, давай конкретные рекомендации "
                    "по городу, еде, транспорту и мероприятиям."
                ),
            },
            {"role": "user", "content": question},
        ],
        "max_tokens": 300,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(BASE_URL, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
