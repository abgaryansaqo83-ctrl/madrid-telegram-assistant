## Project Structure

```
madrid-telegram-assistant/
├── backend/
│   ├── __init__.py
│   ├── ai/
│   │   ├── food_reply.py
│   │   ├── response.py
│   │   └── traffic.py
│   ├── bot.py
│   ├── database.py
│   ├── jobs.py
│   ├── languages.py
│   ├── matching.py
│   ├── memory.py
│   ├── news.py
│   ├── scheduler.py
│   ├── web_app.py
│   └── requirements.txt
├── simplified/
│   ├── __init__.py
│   └── post_digest.py
├── templates/
│   ├── dashboard.html
│   └── index.html
├── data/
│   └── .gitkeep
├── .env
├── .env.example
├── .gitignore
├── Procfile
├── render.yaml
├── requirements.txt
├── runtime.txt
└── README.md

```

## Installation

### 1. Clone Repository

```
git clone https://github.com/yourusername/madrid-telegram-assistant.git
cd madrid-telegram-assistant
```

### 2. Install Dependencies

```
pip install -r backend/requirements.txt
```

### 3. Configure Environment

```
cp .env.example .env
# Edit .env with your credentials
```

### 4. Create Data Directory

```
mkdir -p data
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```
BOT_TOKEN=8281034149:AAGVPUqGbVAq0eefiY_2HEbqzEM21_k-hTk
CHAT_ID=-1003433432009
DIGEST_INTERVAL=30
SCHEDULER_TYPE=interval
```

## Usage

### Run Bot Only

```
python -m backend.bot
```

### Run Scheduler Only

```
python -m backend.scheduler
```

## Bot Commands

- `/start` - Start the bot
- `/news` - Get latest Madrid news
- `/offer [text]` - Post a job offer
- `/request [text]` - Post a job request
- `/match` - Find job matches
- `/help` - Show help message

## Deployment on Render

See [Render Deployment Guide](https://render.com/docs) for full instructions.

## License

MIT License
