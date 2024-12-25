import datetime
import requests
from dotenv import load_dotenv
import os
import logging
import pytz
import calendar

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
# logger.setLevel(logging.DEBUG)  # More detailed logs

priority_to_time_block = {
    # !TODO: update time based on LOE
    "Low": 30,
    "Medium": 30,
    "High": 30,
    "Must Be Done Today": 30
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
    # logger.debug("Fetching tasks with provided filter and sorts.")
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "filter": filter_payload,
        "sorts": sorts_payload,
        "page_size": 500
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        # logger.debug("Tasks fetched successfully.")
        return response.json().get("results", [])
    else:
        logger.error(f"Failed to fetch tasks. Status: {response.status_code}, {response.text}")
        return []

def fetch_all_tasks_sorted_by_priority_created():
    # logger.debug("Fetching tasks sorted by priority and creation time.")
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
    # logger.debug(f"Fetching tasks sorted by creation time with Assigned time = {assigned_time_equals}")
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
    # logger.debug("Fetching current schedule tasks.")
    return fetch_all_tasks_sorted_by_created(assigned_time_equals=True)

def fetch_unassigned_tasks():
    # logger.debug("Fetching unassigned tasks.")
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
    # logger.debug("Attempting to create 'Schedule Day' task if not existing for today.")
    today = datetime.datetime.now(LOCAL_TIMEZONE).date().isoformat()
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
                        "on_or_before": today
                    }
                },
                {
                    "property": "Due",
                    "date": {
                        "on_or_after": today
                    }
                }
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

def update_task(task_id, start_time=None, end_time=None, task_name=None, priority=None, status=None):
    # logger.debug(f"Updating task '{task_name}' (ID: {task_id}) with new times/priority/status.")
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
    else:
        logger.debug(f"Task '{task_name}' updated successfully.")

def parse_custom_date(input_str):
    # logger.debug(f"Parsing custom date input: '{input_str}'")
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

def triage_unassigned_tasks():
    # logger.debug("Triaging unassigned tasks.")
    priority_mapping = {
        "1": "Low",
        "2": "High",
        "c": "Deprecated",
        "x": "Done",
        "s": "Someday"
    }

    unassigned_tasks = fetch_unassigned_tasks()
    print(f"\n📋 You have {len(unassigned_tasks)} unassigned tasks.")

    for task in unassigned_tasks:
        props = task.get("properties", {})
        task_id = task["id"]
        task_name = get_task_name(props)

        print(f"\n📝 Task: '{task_name}' is 'Unassigned'.")
        print("\n[1] Low (💡)")
        print("[2] High (🔥)")
        print("[c] Deprecated (🗑️)")
        print("[x] Done (✅)")
        print("[s] Someday (🌥️)")

        user_choice = input("\nYour choice: ").strip().lower()
        if user_choice == "c":
            update_task(task_id, task_name=task_name, status="Deprecated")
            print(f"🗑️ '{task_name}' archived.")
        elif user_choice == "x":
            update_task(task_id, task_name=task_name, status="Done")
            print(f"✅ '{task_name}' Done.")
        elif user_choice in priority_mapping:
            chosen_priority = priority_mapping[user_choice]
            update_task(task_id, task_name=task_name, priority=chosen_priority)
            print(f"📌 '{task_name}' priority: {chosen_priority}")
            if chosen_priority not in ["Someday", "Done", "Deprecated"]:
                print("\n📅 Set a due date:")
                print("[1] Today (🟢)")
                print("[2] Tomorrow (🔵)")
                print("[3] Next Week (📆)")
                print("Or type e.g. 'Jan 2025'")
                while True:
                    due_choice = input("\nDue date choice: ").strip()
                    today = datetime.datetime.now(LOCAL_TIMEZONE).date()
                    if due_choice == "1":
                        due_date = today
                    elif due_choice == "2":
                        due_date = today + datetime.timedelta(days=1)
                    elif due_choice == "3":
                        due_date = today + datetime.timedelta(days=7)
                    else:
                        parsed = parse_custom_date(due_choice)
                        if parsed:
                            due_date = parsed
                        else:
                            print("⚠️ Invalid date.")
                            continue
                    due_date_str = due_date.isoformat()
                    url = f"https://api.notion.com/v1/pages/{task_id}"
                    payload = {
                        "properties": {
                            "Due": {
                                "date": {
                                    "start": due_date_str
                                }
                            }
                        }
                    }
                    r = requests.patch(url, headers=headers, json=payload)
                    if r.status_code == 200:
                        print(f"📅 '{task_name}' due date: {due_date_str}")
                    else:
                        print("❌ Failed to set due date.")
                    break
        else:
            print(f"⚠️ Invalid choice for '{task_name}'.")

