import datetime
import requests
from dotenv import load_dotenv
import os
import logging
import pytz
import tzlocal
import calendar

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

# Properties
PROPERTY_DUE = "Due"
PROPERTY_PRIORITY = "Priority"
PROPERTY_STATUS = "Status"
PROPERTY_DONE = "Done"
PROPERTY_EFFORT = "Level of Effort"  # New property for time-block calculations

# Initialize Time Zone
LOCAL_TIMEZONE = tzlocal.get_localzone()

# Load environment variables
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

# Example mapping from Level of Effort to scheduling block duration
effort_to_time_block = {
    "Low": 15,      # 15 minutes
    "Medium": 30,   # 30 minutes
    "High": 60      # 60 minutes
}

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


# --------------------------- UTILS & HELPERS ---------------------------

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
    """
    Expects a string like '2025-02-10' or '2025/02/10'.
    You can adapt this for various formats if needed.
    """
    try:
        return datetime.datetime.strptime(input_str, "%Y-%m-%d").date()
    except ValueError:
        # Try alternate format or return None
        try:
            return datetime.datetime.strptime(input_str, "%Y/%m/%d").date()
        except ValueError:
            return None

def schedule_complete():
    print("Scheduling is complete!")


# --------------------------- API CALLS ---------------------------

def fetch_tasks(filter_payload, sorts_payload):
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "filter": filter_payload,
        "sorts": sorts_payload,
        "page_size": 500
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get("results", [])
    else:
        logger.error(f"Failed to fetch tasks. Status: {response.status_code}, {response.text}")
        return []

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
    # target_date should be a string in 'YYYY-MM-DD' format
    # Defaults to today's date if no target_date provided
    if target_date is None:
        target_date = datetime.datetime.now().date().isoformat()

    filter_payload = {
        "and": [
            {
                "property": "Due",
                "date": {
                    "on_or_before": target_date  # So tasks due on or before the chosen date
                }
            },
            {
                "property": "Assigned time",
                "checkbox": {
                    "equals": assigned_time_equals
                }
            },
            {
                "property": "Done",
                "checkbox": {
                    "equals": False
                }
            },
            {
                "property": "Priority",
                "status": {
                    "does_not_equal": "Someday"
                }
            },
            {
                "property": "Priority",
                "status": {
                    "does_not_equal": "Unassigned"
                }
            }
        ]
    }

    sorts_payload = [
        {"timestamp": "created_time", "direction": "ascending"}
    ]

    return fetch_tasks(filter_payload, sorts_payload)

def fetch_current_schedule(target_date=None):
    """
    Fetch tasks assigned_time_equals=True, restricted to the chosen date.
    """
    if target_date is None:
        target_date = datetime.datetime.now().date().isoformat()

    filter_payload = {
        "and": [
            {
                "property": "Due",
                "date": {
                    "on_or_before": target_date
                }
            },
            {
                "property": "Due",
                "date": {
                    "on_or_after": target_date
                }
            },
            {
                "property": "Assigned time",
                "checkbox": {
                    "equals": True
                }
            },
            {
                "property": "Done",
                "checkbox": {
                    "equals": False
                }
            }
        ]
    }

    sorts_payload = [
        {"timestamp": "created_time", "direction": "ascending"}
    ]

    return fetch_tasks(filter_payload, sorts_payload)


def fetch_unassigned_tasks():
    filter_payload = {
        "and": [
            {"property": "Priority", "status": {"equals": "Unassigned"}},
            {"property": "Status", "status": {"does_not_equal": "Done"}},
            {"property": "Status", "status": {"does_not_equal": "Handed Off"}},
            {"property": "Status", "status": {"does_not_equal": "Deprecated"}},
            {"property": "Status", "status": {"does_not_equal": "Waiting on Reply"}},
            {"property": "Status", "status": {"does_not_equal": "Waiting on other task"}},
            {"property": "Done", "checkbox": {"equals": False}},
        ]
    }
    sorts_payload = [
        {"timestamp": "created_time", "direction": "ascending"}
    ]
    return fetch_tasks(filter_payload, sorts_payload)


# --------------------------- CREATE 'SCHEDULE DAY' TASK ---------------------------

