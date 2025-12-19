# backend/ai/bot_ai.py

import os
import httpx

API_KEY = os.getenv("PERPLEXITY_API_KEY")
if not API_KEY:
    raise RuntimeError("PERPLEXITY_API_KEY is not set")

BASE_URL = "https://api.perplexity.ai/chat/completions"


async def ask_city_bot(question: str) -> str:
    """
    Պարզ wrapper Perplexity Sonar API-ի համար.
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        # աշխատող model ID Perplexity-ի docs-ից
        "model": "llama-3.1-sonar-small-128k-chat",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты помощник для жителей и гостей Мадрида. "
                    "Отвечай кратко и по делу, давай конкретные "
                    "рекомендации по городу, еде, транспорту и мероприятиям."
                ),
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        "max_tokens": 300,
        "temperature": 0.3,
        "top_p": 1,
        "presence_penalty": 0,
        "frequency_penalty": 0,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(BASE_URL, headers=headers, json=payload)
        # debugging համար, եթե էլի 400 տա
        if resp.status_code >= 400:
            try:
                print("Perplexity error body:", resp.text)
            except Exception:
                pass
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
