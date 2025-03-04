import datetime
import requests
from dotenv import load_dotenv
import os
import logging
import pytz
import tzlocal
import calendar

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

# ---------------------------------------------------------------------------
PROPERTY_DUE = "Due"
PROPERTY_PRIORITY = "Priority"
PROPERTY_STATUS = "Status"
PROPERTY_DONE = "Done"

LOCAL_TIMEZONE = tzlocal.get_localzone()

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

priority_to_time_block = {
    "Low": 5,
    "Medium": 15,
    "High": 30,
    "Must Be Done Today": 30
}

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# --------------------------- UTILS & HELPERS ---------------------------
daily_tasks = [
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
    "Shower",
    "Clean Room",
    "Shave",
    "Clean out Backpack",
    "Weekly Reset",
    "Pay Off Credit Cards",
    "Play back in chess",
    "Meal Plan",
    "Block out lunch & dinners for the week",
    "Call someone you don't call often (",
    "NYT Mini",
    "Forest Prune",
    "Schedule Day",
    "Drink and Owala"
]

def get_task_name(properties):
    try:
        return properties.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Unnamed Task")
    except IndexError:
        return "Unnamed Task"

def rename_task(task_id, new_name):
    url = f"https://api.notion.com/v1/pages/{task_id}"
    payload = {
        "properties": {
            "Name": {
                "title": [
                    {"text": {"content": new_name}}
                ]
            }
        }
    }
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code == 200:
        logger.info(f"Task renamed to: {new_name}")
    else:
        logger.error(f"Failed to rename task. {response.status_code}: {response.text}")

def format_date_iso(date_time_str):
    try:
        date_time = datetime.datetime.fromisoformat(date_time_str)
        return date_time.date().isoformat()
    except ValueError:
        logger.error(f"Invalid date-time string: {date_time_str}")
        return None

def parse_custom_date(input_str):
    parts = input_str.split()
    if len(parts) == 2:
        month_str, year_str = parts
        try:
            month_str_cap = month_str.capitalize()
            month_num = list(calendar.month_abbr).index(month_str_cap) if month_str_cap in calendar.month_abbr else None
            if not month_num:
                return None
            year = int(year_str)
            return datetime.date(year, month_num, 1)
        except (ValueError, IndexError):
            return None
    return None

# --------------------------- API CALLS ---------------------------
def fetch_tasks(filter_payload, sorts_payload):
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    all_tasks = []
    payload = {
        "filter": filter_payload,
        "sorts": sorts_payload,
        "page_size": 100
    }
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

def fetch_all_tasks_sorted_by_priority_created():
    filter_payload = {
        "and": [
            {"property": "Priority", "status": {"does_not_equal": "Someday"}},
            {"property": "Status", "status": {"does_not_equal": "Done"}},
            {"property": "Status", "status": {"does_not_equal": "Handed Off"}},
            {"property": "Status", "status": {"does_not_equal": "Deprecated"}},
            {"property": "Status", "status": {"does_not_equal": "Waiting on Reply"}},
            {"property": "Status", "status": {"does_not_equal": "Waiting on other task"}},
            {"property": "Done", "checkbox": {"equals": False}},
        ]
    }
    sorts_payload = [
        {"property": "Priority", "direction": "ascending"},
        {"timestamp": "created_time", "direction": "ascending"}
    ]
    return fetch_tasks(filter_payload, sorts_payload)

def fetch_all_tasks_sorted_by_created(assigned_time_equals=False, target_date=None):
    if target_date is None:
        target_date = datetime.datetime.now().date().isoformat()

    filter_payload = {
        "and": [
            {"property": "Due", "date": {"on_or_before": target_date}},
            {"property": "Assigned time", "checkbox": {"equals": assigned_time_equals}},
            {"property": "Done", "checkbox": {"equals": False}},
            {"property": "Priority", "status": {"does_not_equal": "Someday"}},
            {"property": "Priority", "status": {"does_not_equal": "Unassigned"}}
        ]
    }

    sorts_payload = [{"timestamp": "created_time", "direction": "ascending"}]
    return fetch_tasks(filter_payload, sorts_payload)

def fetch_current_schedule():
    return fetch_all_tasks_sorted_by_created(assigned_time_equals=True)

def fetch_unassigned_tasks():
    filter_payload = {
        "and": [
            {"property": "Priority", "status": {"equals": "Unassigned"}},
            {"property": "Status", "status": {"does_not_equal": "Done"}},
            {"property": "Status", "status": {"does_not_equal": "Handed Off"}},
            {"property": "Status", "status": {"does_not_equal": "Deprecated"}},
            {"property": "Status", "status": {"does_not_equal": "Waiting on Reply"}},
            {"property": "Status", "status": {"does_not_equal": "Waiting on other task"}},
            {"property": "Done", "checkbox": {"equals": False}}
        ]
    }
    sorts_payload = [{"timestamp": "created_time", "direction": "ascending"}]
    return fetch_tasks(filter_payload, sorts_payload)

