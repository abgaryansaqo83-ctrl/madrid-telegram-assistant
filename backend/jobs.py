# backend/jobs.py

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Use absolute path for data files
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_FILE = os.path.join(DATA_DIR, "jobs_db.json")
POSTED_FILE = os.path.join(DATA_DIR, "posted_items.json")

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

def init_db():
    """Initialize database file if it doesn't exist"""
    if not os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump({"offers": [], "requests": []}, f)
            logger.info(f"Created new database file: {DB_FILE}")
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            raise

def load_db():
    """Load database with error handling"""
    try:
        init_db()  # Ensure DB exists
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Validate structure
            if "offers" not in data or "requests" not in data:
                logger.warning("Invalid DB structure, resetting...")
                return {"offers": [], "requests": []}
            return data
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in database: {e}")
        return {"offers": [], "requests": []}
    except Exception as e:
        logger.error(f"Error loading database: {e}")
        return {"offers": [], "requests": []}

def save_db(data):
    """Save database with error handling"""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug("Database saved successfully")
    except Exception as e:
        logger.error(f"Error saving database: {e}")
        raise

def add_offer(user, text):
    """Add job offer"""
    try:
        db = load_db()
        offer = {
            "user": user,
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
        db["offers"].append(offer)
        save_db(db)
        logger.info(f"Offer added by user {user}")
    except Exception as e:
        logger.error(f"Error adding offer: {e}")
        raise

def add_request(user, text):
    """Add job request"""
    try:
        db = load_db()
        request = {
            "user": user,
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
        db["requests"].append(request)
        save_db(db)
        logger.info(f"Request added by user {user}")
    except Exception as e:
        logger.error(f"Error adding request: {e}")
        raise

def find_matches():
    """Find matches between requests and offers"""
    try:
        db = load_db()
        matches = []
        
        for req in db["requests"]:
            for off in db["offers"]:
                # Improved matching logic
                req_words = set(req["text"].lower().split())
                off_words = set(off["text"].lower().split())
                
                # Check if at least 2 words match or significant overlap
                common_words = req_words & off_words
                if len(common_words) >= 2 or (len(common_words) >= 1 and len(req_words) <= 3):
                    matches.append((req, off))
        
        logger.info(f"Found {len(matches)} matches")
        return matches
    except Exception as e:
        logger.error(f"Error finding matches: {e}")
        return []

def get_last_posted_items():
    """Get set of already posted items"""
    try:
        if os.path.exists(POSTED_FILE):
            with open(POSTED_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        return set()
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding posted items: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error loading posted items: {e}")
        return set()

def save_posted_item(key):
    """Save posted item to avoid duplicates"""
    try:
        last = get_last_posted_items()
        last.add(key)
        
        # Keep only last 1000 items to prevent file from growing too large
        if len(last) > 1000:
            last = set(list(last)[-1000:])
        
        with open(POSTED_FILE, "w", encoding="utf-8") as f:
            json.dump(list(last), f, ensure_ascii=False, indent=2)
        logger.debug(f"Saved posted item: {key}")
    except Exception as e:
        logger.error(f"Error saving posted item: {e}")

def clear_old_entries(days=30):
    """Clear entries older than specified days"""
    try:
        db = load_db()
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        # Filter offers
        db["offers"] = [
            o for o in db["offers"] 
            if "timestamp" not in o or datetime.fromisoformat(o["timestamp"]).timestamp() > cutoff
        ]
        
        # Filter requests
        db["requests"] = [
            r for r in db["requests"] 
            if "timestamp" not in r or datetime.fromisoformat(r["timestamp"]).timestamp() > cutoff
        ]
        
        save_db(db)
        logger.info(f"Cleared entries older than {days} days")
    except Exception as e:
        logger.error(f"Error clearing old entries: {e}")

# Initialize database on module import
init_db()
