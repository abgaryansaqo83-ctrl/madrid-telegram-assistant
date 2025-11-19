# backend/database.py

import sqlite3
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DB_PATH = "data/bot.db"

def init_db():
    """Initialize database with all tables"""
    os.makedirs("data", exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            language TEXT DEFAULT 'ru',
            preferences TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Conversations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            keywords TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Job offers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            title TEXT,
            description TEXT NOT NULL,
            category TEXT,
            location TEXT,
            salary TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Job requests
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            title TEXT,
            description TEXT NOT NULL,
            category TEXT,
            location TEXT,
            expected_salary TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

def get_connection():
    """Get database connection"""
    return sqlite3.connect(DB_PATH)

def save_user(telegram_id, username=None, language='ru'):
    """Save or update user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO users (telegram_id, username, language)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                language = excluded.language
        """, (telegram_id, username, language))
        
        conn.commit()
        logger.info(f"User {telegram_id} saved")
    except Exception as e:
        logger.error(f"Error saving user: {e}")
    finally:
        conn.close()

def save_conversation(telegram_id, message, keywords=None):
    """Save conversation message"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO conversations (telegram_id, message, keywords)
            VALUES (?, ?, ?)
        """, (telegram_id, message, json.dumps(keywords) if keywords else None))
        
        conn.commit()
        logger.info(f"Conversation saved for user {telegram_id}")
    except Exception as e:
        logger.error(f"Error saving conversation: {e}")
    finally:
        conn.close()

def get_user_conversations(telegram_id, limit=50):
    """Get recent conversations for a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT message, keywords, timestamp
            FROM conversations
            WHERE telegram_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (telegram_id, limit))
        
        conversations = cursor.fetchall()
        return [
            {
                'message': row[0],
                'keywords': json.loads(row[1]) if row[1] else [],
                'timestamp': row[2]
            }
            for row in conversations
        ]
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        return []
    finally:
        conn.close()

def update_user_preferences(telegram_id, preferences):
    """Update user preferences (JSON)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE users
            SET preferences = ?
            WHERE telegram_id = ?
        """, (json.dumps(preferences), telegram_id))
        
        conn.commit()
        logger.info(f"Preferences updated for user {telegram_id}")
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
    finally:
        conn.close()

def get_user_preferences(telegram_id):
    """Get user preferences"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT preferences
            FROM users
            WHERE telegram_id = ?
        """, (telegram_id,))
        
        result = cursor.fetchone()
        if result and result[0]:
            return json.loads(result[0])
        return {}
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        return {}
    finally:
        conn.close()
