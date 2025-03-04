import datetime
import requests
from dotenv import load_dotenv
import os
import logging
import tzlocal

# ------------------ Google Calendar Imports & Constants ------------------
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# Hardcoded calendar IDs
RELEVANT_CAL_IDS = [
    "auh94mav0t03nkb6msorltnq5c@group.calendar.google.com",
    "alexander.pieroni@duke.edu",
    "dukepitchforks@gmail.com",
    "979a35bb2f0c74ab8aca0868feeb5d485c595bc85e30683463c426927ba49b7b@group.calendar.google.com",
    "4fcda66bf9bee7ab50963d3dc47879103efadbde75ccbf7f961ecb6ecf551fcd@group.calendar.google.com",
    "adunq704chaon3jlrr7pdbe3js@group.calendar.google.com",
    "alexanderjpieroni@gmail.com",
    "b98421b54b8241116adb7fcdd6e91ea7bae06619ca0495a432d5ee63505b3ea8@group.calendar.google.com",
    "bd188c1dd513dce377fd9b3e198a11dc63f1c892fae5b64154bc568578ad3146@group.calendar.google.com",
    "apieroni@kyros.ai",
    "898f2b3oak6pvpdgcomjv261i1ktg0ns@import.calendar.google.com",
    "43b2063fd153b80e0c8cf662ebd57a99f25336abc3cac85ff1369d1933b8883d@group.calendar.google.com",
]

# --------------------------- CONFIGURATION ---------------------------
LOCAL_TIMEZONE = tzlocal.get_localzone()
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# --------------------------- UTILS ---------------------------
def get_task_name(properties):
    try:
        return properties.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Unnamed Task")
    except IndexError:
        return "Unnamed Task"

def format_date_iso(date_time_str):
    try:
        dt = datetime.datetime.fromisoformat(date_time_str)
        return dt.date().isoformat()
    except ValueError:
        logger.error(f"Invalid date-time string: {date_time_str}")
        return None

# --------------------------- NOTION API FUNCTIONS ---------------------------
def fetch_tasks(filter_payload, sorts_payload):
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    all_tasks = []
    payload = {"filter": filter_payload, "sorts": sorts_payload, "page_size": 100}
    while True:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            logger.error(f"Failed to fetch tasks. Status: {response.status_code}, {response.text}")
            break
        data = response.json()
        tasks = data.get("results", [])
        all_tasks.extend(tasks)
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")
    return all_tasks

def fetch_colab_tasks():
    """Fetch tasks due within today with Class 'Co-Lab'."""
    today = datetime.datetime.now().date().isoformat()
    # Use "equals" to fetch tasks due exactly today.
    filter_payload = {
        "and": [
            {"property": "Due", "date": {"equals": today}},
            {"property": "Class", "select": {"equals": "Co-Lab"}},
            {"property": "Done", "checkbox": {"equals": False}},
        ]
    }
    sorts_payload = [{"timestamp": "created_time", "direction": "ascending"}]
    return fetch_tasks(filter_payload, sorts_payload)

def update_date_time(task_id, task_name=None, start_time=None, end_time=None, priority=None, status=None):
    url = f"https://api.notion.com/v1/pages/{task_id}"
    payload = {"properties": {}}
    if start_time:
        # Convert string to datetime and then to local ISO
        start_dt = datetime.datetime.fromisoformat(start_time)
        start_time = start_dt.astimezone(LOCAL_TIMEZONE).isoformat()
    if end_time:
        end_dt = datetime.datetime.fromisoformat(end_time)
        end_time = end_dt.astimezone(LOCAL_TIMEZONE).isoformat()
    if start_time or end_time:
        date_payload = {}
        if start_time:
            date_payload["start"] = start_time
        if end_time:
            date_payload["end"] = end_time
        payload["properties"]["Due"] = {"date": date_payload}
    if priority:
        payload["properties"]["Priority"] = {"status": {"name": priority}}
    if status:
        payload["properties"]["Status"] = {"status": {"name": status}}
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code != 200:
        logger.error(f"Failed to update Task '{task_name}'. Status: {response.status_code}, {response.text}")

# --------------------------- GOOGLE CALENDAR FUNCTIONS ---------------------------
def fetch_calendar_events(chosen_date=None):
    """Fetch all calendar events for the given date (defaults to today)."""
    local_tz = tzlocal.get_localzone()
    now_local = datetime.datetime.now(local_tz).replace(second=0, microsecond=0)
    if not chosen_date:
        chosen_date = now_local.date()
    start_of_day = datetime.datetime.combine(chosen_date, datetime.time(0, 0), tzinfo=local_tz)
    end_of_day = start_of_day + datetime.timedelta(days=1)
    time_min = start_of_day.isoformat()
    time_max = end_of_day.isoformat()
    events = []
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        service = build("calendar", "v3", credentials=creds)
        for cal_id in RELEVANT_CAL_IDS:
            try:
                events_result = service.events().list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=50,
                    singleEvents=True,
                    orderBy="startTime"
                ).execute()
                cal_events = events_result.get("items", [])
                events.extend(cal_events)
            except HttpError as error:
                logger.error(f"Failed to fetch events for calendar {cal_id}: {error}")
    except HttpError as error:
        logger.error(f"An error occurred: {error}")
    return events

def get_tec_office_hours_event(events):
    """Return the first event with 'TEC Office Hours' in its summary."""
    for event in events:
        summary = event.get("summary", "")
        if "TEC Office Hours" in summary:
            return event
    return None

# --------------------------- MAIN LOGIC ---------------------------
def main():
    # Fetch today's calendar events and extract the TEC Office Hours event.
    cal_events = fetch_calendar_events()
    tec_event = get_tec_office_hours_event(cal_events)
    if not tec_event:
        logger.error("No TEC Office Hours event found for today. Aborting scheduling.")
        return
    # Extract start and end times from the TEC event.
    start_obj = tec_event.get("start", {})
    end_obj = tec_event.get("end", {})
    start_time = start_obj.get("dateTime", start_obj.get("date"))
    end_time = end_obj.get("dateTime", end_obj.get("date"))
    if not start_time or not end_time:
        logger.error("TEC Office Hours event is missing valid start or end times. Aborting scheduling.")
        return

    # Fetch all tasks due within today with Class 'Co-Lab'
    colab_tasks = fetch_colab_tasks()
    if not colab_tasks:
        print("No Co-Lab tasks due within today found.")
        return

    print(f"Found {len(colab_tasks)} Co-Lab task(s). Scheduling them within the TEC Office Hours block:")
    for task in colab_tasks:
        task_id = task["id"]
        task_name = get_task_name(task.get("properties", {}))
        update_date_time(task_id, task_name=task_name, start_time=start_time, end_time=end_time)
        print(f"Scheduled '{task_name}' from {start_time} to {end_time}.")

if __name__ == "__main__":
    main()