def create_schedule_day_task(target_date_str=None):
    """
    Optionally create a "Schedule Day" task for the chosen date.
    If no date is passed, default to today.
    """
    if not target_date_str:
        target_date_str = datetime.datetime.now(LOCAL_TIMEZONE).date().isoformat()

    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    filter_payload = {
        "filter": {
            "and": [
                {
                    "property": "Name",
                    "title": {
                        "equals": "Schedule Day"
                    }
                },
                {
                    "property": "Due",
                    "date": {
                        "on_or_before": target_date_str
                    }
                },
                {
                    "property": "Due",
                    "date": {
                        "on_or_after": target_date_str
                    }
                }
            ]
        }
    }

    response = requests.post(url, headers=headers, json=filter_payload)
    if response.status_code == 200:
        existing_results = response.json().get("results", [])
        if existing_results:
            print(f"🗓️ 'Schedule Day' task already exists for {target_date_str}. Skipping creation.")
            return
    else:
        logger.error(f"Failed to fetch 'Schedule Day' tasks. Status: {response.status_code}, {response.text}")
        return

    # Create the 'Schedule Day' task
    now = datetime.datetime.now(datetime.timezone.utc)
    due = (now + datetime.timedelta(minutes=30)).isoformat()
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": "Schedule Day"}}]},
            "Class": {"select": {"name": "Admin"}},
            "Due": {"date": {"start": target_date_str}},  # Only date, no end time
            "Priority": {"status": {"name": "High"}}
        }
    }
    create_resp = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
    if create_resp.status_code == 200:
        logger.info(f"'Schedule Day' task created successfully for {target_date_str}.")
    else:
        logger.error(f"Failed to create 'Schedule Day' task. Status: {create_resp.status_code}, {create_resp.text}")


# --------------------------- UPDATE FUNCTIONS ---------------------------

def update_date_only(task_id, task_name=None, date_str=None):
    if not date_str:
        return
    date_only = format_date_iso(date_str) or date_str
    url = f"https://api.notion.com/v1/pages/{task_id}"
    payload = {
        "properties": {
            "Due": {
                "date": {
                    "start": date_only
                }
            }
        }
    }
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

def update_level_of_effort(task_id, effort, task_name=None):
    """
    Updates the 'Level of Effort' property in Notion,
    which we'll use to calculate the time block.
    """
    url = f"https://api.notion.com/v1/pages/{task_id}"
    payload = {
        "properties": {
            PROPERTY_EFFORT: {
                "select": {"name": effort}
            }
        }
    }
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code != 200:
        logger.error(f"Failed to update Level of Effort for '{task_name}'. {response.status_code}: {response.text}")
    else:
        logger.info(f"Task '{task_name}' Level of Effort updated to: {effort}")


# --------------------------- LEVEL OF EFFORT + TRIAGE ---------------------------

