import datetime
import requests
from dotenv import load_dotenv
import os
import logging
import pytz

PROPERTY_DUE = "Due"
PROPERTY_PRIORITY = "Priority"
PROPERTY_STATUS = "Status"
PROPERTY_DONE = "Done"

LOCAL_TIMEZONE = pytz.timezone("America/New_York")

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

priority_to_time_block = {
    "Low": 15,
    "Medium": 30,
    "High": 60,
    "Must Be Done Today": 120
}

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def get_task_name(properties):
    try:
        return properties.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Unnamed Task")
    except IndexError:
        return "Unnamed Task"


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


def fetch_all_tasks_sorted_by_created(assigned_time_equals=False):
    today = datetime.datetime.now().date().isoformat()
    filter_payload = {
        "and": [
            {
                "property": "Due",
                "date": {
                    "on_or_before": today
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


def fetch_current_schedule():
    # Fetch tasks with Assigned time = True
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
            {"property": "Done", "checkbox": {"equals": False}},
        ]
    }
    sorts_payload = [
        {"timestamp": "created_time", "direction": "ascending"}
    ]
    return fetch_tasks(filter_payload, sorts_payload)


def create_schedule_day_task():
    now = datetime.datetime.now(datetime.timezone.utc)
    due = (now + datetime.timedelta(minutes=30)).isoformat()

    url = f"https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": "Schedule Day"}}]},
            "Class": {"select": {"name": "Admin"}},
            "Due": {"date": {"start": now.isoformat(), "end": due}},
            "Priority": {"status": {"name": "High"}}
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        logger.info("'Schedule Day' task created successfully.")
    else:
        logger.error(f"Failed to create 'Schedule Day' task. Status: {response.status_code}, {response.text}")


def update_task(task_id, start_time=None, end_time=None, task_name=None, priority=None, status=None):
    url = f"https://api.notion.com/v1/pages/{task_id}"
    payload = {"properties": {}}

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
    if response.status_code == 200:
        logger.info(f"Updated Task: '{task_name}' with changes: {payload['properties']}")
    else:
        logger.error(f"Failed to update Task: '{task_name}'. Status: {response.status_code}, {response.text}")


def triage_unassigned_tasks():
    priority_mapping = {
        "1": "Low",
        "2": "High",
        "c": "Deprecated",
        "x": "Done",
        "s": "Someday"
    }

    unassigned_tasks = fetch_unassigned_tasks()
    print(f"\nYou have {len(unassigned_tasks)} unassigned tasks.")
    
    for task in unassigned_tasks:
        props = task.get("properties", {})
        task_id = task["id"]
        task_name = get_task_name(props)

        print(f"\nTask: '{task_name}' is currently 'Unassigned'.")
        print("\n[1] Low | [2] High | [c] Deprecated | [x] Done | [s] Someday")
        user_choice = input("\nYour choice: ").strip().lower()

        if user_choice == "c":
            update_task(task_id, task_name=task_name, status="Deprecated")
            print(f"Task '{task_name}' marked as Deprecated.")
        elif user_choice == "x":
            update_task(task_id, task_name=task_name, status="Done")
            print(f"Task '{task_name}' marked as Done.")
        elif user_choice in priority_mapping:
            chosen_priority = priority_mapping[user_choice]
            update_task(task_id, task_name=task_name, priority=chosen_priority)
            print(f"Task '{task_name}' updated to priority: {chosen_priority}.")
        else:
            print(f"Invalid choice for '{task_name}'. No changes made.")


def check_for_overlap(current_schedule, proposed_start, proposed_end):
    for task in current_schedule:
        task_properties = task.get("properties", {})
        task_due = task_properties.get("Due", {}).get("date", {})
        existing_start = task_due.get("start")
        existing_end = task_due.get("end")

        if existing_start and existing_end:
            existing_start = datetime.datetime.fromisoformat(existing_start)
            existing_end = datetime.datetime.fromisoformat(existing_end)

            if (proposed_start < existing_end) and (proposed_end > existing_start):
                return True
    return False


