LANG = {
    "ru": {
        "start": "🤖 Мадридский помощник на связи. Что нужно, Сако?",
        "news": "🌇 Новости Мадрида:",
        "offer_saved": "📌 Вакансия добавлена.",
        "request_saved": "🔎 Запрос на работу сохранён.",
        "no_matches": "🤷‍♂️ Соответствий нет.",
        "matches": "🎯 Найденные совпадения:",
    },
    "es": {
        "start": "🤖 Asistente de Madrid en línea. ¿Qué necesitas, Saqo?",
        "news": "🌇 Noticias de Madrid:",
        "offer_saved": "📌 Oferta registrada.",
        "request_saved": "🔎 Solicitud de trabajo guardada.",
        "no_matches": "🤷‍♂️ No hay coincidencias.",
        "matches": "🎯 Coincidencias encontradas:",
    },
    "en": {
        "start": "🤖 Madrid assistant online. What do you need, Saqo?",
        "news": "🌇 Madrid News:",
        "offer_saved": "📌 Job offer saved.",
        "request_saved": "🔎 Job request saved.",
        "no_matches": "🤷‍♂️ No matches.",
        "matches": "🎯 Matches found:",
    }
}

def detect_lang(user_lang):
    if not user_lang:
        return "ru"

    if user_lang.startswith("ru"):
        return "ru"
    if user_lang.startswith("es"):
        return "es"
    if user_lang.startswith("en"):
        return "en"

    return "ru"
