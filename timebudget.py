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

# Read task length values from environment (in minutes, with defaults)
TASK_LENGTH_LOW = int(os.getenv("TASK_LENGTH_LOW", 30))
TASK_LENGTH_MEDIUM = int(os.getenv("TASK_LENGTH_MEDIUM", 60))
TASK_LENGTH_HIGH = int(os.getenv("TASK_LENGTH_HIGH", 90))
TASK_LENGTH_MUST_BE_DONE_TODAY = int(os.getenv("TASK_LENGTH_MUST_BE_DONE_TODAY", 90))

# Map priority names to task length
priority_to_time_block = {
    "Low": TASK_LENGTH_LOW,
    "Medium": TASK_LENGTH_MEDIUM,
    "High": TASK_LENGTH_HIGH,
    "Must Be Done Today": TASK_LENGTH_MUST_BE_DONE_TODAY,
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# --------------------------- DAILY TASKS ---------------------------
daily_tasks = set([
    "Play back in chess",
    "Drink an Owala",
    "Write 5 Sentences for Blog",
    "Italian Anki",
    "Call someone you don't call often (@Yap Directory)",
    "Shave",
    "Brush Teeth",
    "Shower",
    "Morning Routine",
    "Budget Reset",
    "Kyros HW Check",
    "Book Office Room",
    "Clean Slate",
    "Reconcile",
    "Duolingo",
    "Clean Room",
    "Clean out Backpack",
    "Weekly Reset",
    "Pay Off Credit Cards",
    "Meal Plan",
    "Block out lunch & dinners for the week",
    "NYT Mini",
    "Forest Prune",
    "Schedule Day",
    "Drink and Owala"
])

# --------------------------- UTILS ---------------------------
def get_task_name(properties):
    try:
        return properties.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Unnamed Task")
    except IndexError:
        return "Unnamed Task"

# --------------------------- NOTION API FUNCTIONS ---------------------------
def fetch_unscheduled_tasks_for_class(task_class):
    today = datetime.datetime.now().date().isoformat()
    filter_payload = {
        "and": [
            {"property": "Due", "date": {"equals": today}},
            {"property": "Class", "select": {"equals": task_class}},
            {"property": "Done", "checkbox": {"equals": False}},
        ]
    }
    sorts_payload = [{"timestamp": "created_time", "direction": "ascending"}]
    return fetch_tasks(filter_payload, sorts_payload)

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

# --------------------------- GOOGLE CALENDAR FUNCTIONS ---------------------------
def fetch_calendar_events():
    local_tz = tzlocal.get_localzone()
    start_of_day = datetime.datetime.combine(datetime.datetime.now().date(), datetime.time(0, 0), tzinfo=local_tz)
    end_of_day = start_of_day + datetime.timedelta(days=1)
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
                    timeMin=start_of_day.isoformat(),
                    timeMax=end_of_day.isoformat(),
                    maxResults=50,
                    singleEvents=True,
                    orderBy="startTime"
                ).execute()
                events.extend(events_result.get("items", []))
            except HttpError as error:
                logger.error(f"Failed to fetch events for calendar {cal_id}: {error}")
    except HttpError as error:
        logger.error(f"An error occurred: {error}")
    return events

def get_events_by_name(events, event_name):
    return sorted(
        [event for event in events if event_name.lower() in event.get("summary", "").lower()],
        key=lambda e: e.get("start", {}).get("dateTime", e.get("start", {}).get("date"))
    )

# --------------------------- TASK SCHEDULING ---------------------------
calendar_task_mapping = {
    "Academics": "Academics",
    "Kyros": "Kyros",
    "TEC Office Hours": "Co-Lab",
}
def update_date_time(task_id, task_name, start_time, end_time):
    url = f"https://api.notion.com/v1/pages/{task_id}"
    payload = {
        "properties": {
            "Due": {"date": {"start": start_time, "end": end_time}}
        }
    }
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code != 200:
        logger.error(f"Failed to update Task '{task_name}'. Status: {response.status_code}, {response.text}")
    else:
        print(f"✅ Task '{task_name}' scheduled from {start_time} to {end_time}.")
        
def schedule_tasks_for_mapping(event_name, task_class):
    print(f"\nProcessing mapping: '{event_name}' -> '{task_class}'")

    events = fetch_calendar_events()
    matching_events = get_events_by_name(events, event_name)

    if not matching_events:
        logger.warning(f"No events found for '{event_name}'. Skipping.")
        return

    tasks = fetch_unscheduled_tasks_for_class(task_class)
    if not tasks:
        logger.warning(f"No unscheduled tasks found for '{task_class}'. Skipping.")
        return

    unscheduled_tasks = tasks[:]  # Copy the list to track remaining tasks
    while unscheduled_tasks:
        new_unscheduled_tasks = []  # To track tasks that still don't fit

        for event in matching_events:
            event_start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date"))
            event_end = event.get("end", {}).get("dateTime", event.get("end", {}).get("date"))

            if not event_start or not event_end:
                logger.warning(f"Event '{event_name}' is missing start or end time. Skipping.")
                continue

            current_start_dt = datetime.datetime.fromisoformat(event_start).astimezone(LOCAL_TIMEZONE)
            event_end_dt = datetime.datetime.fromisoformat(event_end).astimezone(LOCAL_TIMEZONE)

            # Fill the event with remaining tasks
            task_index = 0
            while task_index < len(unscheduled_tasks) and current_start_dt + datetime.timedelta(minutes=TASK_LENGTH_MEDIUM) <= event_end_dt:
                task = unscheduled_tasks[task_index]
                task_name = get_task_name(task["properties"])
                task_id = task["id"]
                duration = priority_to_time_block.get("Medium", TASK_LENGTH_MEDIUM)
                new_end_dt = current_start_dt + datetime.timedelta(minutes=duration)

                update_date_time(task_id, task_name, current_start_dt.isoformat(), new_end_dt.isoformat())

                print(f"✅ Task '{task_name}' scheduled from {current_start_dt} to {new_end_dt}.")
                
                # Move to the next time block
                current_start_dt = new_end_dt
                task_index += 1

            # Track remaining tasks that weren't scheduled in this iteration
            new_unscheduled_tasks.extend(unscheduled_tasks[task_index:])

        # If we made no progress, exit the loop to avoid infinite looping
        if len(new_unscheduled_tasks) == len(unscheduled_tasks):
            logger.warning(f"Could not schedule {len(new_unscheduled_tasks)} remaining tasks.")
            break

        # Update unscheduled tasks list
        unscheduled_tasks = new_unscheduled_tasks
        
def main():
    for event_name, task_class in calendar_task_mapping.items():
        schedule_tasks_for_mapping(event_name, task_class)  # Ensure it runs for all mappings

if __name__ == "__main__":
    main()