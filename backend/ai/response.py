# backend/ai/response.py

import threading
import time

# Главный контроллер для unanswered вопросов и их auto-response (русский комментарий)

class QuestionAutoResponder:
    def __init__(self, timeout=300):
        self.pending_questions = {}  # {question_id: (user_id, message, timestamp)}
        self.timeout = timeout      # timeout секунд ожидания (например, 300 = 5 минут)

    def add_question(self, user_id, message, question_id, search_type="food"):
        now = time.time()
        self.pending_questions[question_id] = (user_id, message, now, search_type)
        threading.Thread(target=self._wait_and_respond, args=(question_id,)).start()

    def mark_answered(self, question_id):
        if question_id in self.pending_questions:
            del self.pending_questions[question_id]

    def _wait_and_respond(self, question_id):
        user_id, message, ts, search_type = self.pending_questions[question_id]
        time.sleep(self.timeout)
        if question_id in self.pending_questions:
            # Вызываем нужный search-функционал по типу
            if search_type == "food":
                from backend.ai.food_reply import find_food_place
                result = find_food_place(message)
            elif search_type == "item":
                from backend.ai.item_match import find_item_offer
                result = find_item_offer(message)
            elif search_type == "weather":
                from backend.ai.weather_morning import get_weather_forecast
                result = get_weather_forecast()
            elif search_type == "traffic":
                from backend.ai.traffic import get_traffic_status
                result = get_traffic_status()
            else:
                result = "Не могу найти результат по вашему запросу."

            reply = f"Автоответ:\n{result}"
            send_telegram_message(user_id, reply)
            self.mark_answered(question_id)

def send_telegram_message(user_id, text):
    # Здесь бот отправляет сообщение через aiogram/bot.send_message
    pass