# --------------------------- CREATE 'SCHEDULE DAY' TASK ---------------------------
def create_schedule_day_task():
    today = datetime.datetime.now(LOCAL_TIMEZONE).date().isoformat()
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    filter_payload = {
        "filter": {
            "and": [
                {"property": "Name", "title": {"equals": "Schedule Day"}},
                {"property": "Due", "date": {"on_or_before": today}},
                {"property": "Due", "date": {"on_or_after": today}}
            ]
        }
    }
    response = requests.post(url, headers=headers, json=filter_payload)
    if response.status_code == 200:
        existing_results = response.json().get("results", [])
        if existing_results:
            print("🗓️ 'Schedule Day' task already exists for today. Skipping creation.")
            return
    else:
        logger.error(f"Failed to fetch 'Schedule Day' tasks. Status: {response.status_code}, {response.text}")
        return
    now = datetime.datetime.now(datetime.timezone.utc)
    due = (now + datetime.timedelta(minutes=30)).isoformat()
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": "Schedule Day"}}]},
            "Class": {"select": {"name": "Admin"}},
            "Due": {"date": {"start": now.isoformat(), "end": due}},
            "Priority": {"status": {"name": "High"}}
        }
    }
    create_resp = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
    if create_resp.status_code == 200:
        logger.info("'Schedule Day' task created successfully.")
    else:
        logger.error(f"Failed to create 'Schedule Day' task. Status: {create_resp.status_code}, {create_resp.text}")

# --------------------------- UPDATE FUNCTIONS ---------------------------
def update_date_only(task_id, task_name=None, date_str=None):
    if not date_str:
        return
    date_only = format_date_iso(date_str) or date_str
    url = f"https://api.notion.com/v1/pages/{task_id}"
    payload = {"properties": {"Due": {"date": {"start": date_only}}}}
    r = requests.patch(url, headers=headers, json=payload)
    if r.status_code != 200:
        logger.error(f"Failed to update '{task_name}'. {r.status_code}: {r.text}")
    else:
        logger.info(f"Task '{task_name}' set to date-only start: {date_only}")

def update_date_time(task_id, task_name=None, start_time=None, end_time=None, priority=None, status=None):
    url = f"https://api.notion.com/v1/pages/{task_id}"
    payload = {"properties": {}}
    if start_time:
        start_dt = datetime.datetime.fromisoformat(start_time)
        start_dt_local = start_dt.astimezone(LOCAL_TIMEZONE)
        start_time = start_dt_local.isoformat()
    if end_time:
        end_dt = datetime.datetime.fromisoformat(end_time)
        end_dt_local = end_dt.astimezone(LOCAL_TIMEZONE)
        end_time = end_dt_local.isoformat()
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
        logger.error(f"Failed to update Task: '{task_name}'. Status: {response.status_code}, {response.text}")

def triage_unassigned_tasks():
    priority_mapping = {
        "1": "Low",
        "2": "Medium",
        "3": "High",
        "c": "Deprecated",
        "x": "Done",
        "s": "Someday"
    }
    previously_triaged = set()
    unassigned_tasks = fetch_unassigned_tasks()
    print(f"\n📋 You have {len(unassigned_tasks)} unassigned tasks.")
    for task in unassigned_tasks:
        props = task.get("properties", {})
        task_id = task["id"]
        task_name = get_task_name(props)
        if task_name in previously_triaged:
            print(f"🔁 Task '{task_name}' has already been triaged. Marking as Deprecated.")
            update_date_time(task_id, task_name=task_name, status="Deprecated")
            return
        if task_name in daily_tasks:
            update_date_time(task_id, task_name=task_name, priority="Low")
            now = datetime.datetime.now(LOCAL_TIMEZONE)
            seven_thirty = datetime.datetime.combine(now.date(), datetime.time(7, 30), tzinfo=LOCAL_TIMEZONE)
            due_time = now if now < seven_thirty else seven_thirty
            due_time_iso = due_time.isoformat()
            update_date_time(task_id, task_name=task_name, start_time=due_time_iso, end_time=due_time_iso)
            print(f"📌 '{task_name}' recognized as a daily task. Set to Low priority and due at {due_time_iso}.")
            continue
        print(f"\n📝 Task: '{task_name}' is 'Unassigned'.")
        print("\n[1] Low (💡)")
        print("[2] Medium (♻️)")
        print("[3] High (🔥)")
        print("[c] Deprecated (🗑️)")
        print("[x] Done (✅)")
        print("[s] Someday (🌥️)")
        print("[r] Rename Task")
        user_choice = input("\nYour choice: ").strip().lower()
        if user_choice == "r":
            new_name = input("Enter new task name: ").strip()
            rename_task(task_id, new_name)
            print(f"Task renamed to '{new_name}'.")
            task_name = new_name
            user_choice = input("\nChoose priority or status [1/2/3/c/x/s]: ").strip().lower()
        if user_choice == "c":
            update_date_time(task_id, task_name=task_name, status="Deprecated")
            print(f"🗑️ '{task_name}' archived.")
        elif user_choice == "x":
            update_date_time(task_id, task_name=task_name, status="Done")
            print(f"✅ '{task_name}' Done.")
        elif user_choice in priority_mapping:
            chosen_priority = priority_mapping[user_choice]
            update_date_time(task_id, task_name=task_name, priority=chosen_priority)
            print(f"📌 '{task_name}' priority: {chosen_priority}")
            today_local_date = datetime.datetime.now(LOCAL_TIMEZONE).date().isoformat()
            update_date_only(task_id, task_name=task_name, date_str=today_local_date)
            print(f"📅 Due date for '{task_name}' set to today: {today_local_date}")
        previously_triaged.add(task_name)

