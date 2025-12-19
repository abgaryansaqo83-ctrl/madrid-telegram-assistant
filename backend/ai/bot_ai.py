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
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты помощник для жителей и гостей Мадрида. "
                    "Отвечай кратко и по делу, давай конкретные рекомендации "
                    "по городу, еде, транспорту и мероприятиям."
                ),
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        "max_tokens": 300,
        "temperature": 0.3,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(BASE_URL, headers=headers, json=payload)

        # debug Perplexity errors
        if resp.status_code >= 400:
            print("Perplexity error status:", resp.status_code)
            print("Perplexity error body:", resp.text)

        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
