# backend/ai/bot_ai.py

import os
import httpx

API_KEY = os.getenv("PERPLEXITY_API_KEY")
if not API_KEY:
    raise RuntimeError("PERPLEXITY_API_KEY is not set")

BASE_URL = "https://api.perplexity.ai/chat/completions"


async def ask_city_bot(question: str) -> str:
    """
    Պարզ async wrapper Perplexity Sonar chat API-ի համար.
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "sonar",  # նույն մոդելը, ինչ AskYerevan-ում է օգտագործվում
        "messages": [
            {
                "role": "system",
                "content": (
                            "Ты локальный бот-помощник для жителей Мадрида. "
                            "Отвечай ТОЛЬКО на вопросы, связанные с Мадридом: еда, места, районы, "
                            "транспорт, мероприятия, быт. Если вопрос не про Мадрид — коротко скажи, "
                            "что ты отвечаешь только про Мадрид, и предложи переформулировать вопрос."
              ),
            },
            {"role": "user", "content": question},
        ],
        "temperature": 0.7,
        "max_tokens": 300,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(BASE_URL, headers=headers, json=payload)

        if resp.status_code >= 400:
            print("Perplexity error status:", resp.status_code)
            print("Perplexity error body:", resp.text)

        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
