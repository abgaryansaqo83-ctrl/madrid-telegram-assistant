# backend/ai/bot_ai.py

import os
import httpx

API_KEY = os.getenv("AI_API_KEY")  # դնում ես քո Perplexity/OpenAI key-ը

BASE_URL = "https://api.perplexity.ai/chat/completions"  # կամ OpenAI URL

async def ask_city_bot(question: str) -> str:
    """
    Հեշտ wrapper, որը հարցն ուղարկում է AI-ին և վերադարձնում 텍ստային պատասխանը.
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sonar-small-chat",  # փոխիր քո մոդելով
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты помощник для жителей и гостей Мадрида. "
                    "Отвечай кратко и по делу, давай конкретные рекомендации "
                    "по городу, еде, транспорту, мероприятиям."
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
