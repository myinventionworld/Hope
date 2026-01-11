import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import google.generativeai as genai
import datetime
from src.config import TELEGRAM_TOKEN, GEMINI_API_KEY
from src.calendar_tools import create_calendar_event, delete_calendar_event_by_summary, list_upcoming_events, get_upcoming_events_soon

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
tools = [create_calendar_event, delete_calendar_event_by_summary, list_upcoming_events]
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    tools=tools
)
chat = model.start_chat(enable_automatic_function_calling=True)

# Global variable to store the Chat ID to send reminders to
CHAT_ID = None
notified_events = set()

async def start(update, context):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id
    await update.message.reply_text(
        'Ассистент с Календарем. Попробуй: "Запиши меня в зал сегодня в 8 вечера на 2 часа".\n'
        'Я также буду напоминать о событиях за 15 минут!'
    )

async def handle_message(update, context):
    global CHAT_ID
    if CHAT_ID is None:
        CHAT_ID = update.effective_chat.id
        
    user_text = update.message.text
    print(f"Пользователь: {user_text}")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING)

    try:
        current_date = datetime.date.today().isoformat()
        augmented_user_text = f"Today's date is {current_date}. User request: {user_text}"
        
        response = chat.send_message(augmented_user_text)
        await update.message.reply_text(response.text)

    except Exception as e:
        print(f"Ошибка: {e}")
        await update.message.reply_text("Ой, что-то пошло не так.")

async def check_reminders(context):
    """Job to check for upcoming events and send reminders."""
    global CHAT_ID, notified_events
    if CHAT_ID is None:
        return

    try:
        # Check for events in the next 15 minutes
        events = get_upcoming_events_soon(minutes=15)
        
        for event in events:
            event_id = event['id']
            # If we haven't notified about this event yet
            if event_id not in notified_events:
                summary = event.get('summary', 'Без названия')
                start = event['start'].get('dateTime', event['start'].get('date'))
                
                # Format time nicely
                try:
                    dt = datetime.datetime.fromisoformat(start)
                    time_str = dt.strftime("%H:%M")
                except:
                   time_str = start

                message = f"⏰ Напоминание! Скоро событие: **{summary}** в {time_str}"
                
                await context.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
                notified_events.add(event_id)
                print(f"Sent reminder for event: {summary}")
                
    except Exception as e:
        print(f"Error in check_reminders job: {e}")

def run_bot():
    print("Бот (с Календарем) запускается...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add the reminder job to run every 60 seconds
    if application.job_queue:
        application.job_queue.run_repeating(check_reminders, interval=60, first=10)
        print("Планировщик напоминаний запущен.")

    application.run_polling()
