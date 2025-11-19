# backend/matching.py

import re
import logging
from backend.database import get_connection
from collections import defaultdict

logger = logging.getLogger(__name__)

def parse_housing_offer(text):
    """
    Parse housing offer details from message
    
    Expected format:
    Apartment/house/room in location, price, rooms
    
    Example: "Квартира 1000€, 2 комнаты, Centro"
    """
    
    text_lower = text.lower()
    
    # Extract price (euros)
    price_match = re.search(r'(\d+)\s*€', text)
    price = int(price_match.group(1)) if price_match else None
    
    # Extract rooms
    rooms_match = re.search(r'(\d+)\s*(?:комнат|комнаты|room|habitación)', text_lower)
    rooms = int(rooms_match.group(1)) if rooms_match else None
    
    # Extract type
    housing_type = None
    if 'квартира' in text_lower or 'piso' in text_lower or 'apartment' in text_lower:
        housing_type = 'apartment'
    elif 'дом' in text_lower or 'casa' in text_lower or 'house' in text_lower:
        housing_type = 'house'
    elif 'комната' in text_lower or 'habitación' in text_lower or 'room' in text_lower:
        housing_type = 'room'
    
    # Extract location (simple version)
    locations = ['madrid', 'centro', 'las tablas', 'sanchinarro', 'fuencarral', 'alcobendas', 'chamartín']
    location = None
    for loc in locations:
        if loc in text_lower:
            location = loc
            break
    
    return {
        'type': housing_type,
        'price': price,
        'rooms': rooms,
        'location': location,
        'text': text
    }

def find_matching_requests(offer_data):
    """
    Find all housing requests that match this offer
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    matches = []
    
    try:
        # Query for housing requests with similar parameters
        query = "SELECT telegram_id, description, created_at FROM conversations WHERE "
        conditions = []
        params = []
        
        # Match by location
        if offer_data['location']:
            conditions.append("message LIKE ?")
            params.append(f"%{offer_data['location']}%")
        
        # Match by housing keyword
        conditions.append("message LIKE ?")
        params.append("%квартира%")
        
        if conditions:
            query += " AND ".join(conditions)
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            for user_id, message, timestamp in results:
                matches.append({
                    'user_id': user_id,
                    'message': message,
                    'timestamp': timestamp
                })
        
        logger.info(f"Found {len(matches)} matching requests for offer")
        return matches
    
    except Exception as e:
        logger.error(f"Error finding matches: {e}")
        return []
    
    finally:
        conn.close()

def find_matching_offers(request_data):
    """
    Find all housing offers that match this request
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    matches = []
    
    try:
        # Query for housing offers
        query = "SELECT telegram_id, message, created_at FROM conversations WHERE "
        conditions = []
        params = []
        
        # Match by location
        if request_data['location']:
            conditions.append("message LIKE ?")
            params.append(f"%{request_data['location']}%")
        
        # Match by housing keyword
        conditions.append("message LIKE ?")
        params.append("%сдается%")
        
        if conditions:
            query += " AND ".join(conditions)
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            for user_id, message, timestamp in results:
                matches.append({
                    'user_id': user_id,
                    'message': message,
                    'timestamp': timestamp
                })
        
        logger.info(f"Found {len(matches)} matching offers for request")
        return matches
    
    except Exception as e:
        logger.error(f"Error finding matches: {e}")
        return []
    
    finally:
        conn.close()

def is_housing_offer(text):
    """Check if message is a housing offer"""
    text_lower = text.lower()
    offer_keywords = ['сдается', 'сдаю', 'предлагаю', 'offering', 'se alquila', 'alquilo']
    return any(keyword in text_lower for keyword in offer_keywords)

def is_housing_request(text):
    """Check if message is a housing request"""
    text_lower = text.lower()
    request_keywords = ['ищу', 'ищем', 'looking for', 'busco', 'arrendamos', 'нужна']
    return any(keyword in text_lower for keyword in request_keywords)
