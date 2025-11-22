from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import logging

from backend.news import format_manual_news
from backend.database import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ունենք հատուկ template_folder
app = Flask(__name__, template_folder="../templates")
app.secret_key = os.environ.get("SECRET_KEY", "default-key")  # Flask-ի session, security
CORS(app)

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Dashboard
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# API: Get news
@app.route('/api/news')
def api_news():
    try:
        news = format_manual_news()
        return jsonify({'success': True, 'news': news})
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# API: Get bot statistics
@app.route('/api/stats')
def api_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total users
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM messages")
        total_users = cursor.fetchone()[0]
        
        # Total messages
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = cursor.fetchone()[0]
        
        # Recent messages
        cursor.execute("""
            SELECT user_id, text, timestamp 
            FROM messages 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        recent_messages = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'total_messages': total_messages,
                'recent_messages': [
                    {
                        'user_id': msg[0],
                        'text': msg[1],
                        'timestamp': msg[2].isoformat() if msg[2] else None
                    }
                    for msg in recent_messages
                ]
            }
        })
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Health check
@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
