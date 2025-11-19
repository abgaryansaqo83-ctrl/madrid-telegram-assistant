# backend/languages.py

import logging

logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LANGUAGES = ["ru", "es", "en"]
DEFAULT_LANGUAGE = "ru"

# Language strings for bot responses
LANG = {
    "ru": {
        "start": "🤖 Мадридский помощник на связи. Чем помочь?",
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
/help - Показать эту справку
        """
    },
    "es": {
        "start": "🤖 Asistente de Madrid en línea. ¿En qué puedo ayudar?",
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
/help - Mostrar esta ayuda
        """
    },
    "en": {
        "start": "🤖 Madrid assistant online. How can I help?",
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
/help - Show this help
        """
    }
}

def detect_lang(user_lang: str = None) -> str:
    """
    Detect user's language from Telegram language code
    
    Args:
        user_lang: Telegram language code (e.g., 'ru', 'es-ES', 'en-US')
        
    Returns:
        Supported language code ('ru', 'es', 'en')
    """
    if not user_lang:
        logger.debug(f"No language provided, using default: {DEFAULT_LANGUAGE}")
        return DEFAULT_LANGUAGE
    
    # Normalize to lowercase
    user_lang = user_lang.lower()
    
    # Check exact match first
    if user_lang in SUPPORTED_LANGUAGES:
        logger.debug(f"Exact language match: {user_lang}")
        return user_lang
    
    # Check language prefix (e.g., 'es-ES' -> 'es')
    for lang in SUPPORTED_LANGUAGES:
        if user_lang.startswith(lang):
            logger.debug(f"Language prefix match: {user_lang} -> {lang}")
            return lang
    
    # Default fallback
    logger.debug(f"No match for '{user_lang}', using default: {DEFAULT_LANGUAGE}")
    return DEFAULT_LANGUAGE

def get_text(lang: str, key: str, default: str = None) -> str:
    """
    Get localized text for a given language and key
    
    Args:
        lang: Language code
        key: Text key
        default: Default text if key not found
        
    Returns:
        Localized text or default
    """
    try:
        return LANG.get(lang, LANG[DEFAULT_LANGUAGE]).get(key, default or f"Missing: {key}")
    except Exception as e:
        logger.error(f"Error getting text for lang={lang}, key={key}: {e}")
        return default or f"Error: {key}"

def get_available_languages() -> list:
    """
    Get list of available language codes
    
    Returns:
        List of language codes
    """
    return SUPPORTED_LANGUAGES.copy()

def is_language_supported(lang: str) -> bool:
    """
    Check if a language is supported
    
    Args:
        lang: Language code
        
    Returns:
        True if supported, False otherwise
    """
    return lang in SUPPORTED_LANGUAGES