def triage_unassigned_tasks():
    priority_mapping = {
        "1": "Low",
        "2": "Medium",
        "3": "High",
        "c": "Deprecated",
        "x": "Done",
        "s": "Someday"
    }

    # For level of effort
    effort_mapping = {
        "1": "Low",     # 15 min
        "2": "Medium",  # 30 min
        "3": "High"     # 60 min
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

        print(f"\n📝 Task: '{task_name}' is 'Unassigned'.")
        print("Priority Options:")
        print("[1] Low (💡)")
        print("[2] Medium (♻️)")
        print("[3] High (🔥)")
        print("[c] Deprecated (🗑️)")
        print("[x] Done (✅)")
        print("[s] Someday (🌥️)")
        print("[r] Rename Task")

        user_choice = input("\nChoose priority or status [1/2/3/c/x/s/r]: ").strip().lower()

        # Rename if needed
        if user_choice == "r":
            new_name = input("Enter new task name: ").strip()
            rename_task(task_id, new_name)
            print(f"Task renamed to '{new_name}'.")
            task_name = new_name
            user_choice = input("\nChoose priority or status [1/2/3/c/x/s]: ").strip().lower()

        # Handle status updates
        if user_choice == "c":
            update_date_time(task_id, task_name=task_name, status="Deprecated")
            print(f"🗑️ '{task_name}' archived.")
            continue
        elif user_choice == "x":
            update_date_time(task_id, task_name=task_name, status="Done")
            print(f"✅ '{task_name}' Done.")
            continue
        elif user_choice == "s":
            update_date_time(task_id, task_name=task_name, priority="Someday")
            print(f"🌥️ '{task_name}' set to Someday.")
            continue

        # Handle priority updates
        if user_choice in priority_mapping:
            chosen_priority = priority_mapping[user_choice]
            update_date_time(task_id, task_name=task_name, priority=chosen_priority)
            print(f"📌 '{task_name}' priority: {chosen_priority}")

            # Now ask for Level of Effort
            print("\nSpecify the Level of Effort for scheduling:")
            print("[1] Low (15 min)")
            print("[2] Medium (30 min)")
            print("[3] High (60 min)")

            while True:
                loe_choice = input("\nLevel of Effort [1/2/3]: ").strip()
                if loe_choice in effort_mapping:
                    selected_effort = effort_mapping[loe_choice]
                    update_level_of_effort(task_id, selected_effort, task_name)
                    print(f"💡 '{task_name}' effort: {selected_effort}")
                    break
                else:
                    print("⚠️ Invalid effort choice. Please choose 1, 2, or 3.")

        previously_triaged.add(task_name)


# --------------------------- SCHEDULING LOGIC ---------------------------
# We still default to a single-day scheduling window (9am - 11pm),
# but now for the user-chosen date.

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

def calculate_available_time_blocks(current_schedule, schedule_date, start_hour=9, end_hour=23):
    """
    Returns free blocks for the user-chosen schedule_date (9am - 11pm).
    """
    # Make a local datetime for that date at 9am
    start_of_day = datetime.datetime.combine(schedule_date, datetime.time(hour=start_hour), tzinfo=LOCAL_TIMEZONE)
    end_of_day = datetime.datetime.combine(schedule_date, datetime.time(hour=end_hour), tzinfo=LOCAL_TIMEZONE)

    now_local = datetime.datetime.now(LOCAL_TIMEZONE)
    # If the chosen date is 'today' and it's already past 9am, start from current time
    if schedule_date == now_local.date():
        current_time = max(start_of_day, now_local)
    else:
        # Otherwise, always start from 9am on that date
        current_time = start_of_day

    busy_periods = []
    for task in current_schedule:
        props = task.get("properties", {})
        due = props.get("Due", {}).get("date", {})
        start = due.get("start")
        end = due.get("end")

        if start and end:
            busy_start = datetime.datetime.fromisoformat(start).astimezone(LOCAL_TIMEZONE)
            busy_end = datetime.datetime.fromisoformat(end).astimezone(LOCAL_TIMEZONE)
            # Only consider if the busy period is within the same date
            if busy_start.date() == schedule_date:
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

def display_available_time_blocks(free_blocks, schedule_date):
    print(f"\n🕒 **Available Time Blocks for {schedule_date}**:")
    if not free_blocks:
        print("🚫 No free time left for that day.")
        return
    for start, end in free_blocks:
        print(f"✅ {start.strftime('%I:%M %p')} to {end.strftime('%I:%M %p')}")

def schedule_single_task(task,
                         current_time,
                         test_mode,
                         current_schedule,
                         scheduled_task_names,
                         accept_all_mode=False):
    props = task.get("properties", {})
    task_id = task["id"]
    task_name = get_task_name(props)
    priority = props.get("Priority", {}).get("status", {}).get("name", "Low")
    effort_prop = props.get(PROPERTY_EFFORT) or {}
    select_prop = effort_prop.get("select") or {}
    effort = select_prop.get("name")

    # If empty, prompt user to assign LOE right now
    if not effort:
        print(f"Task '{task_name}' has no Level of Effort set.")
        while True:
            user_input = input("Please choose a Level of Effort [L (Low), M (Medium), H (High)]: ").strip().upper()
            if user_input in ["L", "M", "H", "LOW", "MEDIUM", "HIGH"]:
                if user_input == "L":
                    effort = "Low"
                elif user_input == "M":
                    effort = "Medium"
                elif user_input == "H":
                    effort = "High"
                else:
                    effort = user_input.capitalize()
                update_level_of_effort(task_id, effort, task_name=task_name)
                print(f"Task '{task_name}' LOE set to '{effort}'.")
                break
            else:
                print("Invalid choice. Type L, M, H, or the full name (Low, Medium, High).")
    time_block_minutes = effort_to_time_block.get(effort, 30)

    current_time_local = current_time.astimezone(LOCAL_TIMEZONE)
    start_time_local = current_time_local
    end_time_local = start_time_local + datetime.timedelta(minutes=time_block_minutes)

    # Check for day boundary (no scheduling beyond 11pm)
    if end_time_local.hour >= 23:
        print(f"⚠️ Task '{task_name}' cannot be scheduled fully before 11pm ends.")
        print("Either skip it or mark it done/deprecated. Or push it to tomorrow/+1 week.")
        user_input = input("[S] Skip | [D] Done | [X] Deprecated | [T] Tomorrow | [W] Next Week: ").strip().upper()
        if user_input == "D":
            if not test_mode:
                update_date_time(task_id, status="Done", task_name=task_name)
            print(f"'{task_name}' marked Done.")
        elif user_input == "X":
            if not test_mode:
                update_date_time(task_id, status="Deprecated", task_name=task_name)
            print(f"'{task_name}' marked Deprecated.")
        elif user_input == "T":
            tomorrow = (start_time_local + datetime.timedelta(days=1)).date().isoformat()
            if not test_mode:
                update_date_only(task_id, task_name=task_name, date_str=tomorrow)
            print(f"Task '{task_name}' rescheduled to tomorrow ({tomorrow}).")
        elif user_input == "W":
            next_week = (start_time_local + datetime.timedelta(weeks=1)).date().isoformat()
            if not test_mode:
                update_date_only(task_id, task_name=task_name, date_str=next_week)
            print(f"Task '{task_name}' rescheduled +1 week ({next_week}).")
        else:
            print(f"'{task_name}' skipped for now.")
        return None, accept_all_mode

    # Resolve overlapping blocks by pushing start time forward
    overlap_count = 0
    while check_for_overlap(current_schedule, start_time_local, end_time_local):
        overlap_count += 1
        start_time_local = end_time_local
        end_time_local = start_time_local + datetime.timedelta(minutes=time_block_minutes)
        if end_time_local.hour >= 23:
            print(f"⚠️ Ran out of time blocks for '{task_name}' before 11pm.")
            user_input = input("[S] Skip | [D] Done | [X] Deprecated | [T] Tomorrow | [W] Next Week: ").strip().upper()
            if user_input == "D":
                if not test_mode:
                    update_date_time(task_id, status="Done", task_name=task_name)
                print(f"'{task_name}' marked Done.")
            elif user_input == "X":
                if not test_mode:
                    update_date_time(task_id, status="Deprecated", task_name=task_name)
                print(f"'{task_name}' marked Deprecated.")
            elif user_input == "T":
                tomorrow = (start_time_local + datetime.timedelta(days=1)).date().isoformat()
                if not test_mode:
                    update_date_only(task_id, task_name=task_name, date_str=tomorrow)
                print(f"Task '{task_name}' rescheduled to tomorrow ({tomorrow}).")
            elif user_input == "W":
                next_week = (start_time_local + datetime.timedelta(weeks=1)).date().isoformat()
                if not test_mode:
                    update_date_only(task_id, task_name=task_name, date_str=next_week)
                print(f"Task '{task_name}' rescheduled +1 week ({next_week}).")
            else:
                print(f"'{task_name}' skipped for now.")
            return None, accept_all_mode

    if overlap_count > 0:
        print(f"Moved start time forward {overlap_count} times for '{task_name}' to avoid overlap.")

    start_time_disp = start_time_local.strftime("%Y-%m-%d %I:%M %p %Z")
    end_time_disp = end_time_local.strftime("%Y-%m-%d %I:%M %p %Z")

    if task_name in scheduled_task_names:
        print(f"🚨 Task '{task_name}' is already scheduled. Skipping.")
        return current_time, accept_all_mode

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
        return end_time_local.astimezone(datetime.timezone.utc), accept_all_mode

    print(f"\n{'='*50}")
    print(f"Task: '{task_name}' (Priority: {priority}, Effort: {effort})")
    print(f"Proposed Start: {start_time_disp}, End: {end_time_disp} ({time_block_minutes} mins)")
    print("[Y] Apply | [X] Deprecated | [D] Done | [R] Rename | [T] Tomorrow | [W] +1 Week | [ACCEPT ALL]")
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
            return end_time_local.astimezone(datetime.timezone.utc), accept_all_mode

        # Time override
        parsed_time = None
        for fmt in ["%I%p", "%I:%M%p", "%H:%M"]:
            try:
                day_only = start_time_local.date()
                new_time = datetime.datetime.strptime(user_input, fmt).time()
                new_start_local = LOCAL_TIMEZONE.localize(datetime.datetime.combine(day_only, new_time))
                parsed_time = new_start_local
                break
            except ValueError:
                continue

        if parsed_time:
            start_time_local = parsed_time
            end_time_local = start_time_local + datetime.timedelta(minutes=time_block_minutes)
            # Check overlap again
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
            print("[Y] Apply | [X] Deprecated | [D] Done | [R] Rename | [T] Tomorrow | [W] +1 Week")
        else:
            # Standard options
            if user_input == "Y":
                if not test_mode:
                    start_iso = start_time_local.isoformat()
                    end_iso = end_time_local.isoformat()
                    update_date_time(task_id, task_name=task_name, start_time=start_iso, end_time=end_iso, priority=priority)
                    print(f"Task '{task_name}' scheduled from {start_time_disp} to {end_time_disp}.")
                    if task not in current_schedule:
                        current_schedule.append(task)
                return end_time_local.astimezone(datetime.timezone.utc), accept_all_mode
            elif user_input == "X":
                if not test_mode:
                    update_date_time(task_id, task_name=task_name, status="Deprecated")
                print(f"'{task_name}' marked Deprecated.")
                return None, accept_all_mode
            elif user_input == "D":
                if not test_mode:
                    update_date_time(task_id, status="Done", task_name=task_name)
                print(f"'{task_name}' marked Done.")
                return end_time_local.astimezone(datetime.timezone.utc), accept_all_mode
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
                    accept_all_mode=accept_all_mode
                )
            elif user_input == "T":
                tomorrow = (start_time_local + datetime.timedelta(days=1)).date().isoformat()
                if not test_mode:
                    update_date_only(task_id, task_name=task_name, date_str=tomorrow)
                print(f"Task '{task_name}' rescheduled to tomorrow ({tomorrow}).")
                return None, accept_all_mode
            elif user_input == "W":
                next_week = (start_time_local + datetime.timedelta(weeks=1)).date().isoformat()
                if not test_mode:
                    update_date_only(task_id, task_name=task_name, date_str=next_week)
                print(f"Task '{task_name}' rescheduled to +1 week ({next_week}).")
                return None, accept_all_mode
            else:
                print("Invalid choice. Enter a valid option or time override.")