# --------------------------- CALENDAR INTEGRATION FUNCTIONS ---------------------------
def fetch_calendar_events(chosen_date=None):
    """Fetch calendar events from all relevant calendars for the given date (defaults to today)."""
    local_tz = tzlocal.get_localzone()
    now_local = datetime.datetime.now(local_tz).replace(second=0, microsecond=0)
    if not chosen_date:
        chosen_date = now_local.date()
    start_of_day_local = datetime.datetime.combine(chosen_date, datetime.time(0, 0), tzinfo=local_tz)
    end_of_day_local = start_of_day_local + datetime.timedelta(days=1)
    time_min = start_of_day_local.isoformat()
    time_max = end_of_day_local.isoformat()
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
                    orderBy="startTime",
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

def update_colab_tasks_due(office_hours_event):
    """For any task with Class 'Co-Lab', update its due date/time to match the office hours event."""
    if not office_hours_event:
        return
    start_time = office_hours_event["start"].get("dateTime", office_hours_event["start"].get("date"))
    end_time = office_hours_event["end"].get("dateTime", office_hours_event["end"].get("date"))
    # Fetch all tasks and filter those with Class 'Co-Lab'
    all_tasks = fetch_all_tasks_sorted_by_created(assigned_time_equals=False)
    for task in all_tasks:
        class_value = task.get("properties", {}).get("Class", {}).get("select", {}).get("name")
        if class_value == "Co-Lab":
            task_id = task["id"]
            task_name = get_task_name(task.get("properties", {}))
            update_date_time(task_id, task_name=task_name, start_time=start_time, end_time=end_time)
            print(f"Updated '{task_name}' to TEC Office Hours block: {start_time} - {end_time}")

# --------------------------- OVERLAP & FREE BLOCKS ---------------------------
def check_for_overlap(current_schedule, proposed_start, proposed_end):
    proposed_start_utc = proposed_start.astimezone(datetime.timezone.utc)
    proposed_end_utc = proposed_end.astimezone(datetime.timezone.utc)
    for task in current_schedule:
        props = task.get("properties", {})
        due = props.get("Due", {}).get("date", {})
        existing_start = due.get("start")
        existing_end = due.get("end")
        if not existing_start or not existing_end:
            continue
        existing_start_dt = datetime.datetime.fromisoformat(existing_start).astimezone(datetime.timezone.utc)
        existing_end_dt = datetime.datetime.fromisoformat(existing_end).astimezone(datetime.timezone.utc)
        if (proposed_start_utc < existing_end_dt) and (proposed_end_utc > existing_start_dt):
            return True
    return False

def handle_overlapping_due_dates(current_schedule):
    today = datetime.datetime.now(LOCAL_TIMEZONE).date().isoformat()
    def get_priority_level(task):
        props = task.get("properties", {})
        priority = props.get("Priority", {}).get("status", {}).get("name", "Low")
        return "High" if priority in ["High", "Must Be Done Today"] else "Low"
    def set_date_only(task_id, task_name):
        update_date_only(task_id, task_name=task_name, date_str=today)
    def get_task_times(task):
        props = task.get("properties", {})
        due = props.get("Due", {}).get("date", {})
        start = due.get("start")
        end = due.get("end")
        if not start or not end:
            return None, None
        start_dt = datetime.datetime.fromisoformat(start).astimezone(datetime.timezone.utc)
        end_dt = datetime.datetime.fromisoformat(end).astimezone(datetime.timezone.utc)
        return start_dt, end_dt
    overlapping_pairs = []
    n = len(current_schedule)
    for i in range(n):
        task_a = current_schedule[i]
        a_start_dt, a_end_dt = get_task_times(task_a)
        if a_start_dt is None or a_end_dt is None:
            continue
        for j in range(i+1, n):
            task_b = current_schedule[j]
            b_start_dt, b_end_dt = get_task_times(task_b)
            if b_start_dt is None or b_end_dt is None:
                continue
            if a_start_dt < b_end_dt and b_start_dt < a_end_dt:
                overlapping_pairs.append((task_a, task_b))
    if not overlapping_pairs:
        return
    handled_ids = set()
    for (task_a, task_b) in overlapping_pairs:
        a_id = task_a["id"]
        b_id = task_b["id"]
        if a_id in handled_ids or b_id in handled_ids:
            continue
        a_priority = get_priority_level(task_a)
        b_priority = get_priority_level(task_b)
        set_date_only(a_id, get_task_name(task_a.get("properties", {})))
        set_date_only(b_id, get_task_name(task_b.get("properties", {})))
        if a_priority == "High" and b_priority == "Low":
            current_schedule[:] = [t for t in current_schedule if t["id"] != b_id]
        elif a_priority == "Low" and b_priority == "High":
            current_schedule[:] = [t for t in current_schedule if t["id"] != a_id]
        elif a_priority == "Low" and b_priority == "Low":
            current_schedule[:] = [t for t in current_schedule if t["id"] not in (a_id, b_id)]
        handled_ids.add(a_id)
        handled_ids.add(b_id)

