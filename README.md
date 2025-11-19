# madrid-telegram-assistant
Telegram bot assistant for Madrid group (news auto-fetch, job matching, admin tools).

## Project Description
This Telegram bot is designed to help members of a Madrid-based group.  
It automatically fetches news, matches job offers with requests, and provides admin tools for group management.

## Project Structure

your-project/
│
├── backend/
│   ├── __init__.py         # Marks backend as a Python package
│   ├── bot.py              # Main bot logic and Telegram interactions
│   ├── languages.py        # Supported languages and translation utilities
│   ├── news.py             # Functions to fetch and parse news feeds
│   ├── jobs.py             # Functions to handle job offers, requests, and matching
│   ├── requirements.txt    # Python dependencies for the backend
│   └── .env.example         # Template for environment variables
│
├── simplified/
│   ├── __init__.py         # Marks simplified as a Python package
│   ├── post_digest.py      # Functions to generate or process daily/weekly post digests
│   └── schedule.py         # Scheduling tasks (news updates, digests, etc.)
│
├── README.md               # This file
└── .gitignore              # Git ignore rules

## Getting Started

1. Clone the repository:
```bash
git clone <repository_url>
