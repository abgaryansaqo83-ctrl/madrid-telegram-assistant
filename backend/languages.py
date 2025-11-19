# backend/languages.py

import logging

logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LANGUAGES = ["ru", "es", "en", "hy"]
DEFAULT_LANGUAGE = "ru"

# Language strings for bot responses
LANG = {
    "ru": {
        "start": "🤖 Мадридский помощник на связи. Что нужно, Сако?",
        "news": "🌇 Новости Мадрида:",
        "offer_saved": "📌 Вакансия добавлена.",
        "request_saved": "🔎 Запрос на работу сохранён.",
        "no_matches": "🤷‍♂️ Соответствий нет.",
        "matches": "🎯 Найденные совпадения:",
        "no_news": "📭 Нет доступных новостей.",
        "empty_offer": "⚠️ Пожалуйста, укажите детали вакансии.",
        "empty_request": "⚠️ Пожалуйста, укажите детали запроса.",
        "error": "❌ Произошла ошибка. Попробуйте позже.",
        "help": """
🤖 **Доступные команды:**

/start - Запустить бота
/news - Новости Мадрида
/offer [текст] - Разместить вакансию
/request [текст] - Разместить запрос на работу
/match - Найти совпадения
/help - Показать эту справку

**Примеры:**
/offer Требуется повар в ресторан
/request Ищу работу водителем
        """
    },
    "es": {
        "start": "🤖 Asistente de Madrid en línea. ¿Qué necesitas, Saqo?",
        "news": "🌇 Noticias de Madrid:",
        "offer_saved": "📌 Oferta registrada.",
        "request_saved": "🔎 Solicitud de trabajo guardada.",
        "no_matches": "🤷‍♂️ No hay coincidencias.",
        "matches": "🎯 Coincidencias encontradas:",
        "no_news": "📭 No hay noticias disponibles.",
        "empty_offer": "⚠️ Por favor, proporcione detalles de la oferta.",
        "empty_request": "⚠️ Por favor, proporcione detalles de la solicitud.",
        "error": "❌ Ocurrió un error. Inténtelo más tarde.",
        "help": """
🤖 **Comandos disponibles:**

/start - Iniciar el bot
/news - Noticias de Madrid
/offer [texto] - Publicar oferta de trabajo
/request [texto] - Publicar solicitud de trabajo
/match - Encontrar coincidencias
/help - Mostrar esta ayuda

**Ejemplos:**
/offer Se necesita cocinero en restaurante
/request Busco trabajo como conductor
        """
    },
    "en": {
        "start": "🤖 Madrid assistant online. What do you need, Saqo?",
        "news": "🌇 Madrid News:",
        "offer_saved": "📌 Job offer saved.",
        "request_saved": "🔎 Job request saved.",
        "no_matches": "🤷‍♂️ No matches.",
        "matches": "🎯 Matches found:",
        "no_news": "📭 No news available.",
        "empty_offer": "⚠️ Please provide offer details.",
        "empty_request": "⚠️ Please provide request details.",
        "error": "❌ An error occurred. Please try again later.",
        "help": """
🤖 **Available commands:**

/start - Start the bot
/news - Madrid news
/offer [text] - Post job offer
/request [text] - Post job request
/match - Find matches
/help - Show this help

**Examples:**
/offer Chef needed at restaurant
/request Looking for driver job
        """
    },
    "hy": {
        "start": "🤖 Մադրիդի օգնական