def calculate_available_time_blocks(current_schedule, start_hour=9, end_hour=23):
    now_local = datetime.datetime.now(LOCAL_TIMEZONE)
    today = now_local.date()
    start_of_day = datetime.datetime.combine(today, datetime.time(hour=start_hour), tzinfo=LOCAL_TIMEZONE)
    end_of_day = datetime.datetime.combine(today, datetime.time(hour=end_hour), tzinfo=LOCAL_TIMEZONE)
    current_time = max(start_of_day, now_local)
    busy_periods = []
    for task in current_schedule:
        props = task.get("properties", {})
        due = props.get("Due", {}).get("date", {})
        start = due.get("start")
        end = due.get("end")
        if start and end:
            busy_start = datetime.datetime.fromisoformat(start).astimezone(LOCAL_TIMEZONE)
            busy_end = datetime.datetime.fromisoformat(end).astimezone(LOCAL_TIMEZONE)
            if busy_end > current_time:
                busy_periods.append((max(busy_start, current_time), busy_end))
    busy_periods.sort(key=lambda x: x[0])
    free_blocks = []
    for busy_start, busy_end in busy_periods:
        if current_time < busy_start:
            free_blocks.append((current_time, busy_start))
        current_time = max(current_time, busy_end)
    if current_time < end_of_day:
        free_blocks.append((current_time, end_of_day))
    return free_blocks

def always_available_blocks(start_hour=9, end_hour=23):
    now = datetime.datetime.now(LOCAL_TIMEZONE)
    return [(datetime.datetime.combine(now.date(), datetime.time(hour=start_hour), tzinfo=LOCAL_TIMEZONE),
             datetime.datetime.combine(now.date(), datetime.time(hour=end_hour), tzinfo=LOCAL_TIMEZONE))]

def display_available_time_blocks(free_blocks):
    print("\n🕒 **Available Time Blocks for Today**:")
    if not free_blocks:
        print("🚫 No free time available today.")
        response = input("Would you like to schedule for tomorrow instead? (yes/no): ").strip().lower()
        if response == 'yes':
            schedule_tomorrow()
        else:
            print("Okay, let me know if you'd like help later.")
        return
    for start, end in free_blocks:
        print(f"✅ {start.strftime('%I:%M %p')} to {end.strftime('%I:%M %p')}")

def schedule_tomorrow():
    today_str = datetime.datetime.now(LOCAL_TIMEZONE).date().isoformat()
    tomorrow_date = datetime.datetime.now(LOCAL_TIMEZONE).date() + datetime.timedelta(days=1)
    tomorrow_str = tomorrow_date.isoformat()
    filter_payload = {
        "and": [
            {"property": "Due", "date": {"on_or_before": today_str}},
            {"property": "Done", "checkbox": {"equals": False}}
        ]
    }
    tasks_due_today = fetch_tasks(filter_payload, [])
    for task in tasks_due_today:
        task_id = task["id"]
        task_name = get_task_name(task["properties"])
        update_date_only(task_id, task_name=task_name, date_str=tomorrow_str)
        print(f"Moved '{task_name}' from {today_str} to {tomorrow_str}")
    tomorrow_start_local = datetime.datetime.combine(tomorrow_date, datetime.time(hour=9, minute=0))
    tomorrow_start_utc = tomorrow_start_local.astimezone(datetime.timezone.utc)
    tasks_post_triage = fetch_all_tasks_sorted_by_created(assigned_time_equals=False, target_date=tomorrow_str)
    non_deprecated_tasks = [
        t for t in tasks_post_triage if t.get("properties", {}).get("Status", {}).get("status", {}).get("name") != "Deprecated"
    ]
    seen_ids = set()
    unique_tasks = []
    for t in non_deprecated_tasks:
        if t["id"] not in seen_ids:
            seen_ids.add(t["id"])
            unique_tasks.append(t)
    if unique_tasks:
        schedule_tasks_in_pattern(unique_tasks, test_mode=False, starting_time=tomorrow_start_utc)
    else:
        print("\nNo tasks to schedule tomorrow after moving tasks.")

