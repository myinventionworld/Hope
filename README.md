# Hope - AI Calendar Assistant 🤖📅

> Named after "Надежда" (Hope) - your reliable AI assistant for managing calendar events through natural language in Telegram.

## 📋 Project Structure

```
hope-calendar-bot/
├── .env.example              # Environment variables template
├── .gitignore               
├── README.md                
├── requirements.txt          # Python dependencies
├── docker-compose.yml        # Optional: for containerized deployment
│
├── config/
│   ├── __init__.py
│   ├── settings.py          # Configuration management
│   └── prompts.py           # LLM prompts for event parsing
│
├── src/
│   ├── __init__.py
│   │
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── handlers.py      # Telegram message handlers
│   │   ├── keyboards.py     # Inline keyboards for confirmations
│   │   └── states.py        # Conversation states
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── parser.py        # LLM event parsing logic
│   │   └── validator.py     # Validate parsed data
│   │
│   ├── calendar/
│   │   ├── __init__.py
│   │   ├── google_api.py    # Google Calendar integration
│   │   └── event_builder.py # Build calendar events
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py        # SQLAlchemy models
│   │   └── crud.py          # Database operations
│   │
│   └── utils/
│       ├── __init__.py
│       ├── datetime_utils.py # Date/time parsing helpers
│       └── logger.py         # Logging configuration
│
├── data/
│   └── hope.db              # SQLite database (gitignored)
│
├── credentials/
│   └── .gitkeep             # Google OAuth credentials (gitignored)
│
├── tests/
│   ├── __init__.py
│   ├── test_llm_parser.py
│   ├── test_calendar.py
│   └── test_handlers.py
│
└── main.py                  # Entry point
```

## 🚀 Features

- **Natural Language Processing**: Write events in plain Russian/English
- **Smart Date/Time Recognition**: "завтра утром", "в пятницу в 15:00"
- **Google Calendar Integration**: Direct sync with your calendar
- **Confirmation Flow**: Review before creating events
- **Multi-user Support**: Each user has their own Google Calendar connection

## 📦 Installation

### Prerequisites
- Python 3.10+
- Telegram Bot Token (from @BotFather)
- OpenAI API Key (or local LLM setup)
- Google Cloud Project with Calendar API enabled

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/hope-calendar-bot.git
cd hope-calendar-bot
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. **Set up Google Calendar API**
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Create a new project
- Enable Google Calendar API
- Create OAuth 2.0 credentials (Desktop app)
- Download `credentials.json` to `credentials/` folder

6. **Run the bot**
```bash
python main.py
```

## 🔧 Configuration

Edit `.env` file:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# OpenAI (or other LLM)
OPENAI_API_KEY=your_openai_key_here
LLM_MODEL=gpt-4-turbo-preview

# Database
DATABASE_URL=sqlite:///data/hope.db

# Google Calendar
GOOGLE_CREDENTIALS_PATH=credentials/credentials.json

# Timezone
DEFAULT_TIMEZONE=Europe/Prague
```

## 💬 Usage Examples

**Simple event:**
```
User: Завтра в 10 утра встреча с командой
Hope: 📅 Создать событие?
      Встреча с командой
      🕐 24 октября 2025, 10:00
      [✅ Создать] [❌ Отмена]
```

**With duration:**
```
User: Позаниматься спортом завтра утром 1 час
Hope: 📅 Создать событие?
      Позаниматься спортом
      🕐 24 октября 2025, 09:00 - 10:00
      [✅ Создать] [❌ Отмена]
```

**Recurring event:**
```
User: Каждый понедельник в 18:00 йога
Hope: 📅 Создать повторяющееся событие?
      Йога
      🕐 Каждый понедельник, 18:00
      [✅ Создать] [❌ Отмена]
```

## 🗺️ Roadmap

### MVP (Current Phase)
- [x] Project structure
- [ ] Basic Telegram bot
- [ ] OpenAI event parsing
- [ ] Google Calendar integration
- [ ] User authentication flow
- [ ] Event confirmation UI

### Future Features
- [ ] Voice message support (STT → LLM)
- [ ] Event editing/deletion
- [ ] Smart reminders
- [ ] Recurring events
- [ ] Multi-language support
- [ ] Local LLM option (Llama 3)
- [ ] Calendar view in Telegram
- [ ] Timezone management

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_llm_parser.py

# With coverage
pytest --cov=src tests/
```

## 📄 License

MIT License - feel free to use for personal or commercial projects

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🙏 Acknowledgments

Named after "Надежда" (Hope) - because everyone needs a reliable assistant they can count on.

---
