# backend/memory.py

import re
import logging
from collections import Counter
from backend.database import (
    save_conversation, 
    get_user_conversations,
    get_user_preferences,
    update_user_preferences
)

logger = logging.getLogger(__name__)

# Keywords to track
FOOD_KEYWORDS = {
    'ru': ['ресторан', 'кафе', 'еда', 'кухня', 'повар', 'официант', 'пицца', 'суши', 'бургер'],
    'es': ['restaurante', 'cafe', 'comida', 'cocina', 'cocinero', 'camarero', 'pizza', 'sushi'],
    'en': ['restaurant', 'cafe', 'food', 'kitchen', 'cook', 'waiter', 'pizza', 'sushi', 'burger']
}

LOCATION_KEYWORDS = {
    'madrid': ['madrid', 'мадрид'],
    'centro': ['centro', 'центр'],
    'las_tablas': ['las tablas', 'лас таблас'],
    'sanchinarro': ['sanchinarro', 'санчинарро'],
    'fuencarral': ['fuencarral', 'фуэнкарраль'],
    'alcobendas': ['alcobendas', 'алькобендас'],
    'chamartin': ['chamartin', 'chamartín', 'чамартин']
}

WORK_KEYWORDS = {
    'ru': ['работа', 'вакансия', 'ищу работу', 'требуется', 'водитель', 'уборщик'],
    'es': ['trabajo', 'vacante', 'busco trabajo', 'se necesita', 'conductor', 'limpieza'],
    'en': ['job', 'work', 'vacancy', 'looking for', 'driver', 'cleaner']
}

HOUSING_KEYWORDS = {
    'ru': ['квартира', 'дом', 'комната', 'аренда', 'снять', 'сдать'],
    'es': ['piso', 'apartamento', 'casa', 'habitación', 'alquiler', 'alquilar'],
    'en': ['apartment', 'house', 'room', 'rent', 'rental']
}

def extract_keywords(message):
    """Extract relevant keywords from message"""
    message_lower = message.lower()
    keywords = {
        'food': [],
        'locations': [],
        'work': [],
        'housing': []
    }
    
    # Extract food keywords
    for lang, words in FOOD_KEYWORDS.items():
        for word in words:
            if word in message_lower:
                keywords['food'].append(word)
    
    # Extract location keywords
    for location, variants in LOCATION_KEYWORDS.items():
        for variant in variants:
            if variant in message_lower:
                keywords['locations'].append(location)
    
    # Extract work keywords
    for lang, words in WORK_KEYWORDS.items():
        for word in words:
            if word in message_lower:
                keywords['work'].append(word)
    
    # Extract housing keywords
    for lang, words in HOUSING_KEYWORDS.items():
        for word in words:
            if word in message_lower:
                keywords['housing'].append(word)
    
    return keywords

def save_message_with_analysis(telegram_id, message):
    """Save message and extract keywords"""
    keywords = extract_keywords(message)
    save_conversation(telegram_id, message, keywords)
    
    # Update user preferences based on keywords
    update_preferences(telegram_id, keywords)
    
    logger.info(f"Message analyzed for user {telegram_id}: {keywords}")
    return keywords

def update_preferences(telegram_id, new_keywords):
    """Update user preferences based on new keywords"""
    current_prefs = get_user_preferences(telegram_id)
    
    # Initialize if empty
    if not current_prefs:
        current_prefs = {
            'food_interests': [],
            'preferred_locations': [],
            'work_interests': [],
            'housing_interests': []
        }
    
    # Add new keywords (avoid duplicates)
    for category, words in new_keywords.items():
        pref_key = f"{category}_interests" if category != 'locations' else 'preferred_locations'
        if pref_key not in current_prefs:
            current_prefs[pref_key] = []
        
        for word in words:
            if word not in current_prefs[pref_key]:
                current_prefs[pref_key].append(word)
    
    update_user_preferences(telegram_id, current_prefs)

def get_user_profile(telegram_id):
    """Get comprehensive user profile"""
    conversations = get_user_conversations(telegram_id, limit=100)
    preferences = get_user_preferences(telegram_id)
    
    # Analyze conversation patterns
    all_keywords = {
        'food': [],
        'locations': [],
        'work': [],
        'housing': []
    }
    
    for conv in conversations:
        if conv['keywords']:
            for category, words in conv['keywords'].items():
                all_keywords[category].extend(words)
    
    # Count frequency
    profile = {
        'preferences': preferences,
        'top_food_interests': Counter(all_keywords['food']).most_common(5),
        'top_locations': Counter(all_keywords['locations']).most_common(3),
        'work_related': len(all_keywords['work']) > 0,
        'housing_related': len(all_keywords['housing']) > 0,
        'total_conversations': len(conversations)
    }
    
    return profile

def get_recommendations(telegram_id):
    """Generate smart recommendations based on user profile"""
    profile = get_user_profile(telegram_id)
    recommendations = []
    
    # Food recommendations
    if profile['top_food_interests']:
        top_food = profile['top_food_interests'][0][0]
        recommendations.append(f"🍽️ Based on your interest in {top_food}, you might like...")
    
    # Location recommendations
    if profile['top_locations']:
        top_location = profile['top_locations'][0][0]
        recommendations.append(f"📍 You often mention {top_location}. Check out events there!")
    
    # Work recommendations
    if profile['work_related']:
        recommendations.append("💼 New job opportunities match your profile")
    
    # Housing recommendations
    if profile['housing_related']:
        recommendations.append("🏠 New housing options available in your areas")
    
    return recommendations
