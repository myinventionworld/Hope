import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import google.generativeai as genai
import datetime
from datetime import date
from src.config import TELEGRAM_TOKEN, GEMINI_API_KEY
from src.calendar_tools import create_calendar_event, delete_calendar_event_by_summary, list_upcoming_events, get_upcoming_events_soon, get_events_for_date
from src.auth import get_user_creds, get_flow, save_user_creds, get_all_authenticated_users
from src.database.session import init_db
from src.utils.context import current_user_id, current_user_creds
from src.ui.calendar_keyboard import create_calendar, parse_callback_data

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
tools = [create_calendar_event, delete_calendar_event_by_summary, list_upcoming_events]
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    tools=tools,
    system_instruction=(
        "You are Hope, a helpful Google Calendar Assistant. "
        "Your ONLY purpose is to manage the user's calendar (add, delete, list events) "
        "and answer questions strictly related to their schedule or time management. "
        "If a user asks about anything else (e.g. general knowledge, translation, coding, math), "
        "politely refuse and remind them that you can only help with the calendar."
    )
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
        f'Привет, {user.first_name}! 👋\n\n'
        'Я **Hope** — твой умный ассистент с Календарем. 🤖📅\n\n'
        '**Что я умею:**\n'
        '🔹 Записывать события в Google Calendar ("Запиши к врачу завтра в 10")\n'
        '🔹 Напоминать о встречах за 15 минут\n'
        '🔹 Удалять события ("Удали встречу с врачом")\n'
        '🔹 Показывать твой график\n\n'
        '**С чего начать:**\n'
        '1. Напиши /login чтобы авторизоваться в Google.\n'
        '2. Затем просто пиши мне, что нужно сделать!',
        parse_mode='Markdown'
    )

async def help_command(update, context):
    await update.message.reply_text(
        '**Справка по командам:** ℹ️\n\n'
        '/start — Перезапустить бота\n'
        '/login — Авторизация в Google Calendar\n'
        '/events — Показать ближайшие события\n'
        '/status — Проверить статус подключения\n'
        '/help — Показать это сообщение\n\n'
        '**Примеры запросов:**\n'
        '— "Запиши тренировку в четверг в 19:00 на 1.5 часа"\n'
        '— "Какие планы на завтра?"\n'
        '— "Удали обед с коллегами"',
        parse_mode='Markdown'
    )

async def events_command(update, context):
    """Explicitly list upcoming events via command."""
    user_id = update.effective_user.id
    creds = await get_user_creds(user_id)
    if not creds:
        await update.message.reply_text("Сначала нужно авторизоваться. Напиши /login")
        return
    
    # Store in context for the tool function
    token_creds = current_user_creds.set(creds)
    try:
        events_text = list_upcoming_events(max_results=10)
        await update.message.reply_text(events_text)
    except Exception as e:
        await update.message.reply_text(f"Ошибка получения событий: {e}")
    finally:
        current_user_creds.reset(token_creds)