def schedule_tasks_in_pattern(tasks,
                             test_mode=False,
                             starting_time=None,
                             scheduled_task_names=None):
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

    # Keep "Must Be Done Today" tasks first
    high_priority_tasks.sort(
        key=lambda x: x.get("properties", {}).get("Priority", {}).get("status", {}).get("name") != "Must Be Done Today"
    )

    current_time = starting_time or datetime.datetime.now(datetime.timezone.utc)
    current_schedule = []

    # We only fetch tasks that have assigned_time_equals=True for the chosen date
    # if we want to see what's already scheduled. That logic is handled outside
    # and passed in if desired. For now, we've omitted date param to keep it simple.

    current_schedule = fetch_current_schedule(
        target_date=current_time.astimezone(LOCAL_TIMEZONE).date().isoformat()
    )

    accept_all_mode = False

    # Schedule high priority tasks first
    while high_priority_tasks:
        task = high_priority_tasks.pop(0)
        new_time, accept_all_mode = schedule_single_task(
            task,
            current_time,
            test_mode,
            current_schedule,
            scheduled_task_names,
            accept_all_mode=accept_all_mode
        )
        if new_time:
            current_time = new_time

    # Then schedule low priority tasks
    while low_priority_tasks:
        task = low_priority_tasks.pop(0)
        new_time, accept_all_mode = schedule_single_task(
            task,
            current_time,
            test_mode,
            current_schedule,
            scheduled_task_names,
            accept_all_mode=accept_all_mode
        )
        if new_time:
            current_time = new_time

    schedule_complete()