def calculate_available_time_blocks(current_schedule, start_hour=9, end_hour=23):
    today = datetime.datetime.now(LOCAL_TIMEZONE).date()
    start_of_day = datetime.datetime.combine(today, datetime.time(hour=start_hour), tzinfo=LOCAL_TIMEZONE)
    end_of_day = datetime.datetime.combine(today, datetime.time(hour=end_hour), tzinfo=LOCAL_TIMEZONE)

    busy_periods = []
    for task in current_schedule:
        task_properties = task.get("properties", {})
        task_due = task_properties.get("Due", {}).get("date", {})
        start = task_due.get("start")
        end = task_due.get("end")

        if start and end:
            busy_start = datetime.datetime.fromisoformat(start).astimezone(LOCAL_TIMEZONE)
            busy_end = datetime.datetime.fromisoformat(end).astimezone(LOCAL_TIMEZONE)
            busy_periods.append((busy_start, busy_end))

    busy_periods.sort(key=lambda x: x[0])

    free_blocks = []
    current_time = start_of_day

    for busy_start, busy_end in busy_periods:
        if current_time < busy_start:
            free_blocks.append((current_time, busy_start))
        current_time = max(current_time, busy_end)

    if current_time < end_of_day:
        free_blocks.append((current_time, end_of_day))

    return free_blocks


def display_available_time_blocks(free_blocks):
    print("\nAvailable Time Blocks for Today:")
    if not free_blocks:
        print("No free time available today.")
        return
    for start, end in free_blocks:
        print(f"- {start.strftime('%I:%M %p')} to {end.strftime('%I:%M %p')}")


def show_schedule_overview():
    current_schedule = fetch_current_schedule()
    free_blocks = calculate_available_time_blocks(current_schedule)
    display_available_time_blocks(free_blocks)


def schedule_single_task(task, current_time, test_mode, current_schedule, scheduled_task_names):
    props = task.get("properties", {})
    task_id = task["id"]
    task_name = get_task_name(props)
    priority = props.get("Priority", {}).get("status", {}).get("name", "Low")
    time_block_minutes = priority_to_time_block.get(priority, 30)

    start_time = current_time
    if start_time is None:  # Safety check
        start_time = datetime.datetime.now(datetime.timezone.utc)
    end_time = start_time + datetime.timedelta(minutes=time_block_minutes)

    start_time_local = start_time.astimezone(LOCAL_TIMEZONE)

    # Stop if after 11 PM
    if start_time_local.hour >= 23:
        print(f"🚨 Scheduling halted. Proposed start time ({start_time_local.strftime('%Y-%m-%d %I:%M %p %Z')}) is after 11 PM.")
        logger.info("Scheduling ended after 11 PM cutoff.")
        return None

    while check_for_overlap(current_schedule, start_time, end_time):
        print(f"⚠️ Overlap detected for task '{task_name}'. Shifting the time window...")
        start_time = end_time
        end_time = start_time + datetime.timedelta(minutes=time_block_minutes)

    if task_name in scheduled_task_names:
        print(f"🚨 Task '{task_name}' already scheduled. Skipping.")
        return current_time

    start_time_disp = start_time.astimezone(LOCAL_TIMEZONE).strftime("%Y-%m-%d %I:%M %p %Z")
    end_time_disp = end_time.astimezone(LOCAL_TIMEZONE).strftime("%Y-%m-%d %I:%M %p %Z")

    print(f"\n{'='*50}")
    print(f"Task: '{task_name}' (Priority: {priority})")
    print(f"Proposed Start Time (Local): {start_time_disp}")
    print(f"Proposed End Time (Local): {end_time_disp}")
    print(f"Proposed Time Block: {time_block_minutes} minutes")
    print("[Y] Apply | [S] Come Back Later | [X] Deprecated | [C] Complete | [H] High Priority")
    print(f"{'='*50}")

    scheduled_task_names.add(task_name)

    while True:
        user_input = input("Your choice: ").strip().upper()
        if user_input in ["Y", "S", "X", "C", "HIGH"]:
            break
        else:
            print("Invalid choice. Please enter Y, S, X, HIGH, or C.")

    if user_input == "Y":
        if not test_mode:
            update_task(task_id, start_time=start_time.isoformat(), end_time=end_time.isoformat(), task_name=task_name, priority=priority)
            print(f"Task: '{task_name}' scheduled from {start_time_disp} to {end_time_disp}.")
            # Update current schedule with the newly scheduled task times
            task["properties"]["Due"]["date"]["start"] = start_time.isoformat()
            task["properties"]["Due"]["date"]["end"] = end_time.isoformat()
            # Mark assigned time as True (not shown in original code, but assuming)
            # Add the task to current_schedule if not present
            if task not in current_schedule:
                current_schedule.append(task)
        return end_time

    elif user_input == "S":
        print(f"Task '{task_name}' deferred. Rescheduling for tomorrow.")
        tomorrow = datetime.datetime.combine(
            start_time.astimezone(LOCAL_TIMEZONE).date() + datetime.timedelta(days=1),
            datetime.time.min,
            tzinfo=LOCAL_TIMEZONE,
        )
        if not test_mode:
            update_task(task_id, start_time=tomorrow.isoformat(), task_name=task_name, priority=priority)
            # Update local data
            task["properties"]["Due"]["date"]["start"] = tomorrow.isoformat()
        return current_time

    elif user_input in ("X", "C"):
        if not test_mode:
            update_task(task_id, status="Done", task_name=task_name)
            print(f"Task: '{task_name}' marked as Done.")
            # Remove the task from current_schedule since it's done
            if task in current_schedule:
                current_schedule.remove(task)
        return end_time

    else:
        logger.info(f"Skipped Task: '{task_name}' - Invalid choice.")
        return current_time