def check_for_overlap(current_schedule, proposed_start, proposed_end):
    proposed_start_utc = proposed_start.astimezone(datetime.timezone.utc)
    proposed_end_utc = proposed_end.astimezone(datetime.timezone.utc)
    # logger.debug(f"Checking overlap for interval {proposed_start_utc} - {proposed_end_utc}")

    for task in current_schedule:
        props = task.get("properties", {})
        due = props.get("Due", {}).get("date", {})
        existing_start = due.get("start")
        existing_end = due.get("end")

        if not existing_start or not existing_end:
            logger.debug(f"Task '{get_task_name(props)}' missing start/end times.")
            continue

        existing_start_dt = datetime.datetime.fromisoformat(existing_start).astimezone(datetime.timezone.utc)
        existing_end_dt = datetime.datetime.fromisoformat(existing_end).astimezone(datetime.timezone.utc)

        # logger.debug(f"Compare with '{get_task_name(props)}': {existing_start_dt} - {existing_end_dt}")
        if (proposed_start_utc < existing_end_dt) and (proposed_end_utc > existing_start_dt):
            logger.debug(f"Overlap found with '{get_task_name(props)}'")
            return True

    logger.debug("No overlap found.")
    return False

def handle_overlapping_due_dates(current_schedule):
    logger.debug("Resolving overlapping due dates...")
    today = datetime.datetime.now(LOCAL_TIMEZONE).date().isoformat()

    def get_priority_level(task):
        props = task.get("properties", {})
        priority = props.get("Priority", {}).get("status", {}).get("name", "Low")
        level = "High" if priority in ["High", "Must Be Done Today"] else "Low"
        logger.debug(f"'{get_task_name(props)}' priority: {priority} → {level}")
        return level

    def set_date_only(task_id, task_name):
        logger.debug(f"Setting date-only for '{task_name}'")
        url = f"https://api.notion.com/v1/pages/{task_id}"
        payload = {
            "properties": {
                "Due": {
                    "date": {
                        "start": today
                    }
                }
            }
        }
        r = requests.patch(url, headers=headers, json=payload)
        if r.status_code == 200:
            logger.info(f"✅ '{task_name}' due date = {today}, no time.")
        else:
            logger.error(f"❌ Failed to update '{task_name}'.")

    def get_task_times(task):
        props = task.get("properties", {})
        due = props.get("Due", {}).get("date", {})
        start = due.get("start")
        end = due.get("end")
        logger.debug(f"Checking task '{get_task_name(props)}' for times.")
        if not start or not end:
            logger.debug(f"Task '{get_task_name(props)}' no start/end.")
            return None, None
        start_dt = datetime.datetime.fromisoformat(start).astimezone(datetime.timezone.utc)
        end_dt = datetime.datetime.fromisoformat(end).astimezone(datetime.timezone.utc)
        return start_dt, end_dt

    def get_task_name_for(task):
        return get_task_name(task.get("properties", {}))

    overlapping_pairs = []
    n = len(current_schedule)
    logger.debug(f"Current schedule length: {n}")
    logger.debug("Tasks in current schedule for overlap check:")
    for ctask in current_schedule:
        cname = get_task_name(ctask.get("properties", {}))
        logger.debug(f" - {cname}")

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
                logger.info(f"Overlap: '{get_task_name_for(task_a)}' and '{get_task_name_for(task_b)}'")
                overlapping_pairs.append((task_a, task_b))

    if not overlapping_pairs:
        logger.debug("No overlaps found to resolve.")
        return

    logger.debug(f"Overlapping pairs found: {len(overlapping_pairs)}")
    handled_ids = set()
    for (task_a, task_b) in overlapping_pairs:
        a_id = task_a["id"]
        b_id = task_b["id"]
        if a_id in handled_ids or b_id in handled_ids:
            logger.debug(f"Already handled {a_id} or {b_id}.")
            continue

        a_priority = get_priority_level(task_a)
        b_priority = get_priority_level(task_b)
        a_name = get_task_name_for(task_a)
        b_name = get_task_name_for(task_b)

        logger.info(f"Resolving overlap between '{a_name}' ({a_priority}) and '{b_name}' ({b_priority})")

        set_date_only(a_id, a_name)
        set_date_only(b_id, b_name)

        if a_priority == "High" and b_priority == "High":
            logger.info(f"Both high: keep both '{a_name}' and '{b_name}'.")
        elif a_priority == "High" and b_priority == "Low":
            logger.info(f"Keep '{a_name}' (High), remove '{b_name}' (Low).")
            current_schedule[:] = [t for t in current_schedule if t["id"] != b_id]
        elif a_priority == "Low" and b_priority == "High":
            logger.info(f"Keep '{b_name}' (High), remove '{a_name}' (Low).")
            current_schedule[:] = [t for t in current_schedule if t["id"] != a_id]
        else:
            logger.info(f"Both low: remove '{a_name}' and '{b_name}'.")
            current_schedule[:] = [t for t in current_schedule if t["id"] not in (a_id, b_id)]

        handled_ids.add(a_id)
        handled_ids.add(b_id)

    logger.debug("Finished resolving overlaps.")

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