# --------------------------- MAIN ENTRY POINT ---------------------------

def assign_dues_and_blocks(test_mode=False):
    """
    Main entry point to fetch tasks, triage them, create 'Schedule Day' task,
    and schedule everything with date/time blocks for a chosen date.
    """
    # Ask user which date they want to schedule tasks for
    print("\nWhich date would you like to schedule tasks for?")
    print("[1] Today")
    print("[2] Tomorrow")
    print("[3] Custom Date (YYYY-MM-DD)")
    date_choice = input("Pick an option: ").strip()

    if date_choice == "1":
        schedule_date = datetime.datetime.now().date()
    elif date_choice == "2":
        schedule_date = datetime.datetime.now().date() + datetime.timedelta(days=1)
    elif date_choice == "3":
        user_input = input("Enter a date (YYYY-MM-DD): ").strip()
        parsed = parse_custom_date(user_input)
        if parsed:
            schedule_date = parsed
        else:
            print("Invalid date format. Defaulting to today.")
            schedule_date = datetime.datetime.now().date()
    else:
        print("Invalid choice. Defaulting to today.")
        schedule_date = datetime.datetime.now().date()

    # Round to next half-hour from 9am (or current time if it's the same day)
    local_now = datetime.datetime.now(LOCAL_TIMEZONE)
    # Start at 9:00 for that date
    chosen_date_9am = datetime.datetime.combine(schedule_date, datetime.time(hour=9), tzinfo=LOCAL_TIMEZONE)

    if schedule_date == local_now.date():
        # If scheduling for today, start from the next half hour or local time
        if local_now.minute < 30:
            local_now = local_now.replace(second=0, microsecond=0, minute=30)
        else:
            local_now = (local_now.replace(second=0, microsecond=0) + datetime.timedelta(hours=1)).replace(minute=0)
        start_time_local = max(chosen_date_9am, local_now)
    else:
        # If scheduling for another day, just start from 9:00
        start_time_local = chosen_date_9am

    current_time_utc = start_time_local.astimezone(datetime.timezone.utc)

    # Create "Schedule Day" if needed
    create_schedule_day_task(target_date_str=schedule_date.isoformat())

    # Triage unassigned tasks
    triage_unassigned_tasks()

    # Now fetch tasks for scheduling
    tasks_post_triage = fetch_all_tasks_sorted_by_created(
        assigned_time_equals=False,
        target_date=schedule_date.isoformat()
    )
    print(f"\nYou have {len(tasks_post_triage)} tasks after triage for {schedule_date}.")

    current_schedule = fetch_current_schedule(target_date=schedule_date.isoformat())
    free_blocks = calculate_available_time_blocks(current_schedule, schedule_date, start_hour=9, end_hour=23)
    display_available_time_blocks(free_blocks, schedule_date)

    # Filter out any tasks marked 'Deprecated' before scheduling
    non_deprecated_tasks = [
        t for t in tasks_post_triage
        if t.get("properties", {}).get("Status", {}).get("status", {}).get("name") != "Deprecated"
    ]

    seen_ids = set()
    unique_tasks = []
    for t in non_deprecated_tasks:
        if t["id"] not in seen_ids:
            seen_ids.add(t["id"])
            unique_tasks.append(t)

    if unique_tasks:
        schedule_tasks_in_pattern(
            unique_tasks,
            test_mode=test_mode,
            starting_time=current_time_utc
        )
    else:
        print(f"\nNo tasks to schedule after cleanup for {schedule_date}.")
        schedule_complete()


