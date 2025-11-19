import json
import os

DB_FILE = "jobs_db.json"

if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({"offers": [], "requests": []}, f)

def load_db():
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

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
        for off in db["offers"]:
            if any(w in off["text"].lower() for w in req["text"].lower().split()):
                matches.append((req, off))

    return matches

def get_last_posted_items():
    if os.path.exists("posted_items.json"):
        with open("posted_items.json", "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_posted_item(key):
    last = get_last_posted_items()
    last.add(key)
    with open("posted_items.json", "w", encoding="utf-8") as f:
        json.dump(list(last), f, ensure_ascii=False, indent=2)
