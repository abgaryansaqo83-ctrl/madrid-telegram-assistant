# backend/ai/bot_ai.py

import os
import httpx
import re

API_KEY = os.getenv("PERPLEXITY_API_KEY")
if not API_KEY:
    raise RuntimeError("PERPLEXITY_API_KEY is not set")

BASE_URL = "https://api.perplexity.ai/chat/completions"


async def ask_city_bot(question: str) -> str:
    """
    AI assistant-ը Մադրիդի համար։
    Մաքրում է citation թվերը և կտրում է երկար պատասխանները։
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты локальный бот-помощник для жителей Мадрида. "
                    "Отвечай КРАТКО (максимум 3-4 предложения) на вопросы про Мадрид: "
                    "еда, места, районы, транспорт, мероприятия, быт. "
                    "Если вопрос не про Мадрид — коротко скажи, что ты отвечаешь только про Мадрид."
                ),
            },
            {"role": "user", "content": question},
        ],
        "temperature": 0.7,
        "max_tokens": 200,  # Կրճատել 300-ից 200
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(BASE_URL, headers=headers, json=payload)

        if resp.status_code >= 400:
            print("Perplexity error status:", resp.status_code)
            print("Perplexity error body:", resp.text)

        resp.raise_for_status()
        data = resp.json()
        
        # Վերցնել պատասխանը
        text = data["choices"][0]["message"]["content"].strip()
        
        # Մաքրել citation թվերը [1], [2], [3] և այլն
        text = re.sub(r'\[\d+\]', '', text)
        
        # Հեռացնել ավել բացատները
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Կտրել եթե չափից երկար է (Telegram-ի 4096 char limit-ից շատ փոքր)
        if len(text) > 800:
            text = text[:800] + "..."
        
        return text