# -------------------------------------------------------------------
#  Below is the prompt_toolkit-based TUI for unassigned tasks
# -------------------------------------------------------------------

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
        self.app = Application(
            layout=Layout(self.layout),
            key_bindings=self.kb,
            full_screen=True,
            style=self.style()
        )

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

        task_list_window = Window(
            content=FormattedTextControl(get_formatted_tasks),
            wrap_lines=False
        )

        body = HSplit([
            Window(
                height=1,
                content=FormattedTextControl("Unassigned Tasks (Up/Down, Enter, Ctrl-Q to quit)"),
            ),
            task_list_window
        ])
        return body

    def run(self):
        self.app.run()

    def handle_task_action(self, index):
        task = self.tasks[index]
        name = get_task_name(task.get("properties", {}))
        task_id = task["id"]
        print(f"\nSelected task: {name}")
        print("[1] Low priority")
        print("[2] High priority")
        print("[c] Deprecated")
        print("[x] Done")
        print("[s] Someday")
        print("[r] Rename Task")

        choice = input("Your choice: ").strip().lower()

        priority_mapping = {
            "1": "Low",
            "2": "High",
            "c": "Deprecated",
            "x": "Done",
            "s": "Someday"
        }

        if choice == "r":
            new_name = input("Enter new task name: ").strip()
            rename_task(task_id, new_name)
            print(f"Task renamed to '{new_name}'.")
        elif choice in priority_mapping:
            chosen = priority_mapping[choice]
            if chosen in ["Deprecated", "Done"]:
                update_date_time(task_id, task_name=name, status=chosen)
            elif chosen == "Someday":
                update_date_time(task_id, task_name=name, priority=chosen)
            else:
                update_date_time(task_id, task_name=name, priority=chosen)
                print("\nChoose Level of Effort:")
                print("[1] Low (15 min)")
                print("[2] Medium (30 min)")
                print("[3] High (60 min)")
                while True:
                    loe_choice = input("LOE choice: ").strip()
                    effort_mapping = {"1": "Low", "2": "Medium", "3": "High"}
                    if loe_choice in effort_mapping:
                        selected_effort = effort_mapping[loe_choice]
                        update_level_of_effort(task_id, selected_effort, task_name=name)
                        break
                    else:
                        print("Invalid Level of Effort choice.")
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