def display_available_time_blocks(free_blocks):
    print("\n🕒 **Available Time Blocks for Today**:")
    if not free_blocks:
        print("🚫 No free time available today.")
        return
    for start, end in free_blocks:
        print(f"✅ {start.strftime('%I:%M %p')} to {end.strftime('%I:%M %p')}")

def show_schedule_overview(current_schedule):
    print("\n🔍 Checking schedule overview...")
    logger.debug("Before resolving overlaps.")
    print("\n🛠️ Resolving overlapping due dates...")
    handle_overlapping_due_dates(current_schedule)
    logger.debug("After resolving overlaps.")

    free_blocks = calculate_available_time_blocks(current_schedule)
    display_available_time_blocks(free_blocks)

def schedule_single_task(task, current_time, test_mode, current_schedule, scheduled_task_names):
    props = task.get("properties", {})
    task_id = task["id"]
    task_name = get_task_name(props)
    priority = props.get("Priority", {}).get("status", {}).get("name", "Low")
    time_block_minutes = priority_to_time_block.get(priority, 30)

    current_time_local = current_time.astimezone(LOCAL_TIMEZONE)
    start_time_local = current_time_local
    end_time_local = start_time_local + datetime.timedelta(minutes=time_block_minutes)

    if start_time_local.hour >= 23:
        print(f"🚨 Scheduling halted. Start time after 11 PM: {start_time_local.strftime('%Y-%m-%d %I:%M %p %Z')}")
        schedule_complete()
        return None

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
        return current_time

    print(f"\n{'='*50}")
    print(f"Task: '{task_name}' (Priority: {priority})")
    print(f"Proposed Start: {start_time_disp}, End: {end_time_disp} ({time_block_minutes} mins)")
    print("[Y] Apply | [S] Later | [X] Deprecated | [C] Complete | [H] High | [W] +1 Week")
    print("Or type a time like '9pm' to override:")
    print(f"{'='*50}")

    scheduled_task_names.add(task_name)

    while True:
        user_input = input("Your choice: ").strip().upper()
        if user_input in ["Y","S","X","C","H","W"]:
            break
        else:
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
                if start_time_local.hour >= 23:
                    print("🚨 New start after 11 PM. Halting.")
                    return None

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
                print("[Y] Apply | [S] Later | [X] Deprecated | [C] Complete | [H] High | [W] +1 Week")
            else:
                print("Invalid time. Try again.")

    if user_input == "Y":
        if not test_mode:
            start_iso = start_time_local.isoformat()
            end_iso = end_time_local.isoformat()
            update_task(task_id, start_time=start_iso, end_time=end_iso, task_name=task_name, priority=priority)
            print(f"Task '{task_name}' scheduled from {start_time_disp} to {end_time_disp}.")
            task["properties"]["Due"]["date"]["start"] = start_iso
            task["properties"]["Due"]["date"]["end"] = end_iso
            if task not in current_schedule:
                current_schedule.append(task)
        return end_time_local.astimezone(datetime.timezone.utc)

    elif user_input == "S":
        print(f"Task '{task_name}' deferred to tomorrow.")
        tomorrow_local = datetime.datetime.combine(start_time_local.date() + datetime.timedelta(days=1),
                                                   datetime.time.min, tzinfo=LOCAL_TIMEZONE)
        if not test_mode:
            tomorrow_iso = tomorrow_local.isoformat()
            update_task(task_id, start_time=tomorrow_iso, task_name=task_name, priority=priority)
            task["properties"]["Due"]["date"]["start"] = tomorrow_iso
        return current_time

    elif user_input in ("X","C"):
        if not test_mode:
            update_task(task_id, status="Done", task_name=task_name)
            print(f"Task '{task_name}' Done.")
            if task in current_schedule:
                current_schedule.remove(task)
        return end_time_local.astimezone(datetime.timezone.utc)

    elif user_input == "H":
        if not test_mode:
            start_iso = start_time_local.isoformat()
            end_iso = end_time_local.isoformat()
            update_task(task_id, start_time=start_iso, end_time=end_iso, priority="High", task_name=task_name)
            print(f"Task '{task_name}' High priority and scheduled.")
            if task in current_schedule:
                current_schedule.remove(task)
        return end_time_local.astimezone(datetime.timezone.utc)

    elif user_input == "W":
        one_week_later_date = (start_time_local.date() + datetime.timedelta(days=7)).isoformat()
        if not test_mode:
            url = f"https://api.notion.com/v1/pages/{task_id}"
            payload = {
                "properties": {
                    "Due": {
                        "date": {
                            "start": one_week_later_date
                        }
                    }
                }
            }
            r = requests.patch(url, headers=headers, json=payload)
            if r.status_code == 200:
                print(f"Task '{task_name}' date moved to {one_week_later_date}.")
                task["properties"]["Due"]["date"]["start"] = one_week_later_date
                if "end" in task["properties"]["Due"]["date"]:
                    del task["properties"]["Due"]["date"]["end"]
        return current_time

    else:
        logger.info(f"Skipped Task: '{task_name}' - Invalid choice.")
        return current_time