def show_schedule_overview(current_schedule):
    print("\n🔍 Checking schedule overview...")
    print("\n🛠️ Resolving overlapping due dates...")
    free_blocks = always_available_blocks(start_hour=9, end_hour=23)
    display_available_time_blocks(free_blocks)

def wrap_to_9am_if_needed(dt: datetime.datetime, target_date: datetime.date) -> datetime.datetime:
    local_dt = dt.astimezone(LOCAL_TIMEZONE)
    if local_dt.date() != target_date or local_dt.hour >= 23:
        candidate = datetime.datetime.combine(target_date, datetime.time(9, 0), tzinfo=LOCAL_TIMEZONE)
    else:
        candidate = local_dt
    now_local = datetime.datetime.now(LOCAL_TIMEZONE)
    final_local = max(candidate, now_local)
    return final_local.astimezone(datetime.timezone.utc)

def schedule_complete():
    print("Scheduling is complete!")

# --------------------------- CORE SCHEDULING LOGIC ---------------------------
def schedule_single_task(task, current_time, test_mode, current_schedule, scheduled_task_names,
                         accept_all_mode=False, allow_late_night_scheduling=False, ignore_availability_mode=False):
    props = task.get("properties", {})
    task_id = task["id"]
    task_name = get_task_name(props)
    priority = props.get("Priority", {}).get("status", {}).get("name", "Low")
    status = props.get("Status", {}).get("status", {}).get("name", "Not started")
    time_block_minutes = priority_to_time_block.get(priority, 30)
    current_time_local = current_time.astimezone(LOCAL_TIMEZONE)
    start_time_local = current_time_local
    end_time_local = start_time_local + datetime.timedelta(minutes=time_block_minutes)
    if status == "Not started [later]":
        start_time_local = current_time.astimezone(LOCAL_TIMEZONE)
        if start_time_local.hour < 18:
            start_time_local = start_time_local.replace(hour=18, minute=0, second=0)
            end_time_local = start_time_local + datetime.timedelta(minutes=30)
            print(f"📌 Adjusting '{task_name}' to start after 6 PM.")
        else:
            end_time_local = start_time_local + datetime.timedelta(minutes=30)
    else:
        end_time_local = current_time + datetime.timedelta(minutes=30)
    if (start_time_local.hour >= 23) and (not allow_late_night_scheduling) and (not ignore_availability_mode):
        print(f"🚨 We have reached {start_time_local.strftime('%I:%M %p')} which is after 11 PM.")
        print("Options:")
        print("[Y] Continue scheduling into late night (no 11 PM limit).")
        print("[T] Move this task (and subsequent) to tomorrow.")
        print("[R] Restart from 9 AM ignoring availability (recycle today's date).")
        print("[Q] Quit scheduling entirely.")
        response = input("Your choice: ").strip().upper()
        if response == 'Y':
            allow_late_night_scheduling = True
            print("Okay, ignoring the 11 PM restriction for the rest of this session!")
        elif response == 'T':
            print(f"Task '{task_name}' deferred to tomorrow.")
            tomorrow_str = (start_time_local.date() + datetime.timedelta(days=1)).isoformat()
            if not test_mode:
                update_date_only(task_id, task_name=task_name, date_str=tomorrow_str)
            return None, allow_late_night_scheduling, ignore_availability_mode, accept_all_mode
        elif response == 'R':
            ignore_availability_mode = True
            print("Okay, from now on we'll keep scheduling from 9 AM ignoring availability.")
        else:
            schedule_complete()
            return None, allow_late_night_scheduling, ignore_availability_mode, accept_all_mode
    if ignore_availability_mode:
        target_date = start_time_local.astimezone(LOCAL_TIMEZONE).date()
        start_time_local_9 = wrap_to_9am_if_needed(start_time_local, target_date)
        if start_time_local_9 != start_time_local:
            start_time_local = start_time_local_9
            end_time_local = start_time_local + datetime.timedelta(minutes=time_block_minutes)
    else:
        overlap_count = 0
        while check_for_overlap(current_schedule, start_time_local, end_time_local):
            overlap_count += 1
            start_time_local = end_time_local
            end_time_local = start_time_local + datetime.timedelta(minutes=time_block_minutes)
        if overlap_count > 0:
            print(f"Adjusted schedule {overlap_count} times to find a free slot.")
    start_time_disp = start_time_local.strftime("%Y-%m-%d %I:%M %p %Z")
    end_time_disp = end_time_local.strftime("%Y-%m-%d %I:%M %p %Z")
    if task_name in scheduled_task_names:
        print(f"🚨 Task '{task_name}' already scheduled. Skipping.")
        return current_time, allow_late_night_scheduling, ignore_availability_mode, accept_all_mode
    if accept_all_mode:
        if not test_mode:
            start_iso = start_time_local.isoformat()
            end_iso = end_time_local.isoformat()
            update_date_time(task_id, task_name=task_name, start_time=start_iso, end_time=end_iso, priority=priority)
            print(f"[Accept All] Task '{task_name}' scheduled from {start_time_disp} to {end_time_disp}.")
            task["properties"]["Due"]["date"]["start"] = start_iso
            task["properties"]["Due"]["date"]["end"] = end_iso
            if task not in current_schedule:
                current_schedule.append(task)
        return end_time_local.astimezone(datetime.timezone.utc), allow_late_night_scheduling, ignore_availability_mode, accept_all_mode
    print(f"\n{'='*50}")
    print(f"Task: '{task_name}' (Priority: {priority})")
    print(f"Proposed Start: {start_time_disp}, End: {end_time_disp} ({time_block_minutes} mins)")
    print("[Y] Apply | [S] Tomorrow | [X] Deprecated | [C] Complete | [H] High | [W] +1 Week | [R] Rename")
    print("Or type a time like '9pm' to override, or type 'ACCEPT ALL' to apply all remaining automatically:")
    print(f"{'='*50}")
    scheduled_task_names.add(task_name)
    while True:
        user_input = input("Your choice: ").strip().upper()
        if user_input == "ACCEPT ALL":
            print("✅ Switching to 'Accept All' mode for this and remaining tasks.")
            accept_all_mode = True
            if not test_mode:
                start_iso = start_time_local.isoformat()
                end_iso = end_time_local.isoformat()
                update_date_time(task_id, task_name=task_name, start_time=start_iso, end_time=end_iso, priority=priority)
                print(f"Task '{task_name}' scheduled from {start_time_disp} to {end_time_disp}.")
                if task not in current_schedule:
                    current_schedule.append(task)
            return end_time_local.astimezone(datetime.timezone.utc), allow_late_night_scheduling, ignore_availability_mode, accept_all_mode
        if user_input in ["Y", "S", "X", "C", "H", "W"]:
            break
        parsed_time = None
        for fmt in ["%I%p", "%I:%M%p", "%H:%M"]:
            try:
                today = start_time_local.date()
                new_time = datetime.datetime.strptime(user_input, fmt).time()
                new_start_local = LOCAL_TIMEZONE.localize(datetime.datetime.combine(today, new_time))
                parsed_time = new_start_local
                break
            except ValueError:
                continue
        if parsed_time:
            start_time_local = parsed_time
            end_time_local = start_time_local + datetime.timedelta(minutes=time_block_minutes)
            if ignore_availability_mode:
                start_time_local_9 = wrap_to_9am_if_needed(start_time_local, start_time_local.date())
                if start_time_local_9 != start_time_local:
                    start_time_local = start_time_local_9
                    end_time_local = start_time_local_9 + datetime.timedelta(minutes=time_block_minutes)
            else:
                overlap_count = 0
                while check_for_overlap(current_schedule, start_time_local, end_time_local):
                    overlap_count += 1
                    start_time_local = end_time_local
                    end_time_local = start_time_local + datetime.timedelta(minutes=time_block_minutes)
                if overlap_count > 0:
                    print(f"Adjusted schedule {overlap_count} times to avoid overlap.")
            start_time_disp = start_time_local.strftime("%Y-%m-%d %I:%M %p %Z")
            end_time_disp = end_time_local.strftime("%Y-%m-%d %I:%M %p %Z")
            print(f"\nNew Start: {start_time_disp}, End: {end_time_disp}")
            print("[Y] Apply | [S] Tomorrow | [X] Deprecated | [C] Complete | [H] High | [W] +1 Week")
        else:
            print("Invalid time format. Try again.")
    if user_input == "Y":
        if not test_mode:
            start_iso = start_time_local.isoformat()
            end_iso = end_time_local.isoformat()
            update_date_time(task_id, task_name=task_name, start_time=start_iso, end_time=end_iso, priority=priority)
            print(f"Task '{task_name}' scheduled from {start_time_disp} to {end_time_disp}.")
            if task not in current_schedule:
                current_schedule.append(task)
        return end_time_local.astimezone(datetime.timezone.utc), allow_late_night_scheduling, ignore_availability_mode, accept_all_mode
    elif user_input == "R":
        new_name = input("Enter new task name: ").strip()
        rename_task(task_id, new_name)
        print(f"Task renamed to '{new_name}'.")
        task_name = new_name
        task["properties"]["Name"]["title"][0]["text"]["content"] = new_name
        return schedule_single_task(
            task,
            current_time,
            test_mode,
            current_schedule,
            scheduled_task_names,
            accept_all_mode=accept_all_mode,
            allow_late_night_scheduling=allow_late_night_scheduling,
            ignore_availability_mode=ignore_availability_mode
        )
    elif user_input == "S":
        print(f"Task '{task_name}' deferred to tomorrow.")
        tomorrow_str = (start_time_local.date() + datetime.timedelta(days=1)).isoformat()
        if not test_mode:
            update_date_only(task_id, task_name=task_name, date_str=tomorrow_str)
        return None, allow_late_night_scheduling, ignore_availability_mode, accept_all_mode
    elif user_input in ("X", "C"):
        if not test_mode:
            update_date_time(task_id, status="Done", task_name=task_name)
            print(f"Task '{task_name}' Done.")
            if task in current_schedule:
                current_schedule.remove(task)
        return end_time_local.astimezone(datetime.timezone.utc), allow_late_night_scheduling, ignore_availability_mode, accept_all_mode
    elif user_input == "H":
        if not test_mode:
            start_iso = start_time_local.isoformat()
            end_iso = end_time_local.isoformat()
            update_date_time(task_id, task_name=task_name, start_time=start_iso, end_time=end_iso, priority="High")
            print(f"Task '{task_name}' High priority and scheduled.")
            if task not in current_schedule:
                current_schedule.append(task)
        return end_time_local.astimezone(datetime.timezone.utc), allow_late_night_scheduling, ignore_availability_mode, accept_all_mode
    elif user_input == "W":
        one_week_later_date = (start_time_local.date() + datetime.timedelta(days=7)).isoformat()
        if not test_mode:
            update_date_only(task_id, task_name=task_name, date_str=one_week_later_date)
        print(f"Moved '{task_name}' one week later.")
        return None, allow_late_night_scheduling, ignore_availability_mode, accept_all_mode

