# src/ui/calendar_keyboard.py
import calendar
from datetime import date
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Callback data format: CALENDAR|ACTION|YEAR|MONTH|DAY
# Actions: IGNORE, DAY, PREV, NEXT

DAYS_OF_WEEK = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_RU = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]

def create_calendar(year: int = None, month: int = None) -> InlineKeyboardMarkup:
    """
    Creates an inline keyboard with a calendar for the given year and month.
    """
    now = date.today()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    keyboard = []
    
    # Row 1: Month and Year
    keyboard.append([
        InlineKeyboardButton(
            f"{MONTHS_RU[month]} {year}",
            callback_data=f"CALENDAR|IGNORE|{year}|{month}|0"
        )
    ])
    
    # Row 2: Days of week
    keyboard.append([
        InlineKeyboardButton(day, callback_data=f"CALENDAR|IGNORE|{year}|{month}|0")
        for day in DAYS_OF_WEEK
    ])
    
    # Get calendar matrix for the month
    cal = calendar.Calendar(firstweekday=0)  # Monday first
    month_days = cal.monthdayscalendar(year, month)
    
    # Rows 3-8: Days grid
    for week in month_days:
        row = []
        for day_num in week:
            if day_num == 0:
                # Empty day
                row.append(InlineKeyboardButton(
                    " ",
                    callback_data=f"CALENDAR|IGNORE|{year}|{month}|0"
                ))
            else:
                row.append(InlineKeyboardButton(
                    str(day_num),
                    callback_data=f"CALENDAR|DAY|{year}|{month}|{day_num}"
                ))
        keyboard.append(row)
    
    # Row 9: Navigation
    # Calculate previous and next month
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
    
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    keyboard.append([
        InlineKeyboardButton(
            "◀️ Пред.",
            callback_data=f"CALENDAR|PREV|{prev_year}|{prev_month}|0"
        ),
        InlineKeyboardButton(
            "Сегодня",
            callback_data=f"CALENDAR|TODAY|{now.year}|{now.month}|{now.day}"
        ),
        InlineKeyboardButton(
            "След. ▶️",
            callback_data=f"CALENDAR|NEXT|{next_year}|{next_month}|0"
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)

def parse_callback_data(data: str) -> dict:
    """Parses callback data string into a dictionary."""
    parts = data.split("|")
    return {
        "prefix": parts[0],
        "action": parts[1],
        "year": int(parts[2]),
        "month": int(parts[3]),
        "day": int(parts[4])
    }
