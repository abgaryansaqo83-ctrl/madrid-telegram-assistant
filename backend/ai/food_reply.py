import os
import requests

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or "AIzaSyCv2Pum7Uv-EZ2Mocn_RGuwV5qE7cioC-w"

def find_food_place(query, location="Madrid, Spain"):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": f"{query} в {location}",
        "key": GOOGLE_API_KEY,
        "type": "restaurant"
    }
    response = requests.get(url, params=params)
    results = response.json().get("results", [])
    if results:
        place = results[0]
        name = place.get("name", "")
        address = place.get("formatted_address", "")
        rating = place.get("rating", "N/A")
        return f"Ресторан: {name}\nАдрес: {address}\nОценка: {rating}"
    else:
        return "Ничего подходящего не найдено."