def schedule_tasks_in_pattern(tasks, test_mode=False, starting_time=None, scheduled_task_names=None):
    if scheduled_task_names is None:
        scheduled_task_names = set()
    print(f"\nYou have {len(tasks)} tasks to schedule.")
    high_priority_tasks = []
    low_priority_tasks = []
    for t in tasks:
        props = t.get("properties", {})
        priority = props.get("Priority", {}).get("status", {}).get("name", "Low")
        done = props.get("Done", {}).get("checkbox", False)
        if done:
            continue
        if priority in ["High", "Must Be Done Today"]:
            high_priority_tasks.append(t)
        else:
            low_priority_tasks.append(t)
    high_priority_tasks.sort(key=lambda x: x.get("properties", {}).get("Priority", {}).get("status", {}).get("name") != "Must Be Done Today")
    current_time = starting_time or datetime.datetime.now(datetime.timezone.utc)
    current_schedule = fetch_current_schedule()
    allow_late_night_scheduling = False
    ignore_availability_mode = False
    accept_all_mode = False
    while high_priority_tasks:
        task = high_priority_tasks.pop(0)
        new_time, allow_late_night_scheduling, ignore_availability_mode, accept_all_mode = schedule_single_task(
            task,
            current_time,
            test_mode,
            current_schedule,
            scheduled_task_names,
            accept_all_mode=accept_all_mode,
            allow_late_night_scheduling=allow_late_night_scheduling,
            ignore_availability_mode=ignore_availability_mode
        )
        if new_time is None:
            return
        current_time = new_time
    while low_priority_tasks:
        task = low_priority_tasks.pop(0)
        new_time, allow_late_night_scheduling, ignore_availability_mode, accept_all_mode = schedule_single_task(
            task,
            current_time,
            test_mode,
            current_schedule,
            scheduled_task_names,
            accept_all_mode=accept_all_mode,
            allow_late_night_scheduling=allow_late_night_scheduling,
            ignore_availability_mode=ignore_availability_mode
        )
        if new_time is None:
            return
        current_time = new_time

