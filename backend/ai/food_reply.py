import os
import requests

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or "AIzaSyCv2Pum7Uv-EZ2Mocn_RGuwV5qE7cioC-w"

def find_food_place(query, location="Madrid, Spain", max_alternatives=3):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": f"{query} в {location}",
        "key": GOOGLE_API_KEY,
        "type": "restaurant"
    }
    response = requests.get(url, params=params)
    results = response.json().get("results", [])
    if results:
        # Выдаем первый найденный ресторан + список альтернатив
        main = results[0]
        name = main.get("name", "")
        address = main.get("formatted_address", "")
        rating = main.get("rating", "N/A")
        place_url = f"https://www.google.com/maps/search/?api=1&query={address.replace(' ', '+')}"
        # Альтернативные места (до max_alternatives)
        alternatives = []
        for alt in results[1:max_alternatives+1]:
            alt_name = alt.get("name", "")
            alt_addr = alt.get("formatted_address", "")
            alt_rating = alt.get("rating", "N/A")
            alt_link = f"https://www.google.com/maps/search/?api=1&query={alt_addr.replace(' ', '+')}"
            alternatives.append(f"{alt_name}, {alt_addr}, Оценка: {alt_rating}, {alt_link}")
        # Вернуть результат словарем для гибкости вывода
        return {
            "name": name,
            "address": address,
            "rating": rating,
            "url": place_url,
            "alternatives": alternatives
        }
    else:
        # Fallback на русском в стиле ChatGPT/юмора
        return {
            "name": "",
            "address": "",
            "rating": "",
            "alternatives": [],
            "url": "",
            "fallback": (
                "[translate:😥 Ничего подходящего не найдено.\n"
                "Попробуйте другие варианты, например: бургер, паста, хачапури, суши или пицца!\n"
                "Также можете спросить 'где поесть рядом'.]"
            )
        }
