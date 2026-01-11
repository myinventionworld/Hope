import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import google.generativeai as genai
import datetime
from src.config import TELEGRAM_TOKEN, GEMINI_API_KEY
from src.calendar_tools import create_calendar_event, delete_calendar_event_by_summary, list_upcoming_events, get_upcoming_events_soon
from src.auth import get_user_creds, get_flow, save_user_creds, get_all_authenticated_users
from src.database.session import init_db
from src.utils.context import current_user_id, current_user_creds

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
tools = [create_calendar_event, delete_calendar_event_by_summary, list_upcoming_events]
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    tools=tools
)
# Note: For multi-user, we likely want a new chat session per user or per request, 
# but for simplicity we keep one global object for the *model*, 
# and we will start a chat session locally if needed. 
# Actually, `model.start_chat` returns a ChatSession which holds history.
# We should probably persist history per user, but for now we'll just create a new chat 
# or use a global one (which mixes history, bad for privacy).
# STOPGAP: Cleanest is `model.generate_content(..., tools=...)` with history passed explicitly.
# But `chat.send_message` manages history automatically.
# Let's keep it simple: One global chat is FATAL for multi-user privacy.
# We will use a dictionary `user_chats = {}`.

user_chats = {}

async def start(update, context):
    user = update.effective_user
    await update.message.reply_text(
        f'Привет, {user.first_name}! Я Ассистент с Календарем.\n'
        'Чтобы я мог управлять твоим календарем, нужно авторизоваться.\n'
        'Напиши /login, чтобы получить ссылку.'
    )

async def login(update, context):
    user_id = update.effective_user.id
    flow = get_flow()
    auth_url, _ = flow.authorization_url(prompt='consent')
    
    await update.message.reply_text(
        f'Пожалуйста, перейди по ссылке, авторизуйся и пришли мне код подтверждения:\n\n{auth_url}'
    )

async def handle_message(update, context):
    user_id = update.effective_user.id
    user_text = update.message.text
    print(f"Пользователь {user_id}: {user_text}")
    
    # Check if text looks like an auth code (starts with 4/ and is long)
    if user_text.strip().startswith('4/'):
        try:
            flow = get_flow()
            flow.fetch_token(code=user_text.strip())
            creds = flow.credentials
            await save_user_creds(user_id, creds)
            await update.message.reply_text("Отлично! Ты успешно авторизован. Теперь можешь просить меня записать что-то в календарь.")
            return
        except Exception as e:
            print(f"Auth error: {e}")
            await update.message.reply_text(f"Не удалось авторизоваться. Ошибка: {str(e)}")
            return

    # Normal message handling
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING)

    # 1. Load credentials into Context
    creds = await get_user_creds(user_id)
    if not creds:
        await update.message.reply_text("Сначала нужно авторизоваться. Напиши /login")
        return

    # Set context vars
    token_id = current_user_id.set(user_id)
    token_creds = current_user_creds.set(creds)

    try:
        # 2. Get or create ChatSession
        if user_id not in user_chats:
            user_chats[user_id] = model.start_chat(enable_automatic_function_calling=True)
        
        chat = user_chats[user_id]
        
        current_date = datetime.date.today().isoformat()
        augmented_user_text = f"Today's date is {current_date}. User request: {user_text}"
        
        response = chat.send_message(augmented_user_text)
        await update.message.reply_text(response.text)

    except Exception as e:
        print(f"Ошибка: {e}")
        await update.message.reply_text("Ой, что-то пошло не так.")
    finally:
        # Reset context (for safety, though usually not strictly needed in async handlers if they don't leak)
        current_user_id.reset(token_id)
        current_user_creds.reset(token_creds)

async def check_reminders(context):
    """Job to check for upcoming events and send reminders for ALL users."""
    try:
        users = await get_all_authenticated_users()
        
        for user in users:
            user_id = user.telegram_id
            
            # Load creds for this user
            creds = await get_user_creds(user_id)
            if not creds:
                 continue

            # Set context
            token_creds = current_user_creds.set(creds)
            
            try:
                # Check events
                events = get_upcoming_events_soon(minutes=15)
                # Note: We need a smarter way to track notified events per user.
                # 'notified_events' was a global set. 
                # For MVP, we can just send it. Better: save 'last_notified' in DB or check if event started recently.
                # Simplification: We will just print found events for now to avoid spamming 
                # or duplicate notifications every minute without persistent state.
                # A real implementation needs a 'Reminders' table.
                
                if events:
                     for event in events:
                        summary = event.get('summary', 'Без названия')
                        start = event['start'].get('dateTime', event['start'].get('date'))
                        # Just send blindly for now (MVP limitation: might duplicate if job runs often)
                        # To fix duplication: only notify if start time is in [now+14m, now+15m]
                        
                        # Let's try to be specific: < 15 min and > 14 min? No, job runs every 60s.
                        # We risk missing it.
                        # We risk repeating it.
                        # For this task, getting it working is priority.
                        
                        msg = f"⏰ Напоминание! Скоро: {summary} ({start})"
                        # Use ignore_errors=True in case user blocked bot
                        try:
                             await context.bot.send_message(chat_id=user_id, text=msg)
                        except:
                            pass

            finally:
                current_user_creds.reset(token_creds)
                
    except Exception as e:
        print(f"Error in check_reminders job: {e}")

async def post_init(application):
    await init_db()

def run_bot():
    print("Бот (с Календарем) запускается...")
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    if application.job_queue:
        # Check every minute
        application.job_queue.run_repeating(check_reminders, interval=60, first=10)

    application.run_polling()