def schedule_tasks_in_pattern(tasks, test_mode=False, starting_time=None, deferred_tasks=None, scheduled_task_names=None):
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

    high_priority_tasks.sort(key=lambda task: task.get("properties", {}).get("Priority", {}).get("status", {}).get("name") != "Must Be Done Today")

    current_time = starting_time or datetime.datetime.now(datetime.timezone.utc)
    current_schedule = fetch_current_schedule()

    while high_priority_tasks:
        task = high_priority_tasks.pop(0)
        new_time = schedule_single_task(task, current_time, test_mode, current_schedule, scheduled_task_names)
        if new_time is None:
            return
        current_time = new_time

    while low_priority_tasks:
        task = low_priority_tasks.pop(0)
        new_time = schedule_single_task(task, current_time, test_mode, current_schedule, scheduled_task_names)
        if new_time is None:
            return
        current_time = new_time

def schedule_complete():
    print("Scheduling complete. Have a great day!")

def assign_dues_and_blocks(test_mode=False):
    # logger.debug("Assigning dues and blocks...")
    local_now = datetime.datetime.now(LOCAL_TIMEZONE).replace(second=0, microsecond=0)
    if local_now.minute < 30:
        local_now = local_now.replace(minute=30)
    else:
        local_now = local_now.replace(minute=0) + datetime.timedelta(hours=1)

    current_time = local_now.astimezone(datetime.timezone.utc)
    # logger.debug(f"Initial current time: {current_time}")

    tasks = fetch_all_tasks_sorted_by_priority_created()
    create_schedule_day_task()

    triage_unassigned_tasks()

    tasks_post_triage = fetch_all_tasks_sorted_by_created(assigned_time_equals=False)
    print(f"\nYou have {len(tasks_post_triage)} tasks after triage.")

    current_schedule = fetch_current_schedule()
    show_schedule_overview(current_schedule)

    updated_tasks = fetch_all_tasks_sorted_by_created(assigned_time_equals=False)
    non_deprecated_tasks = [
        t for t in updated_tasks
        if t.get("properties", {}).get("Status", {}).get("status", {}).get("name") != "Deprecated"
    ]

    seen_ids = set()
    unique_tasks = []
    for t in non_deprecated_tasks:
        if t["id"] not in seen_ids:
            seen_ids.add(t["id"])
            unique_tasks.append(t)

    if unique_tasks:
        schedule_tasks_in_pattern(unique_tasks, test_mode=test_mode, starting_time=current_time)
    else:
        print("\nNo tasks to schedule after cleanup.")

    print("\n🎉 **Scheduling complete! Have a great day!**")

if __name__ == "__main__":
    assign_dues_and_blocks(test_mode=False)