# --------------------------- MAIN ENTRY POINT FOR SCHEDULING ---------------------------
def assign_dues_and_blocks(test_mode=False):
    """
    Main entry point to fetch tasks, triage, create 'Schedule Day' task, update tasks based on calendar events,
    and schedule everything with date/time blocks.
    """
    # Prompt for scheduling day
    schedule_day_input = input("When do you want to schedule for? (today, tomorrow): ").strip().lower()
    if schedule_day_input == "tomorrow":
        schedule_tomorrow()
        schedule_complete()
        return
    elif schedule_day_input != "today":
        print("Unrecognized choice. Defaulting to scheduling for today.")
    # --- New: Fetch calendar events and update Co-Lab tasks based on TEC Office Hours ---
    try:
        cal_events = fetch_calendar_events()  # Defaults to today
        office_hours = get_tec_office_hours_event(cal_events)
        if office_hours:
            print("TEC Office Hours event found; updating 'Co-Lab' tasks accordingly.")
            update_colab_tasks_due(office_hours)
        else:
            print("No TEC Office Hours event found for today.")
    except Exception as e:
        print("Failed to fetch or update calendar events:", e)
    # -------------------------------------------------------------------------------
    # Round to next half-hour
    local_now = datetime.datetime.now(LOCAL_TIMEZONE).replace(second=0, microsecond=0)
    if local_now.minute < 30:
        local_now = local_now.replace(minute=30)
    else:
        local_now = local_now.replace(minute=0) + datetime.timedelta(hours=1)
    current_time_utc = local_now.astimezone(datetime.timezone.utc)
    tasks = fetch_all_tasks_sorted_by_priority_created()
    create_schedule_day_task()
    triage_unassigned_tasks()
    tasks_post_triage = fetch_all_tasks_sorted_by_created(assigned_time_equals=False)
    print(f"\nYou have {len(tasks_post_triage)} tasks after triage.")
    current_schedule = fetch_current_schedule()
    show_schedule_overview(current_schedule)
    updated_tasks = fetch_all_tasks_sorted_by_created(assigned_time_equals=False)
    non_deprecated_tasks = [t for t in updated_tasks if t.get("properties", {}).get("Status", {}).get("status", {}).get("name") != "Deprecated"]
    seen_ids = set()
    unique_tasks = []
    for t in non_deprecated_tasks:
        if t["id"] not in seen_ids:
            seen_ids.add(t["id"])
            unique_tasks.append(t)
    if unique_tasks:
        schedule_tasks_in_pattern(unique_tasks, test_mode=test_mode, starting_time=current_time_utc)
    else:
        print("\nNo tasks to schedule after cleanup.")
    schedule_complete()

