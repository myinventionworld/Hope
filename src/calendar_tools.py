import datetime
from googleapiclient.discovery import build
from src.auth import authenticate_google_calendar

def create_calendar_event(title: str, start_time_str: str, duration_hours: int):
    try:
        creds = authenticate_google_calendar()
        service = build('calendar', 'v3', credentials=creds)

        start_time = datetime.datetime.fromisoformat(start_time_str)
        
        if start_time.tzinfo is None or start_time.tzinfo.utcoffset(start_time) is None:
            start_time = start_time.astimezone()

        end_time = start_time + datetime.timedelta(hours=duration_hours)

        offset = start_time.strftime('%z')
        timezone_offset = f"{offset[:-2]}:{offset[-2:]}" 
        
        try:
            timezone = start_time.tzinfo.zone 
        except AttributeError:
             timezone = start_time.tzname()
             if timezone is None or len(timezone) > 3:
                 timezone = timezone_offset

        event = {
            'summary': title,
            'start': {'dateTime': start_time.isoformat(), 'timeZone': timezone},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': timezone},
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Событие '{title}' успешно создано в {start_time.strftime('%H:%M %d-%m-%Y')}. Link: {event.get('htmlLink')}"

    except Exception as e:
        print(f"Ошибка создания события: {e}")
        return f"Не удалось создать событие. Ошибка: {e}"


def delete_calendar_event_by_summary(event_summary: str):
    try:
        creds = authenticate_google_calendar()
        service = build('calendar', 'v3', credentials=creds)

        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time

        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=20, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return "Предстоящих событий не найдено."

        found_event_id = None
        found_event_summary = None

        for event in events:
            event_title = event.get('summary', '').lower()
            if event_summary.lower() in event_title:
                found_event_id = event['id']
                found_event_summary = event['summary']
                break # Удаляем первое совпавшее событие

        if found_event_id:
            service.events().delete(calendarId='primary', eventId=found_event_id).execute()
            return f"Событие '{found_event_summary}' (ID: {found_event_id}) успешно удалено."
        else:
            return f"Не найдено предстоящего события, содержащего '{event_summary}' в названии."

    except Exception as e:
        print(f"Ошибка удаления события: {e}")
        return f"Не удалось удалить событие. Ошибка: {e}"


def list_upcoming_events(max_results: int = 10):
    try:
        creds = authenticate_google_calendar()
        service = build('calendar', 'v3', credentials=creds)

        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=max_results, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return "Нет предстоящих событий."
        
        result = "Предстоящие события:\n"
        for event in events:
            start_info = event['start']
            start_str = start_info.get('dateTime', start_info.get('date'))
            summary = event.get('summary', 'Без названия')
            event_id = event['id']

            formatted_start = ""
            time_type = ""

            if 'dateTime' in start_info:
                dt_object = datetime.datetime.fromisoformat(start_str)
                formatted_start = dt_object.strftime("%d.%m.%Y %H:%M")
                time_type = "Дата/Время"
            elif 'date' in start_info:
                date_object = datetime.date.fromisoformat(start_str)
                formatted_start = date_object.strftime("%d.%m.%Y")
                time_type = "Дата"
            
            result += f"- {time_type}: {formatted_start} | Название: \"{summary}\" | ID: {event_id}\n"
        return result

    except Exception as e:
        return f"Ошибка получения списка событий: {e}"

def get_upcoming_events_soon(minutes: int = 15):
    """
    Возвращает список событий, которые начнутся в ближайшие 'minutes' минут.
    """
    try:
        creds = authenticate_google_calendar()
        service = build('calendar', 'v3', credentials=creds)

        now = datetime.datetime.utcnow()
        # Look ahead 'minutes'
        time_max = (now + datetime.timedelta(minutes=minutes)).isoformat() + 'Z'
        now_iso = now.isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary', 
            timeMin=now_iso,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
    except Exception as e:
        print(f"Error fetching upcoming events: {e}")
        return []
