import json
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "jobs_db.json")

# Creates DB if it does not exist
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({"offers": [], "requests": []}, f)

def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"offers": [], "requests": []}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_offer(user, text):
    db = load_db()
    db["offers"].append({"user": user, "text": text})
    save_db(db)

def add_request(user, text):
    db = load_db()
    db["requests"].append({"user": user, "text": text})
    save_db(db)

def find_matches():
    db = load_db()
    matches = []
    
    for req in db["requests"]:
        req_words = req["text"].lower().split()
        for off in db["offers"]:
            if any(w in off["text"].lower() for w in req_words):
                matches.append((req, off))

    return matches