# -------------------------------------------------------------------
#  Below is the prompt_toolkit-based TUI for unassigned tasks
# -------------------------------------------------------------------
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

class TaskSchedulerTUI:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tasks = []
        self.current_index = 0
        self.load_tasks()
        self.kb = KeyBindings()
        @self.kb.add('c-q')
        def exit_(event):
            event.app.exit()
        @self.kb.add('up')
        def up_(event):
            if self.current_index > 0:
                self.current_index -= 1
        @self.kb.add('down')
        def down_(event):
            if self.current_index < len(self.tasks) - 1:
                self.current_index += 1
        @self.kb.add('enter')
        def select_(event):
            if self.tasks:
                self.handle_task_action(self.current_index)
        self.layout = self.create_layout()
        self.app = Application(layout=Layout(self.layout), key_bindings=self.kb, full_screen=True, style=self.style())
    def load_tasks(self):
        self.tasks = fetch_unassigned_tasks()
    def style(self):
        return Style.from_dict({
            "status": "reverse",
            "frame": "bg:#000000 #ffffff",
            "task": "#ff9d00",
            "highlighted": "bg:#444444 #ffffff"
        })
    def create_layout(self):
        def get_formatted_tasks():
            lines = []
            for i, task in enumerate(self.tasks):
                name = get_task_name(task.get("properties", {}))
                prefix = "→ " if i == self.current_index else "  "
                style = "class:highlighted" if i == self.current_index else "class:task"
                lines.append((style, prefix + name))
            if not lines:
                lines = [("class:task", "No unassigned tasks.")]
            return lines
        task_list_window = Window(content=FormattedTextControl(get_formatted_tasks), wrap_lines=False)
        body = HSplit([
            Window(height=1, content=FormattedTextControl("Unassigned Tasks (Up/Down, Enter, Ctrl-Q to quit)")),
            task_list_window
        ])
        return body
    def run(self):
        self.app.run()
    def handle_task_action(self, index):
        task = self.tasks[index]
        name = get_task_name(task.get("properties", {}))
        print(f"\nSelected task: {name}")
        print("[1] Low")
        print("[2] High")
        print("[c] Deprecated")
        print("[x] Done")
        print("[s] Someday")
        choice = input("Your choice: ").strip().lower()
        priority_mapping = {"1": "Low", "2": "High", "c": "Deprecated", "x": "Done", "s": "Someday"}
        if choice in priority_mapping:
            chosen = priority_mapping[choice]
            if chosen in ["Deprecated", "Done"]:
                update_date_time(task["id"], task_name=name, status=chosen)
            else:
                update_date_time(task["id"], task_name=name, priority=chosen)
            print(f"Task '{name}' updated → {chosen}")
        else:
            print("Invalid choice.")
        self.load_tasks()

def run_gui():
    scheduler_tui = TaskSchedulerTUI()
    scheduler_tui.run()

if __name__ == "__main__":
    print("What would you like to do?")
    print("[1] Just triage unassigned tasks")
    print("[2] Schedule tasks")
    print("[3] Both triage and schedule")
    user_choice = input("Select an option: ").strip().lower()
    if user_choice == "1":
        triage_unassigned_tasks()
    elif user_choice == "2":
        assign_dues_and_blocks(test_mode=False)
    elif user_choice == "3":
        triage_unassigned_tasks()
        assign_dues_and_blocks(test_mode=False)
    else:
        print("Invalid selection. Exiting.")