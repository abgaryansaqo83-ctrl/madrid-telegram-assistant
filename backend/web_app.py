from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os
import logging

from backend.news import (
    build_city_overview_message,
    build_cinema_message,
    build_restaurant_message,
    build_holidays_message,
)
from backend.database import get_db_connection, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="../templates")
app.secret_key = os.environ.get("SECRET_KEY", "default-key")
CORS(app)

# Բազայի ինիցիալիզացիա
init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/news")
def api_news():
    try:
        parts: list[str] = []

        overview = build_city_overview_message()
        if overview:
            parts.append(overview)

        cinema = build_cinema_message(max_items=3)
        if cinema:
            parts.append(cinema)

        restaurants = build_restaurant_message(max_items=3)
        if restaurants:
            parts.append(restaurants)

        holidays = build_holidays_message(max_items=3)
        if holidays:
            parts.append(holidays)

        news_text = "\n\n".join(parts) if parts else "Пока нет новостей для Мадрида."
        return jsonify({"success": True, "news": news_text})
    except Exception as e:
        logger.error(f"Error fetching news: {e}", exc_info=True)
        return jsonify({"success": False, "error": "news_unavailable"}), 500


@app.route("/api/stats")
def api_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Total users
        cursor.execute("SELECT COUNT(DISTINCT telegram_id) FROM users")
        total_users = cursor.fetchone()[0]

        # Total messages
        cursor.execute("SELECT COUNT(*) FROM conversations")
        total_messages = cursor.fetchone()[0]

        # Recent messages
        cursor.execute(
            """
            SELECT telegram_id, message, timestamp
            FROM conversations
            ORDER BY timestamp DESC
            LIMIT 10
            """
        )
        recent_messages = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(
            {
                "success": True,
                "stats": {
                    "total_users": total_users,
                    "total_messages": total_messages,
                    "recent_messages": [
                        {
                            "telegram_id": msg[0],
                            "message": msg[1],
                            "timestamp": msg[2],
                        }
                        for msg in recent_messages
                    ],
                },
            }
        )
    except Exception as e:
        logger.error(f"Error fetching stats: {e}", exc_info=True)
        return jsonify({"success": False, "error": "stats_unavailable"}), 500


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