def schedule_tasks_in_pattern(tasks, test_mode=False, starting_time=None, deferred_tasks=None, scheduled_task_names=None):
    if scheduled_task_names is None:
        scheduled_task_names = set()

    print(f"\nYou have {len(tasks)} tasks to schedule.")

    # Separate tasks by priority
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

    # Sort High priority tasks so "Must Be Done Today" are first
    high_priority_tasks.sort(key=lambda task: task.get("properties", {}).get("Priority", {}).get("status", {}).get("name") != "Must Be Done Today")

    current_time = starting_time or datetime.datetime.now(datetime.timezone.utc)
    current_schedule = fetch_current_schedule()  # Fetch once and reuse

    # Schedule High Priority tasks first
    while high_priority_tasks:
        task = high_priority_tasks.pop(0)
        new_time = schedule_single_task(task, current_time, test_mode, current_schedule, scheduled_task_names)
        if new_time is None:
            # Scheduling halted
            return
        current_time = new_time

    # Then schedule Low Priority tasks
    while low_priority_tasks:
        task = low_priority_tasks.pop(0)
        new_time = schedule_single_task(task, current_time, test_mode, current_schedule, scheduled_task_names)
        if new_time is None:
            # Scheduling halted
            return
        current_time = new_time


def assign_dues_and_blocks(test_mode=False):
    local_now = datetime.datetime.now(LOCAL_TIMEZONE)
    local_now = local_now.replace(second=0, microsecond=0)
    # Round up to next half hour
    if local_now.minute < 30:
        local_now = local_now.replace(minute=30)
    else:
        local_now = local_now.replace(minute=0) + datetime.timedelta(hours=1)

    current_time = local_now.astimezone(datetime.timezone.utc)

    # Show schedule overview once
    logger.info("Showing schedule overview.")
    show_schedule_overview()

    # Fetch tasks and create 'Schedule Day'
    logger.info("Fetching tasks by priority.")
    tasks = fetch_all_tasks_sorted_by_priority_created()
    create_schedule_day_task()

    # Triage tasks once
    logger.info("Triaging unassigned tasks.")
    triage_unassigned_tasks()

    # After triage, fetch the tasks once by creation time for scheduling
    logger.info("Fetching tasks after triage.")
    tasks_post_triage = fetch_all_tasks_sorted_by_created(assigned_time_equals=False)

    print(f"\nYou have {len(tasks_post_triage)} tasks after triage.")

    scheduled_task_names = set()
    schedule_tasks_in_pattern(
        tasks_post_triage,
        test_mode=test_mode,
        starting_time=current_time,
        scheduled_task_names=scheduled_task_names
    )


if __name__ == "__main__":
    assign_dues_and_blocks(test_mode=False)