async def status_command(update, context):
    user_id = update.effective_user.id
    creds = await get_user_creds(user_id)
    
    if creds and creds.valid:
        await update.message.reply_text("✅ **Статус**: Авторизован в Google Calendar.", parse_mode='Markdown')
    elif creds:
        await update.message.reply_text("⚠️ **Статус**: Требуется обновление токена (попробуйте сделать запрос).", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ **Статус**: Не авторизован. Используйте /login.", parse_mode='Markdown')

async def calendar_command(update, context):
    """Show interactive calendar keyboard."""
    user_id = update.effective_user.id
    creds = await get_user_creds(user_id)
    if not creds:
        await update.message.reply_text("⛔️ Сначала нужно авторизоваться. Напиши /login")
        return
    
    await update.message.reply_text(
        "📅 Выберите дату:",
        reply_markup=create_calendar()
    )

async def calendar_callback(update, context):
    """Handle calendar button presses."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    creds = await get_user_creds(user_id)
    if not creds:
        await query.edit_message_text("⛔️ Сначала нужно авторизоваться. Напиши /login")
        return
    
    data = parse_callback_data(query.data)
    action = data["action"]
    year = data["year"]
    month = data["month"]
    day = data["day"]
    
    if action == "IGNORE":
        return
    
    if action in ("PREV", "NEXT", "TODAY"):
        # Update the calendar view
        await query.edit_message_text(
            "📅 Выберите дату:",
            reply_markup=create_calendar(year, month)
        )
        return
    
    if action == "DAY":
        # Fetch events for that day
        token_creds = current_user_creds.set(creds)
        try:
            target_date = date(year, month, day)
            events_text = get_events_for_date(target_date)
            await query.edit_message_text(events_text)
        finally:
            current_user_creds.reset(token_creds)

async def login(update, context):
    user_id = update.effective_user.id
    flow = get_flow()
    auth_url, _ = flow.authorization_url(prompt='consent')
    
    await update.message.reply_text(
        f'🔗 **Авторизация**\n\n'
        f'Перейди по ссылке, авторизуйся и пришли мне код подтверждения:\n{auth_url}',
        parse_mode='Markdown'
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
            await update.message.reply_text(f"❌ Не удалось авторизоваться. Ошибка: {str(e)}")
            return

    # Normal message handling
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING)

    # 1. Load credentials into Context
    creds = await get_user_creds(user_id)
    if not creds:
        await update.message.reply_text("⛔️ Сначала нужно авторизоваться. Напиши /login")
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

sent_reminders = set()

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
                # Check events starting in the next 30 minutes
                events = get_upcoming_events_soon(minutes=30)
                
                if events:
                     for event in events:
                        event_id = event['id']
                        
                        # Skip if already sent
                        if event_id in sent_reminders:
                            continue
                            
                        summary = event.get('summary', 'Без названия')
                        start = event['start']
                        end = event['end']
                        
                        # Handle formatting and time check
                        start_str = start.get('dateTime', start.get('date'))
                        end_str = end.get('dateTime', end.get('date'))
                        
                        msg = ""
                        
                        if 'dateTime' in start:
                            # Parse times
                            start_dt = datetime.datetime.fromisoformat(start_str)
                            end_dt = datetime.datetime.fromisoformat(end_str)
                            
                            # Check if it's too close to start (e.g. user said "not right now")
                            # We'll rely primarily on the duplicate check, but we could also check time
                            # Current logic: If we catch it in the [0, 30] min window and haven't sent it, we send.
                            
                            # Format: "Название активности: время(например 16:00 - 17:00"
                            time_range = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
                            msg = f"⏰ Напоминание! Скоро: {summary}: {time_range}"
                        else:
                            # All-day event
                            msg = f"⏰ Напоминание! Сегодня: {summary}"

                        try:
                             await context.bot.send_message(chat_id=user_id, text=msg)
                             # Mark as sent
                             sent_reminders.add(event_id)
                        except Exception as inner_e:
                            print(f"Failed to send message to {user_id}: {inner_e}")

            finally:
                current_user_creds.reset(token_creds)
                
    except Exception as e:
        print(f"Error in check_reminders job: {e}")

async def post_init(application):
    await init_db()
    
    # Set bot commands for the menu button
    await application.bot.set_my_commands([
        ('start', 'Запустить бота'),
        ('calendar', '📅 Календарь'),
        ('events', 'Ближайшие события'),
        ('status', 'Статус подключения'),
        ('login', 'Авторизация в Google'),
        ('help', 'Справка'),
    ])

def run_bot():
    print("Бот (с Календарем) запускается...")
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("events", events_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("calendar", calendar_command))
    
    # Callback handler for calendar navigation
    application.add_handler(CallbackQueryHandler(calendar_callback, pattern=r"^CALENDAR\|"))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    if application.job_queue:
        # Check every minute
        application.job_queue.run_repeating(check_reminders, interval=60, first=10)

    application.run_polling()
