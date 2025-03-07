#!/usr/bin/env python3
import os
import datetime
import requests
import logging
import threading
import tzlocal
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging to show only INFO and above messages
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID")

if not NOTION_API_KEY or not DATABASE_ID:
    exit(1)

# Set up headers for the Notion API
headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def get_task_name(properties):
    """
    Retrieve the task name from the task properties.
    """
    try:
        return properties.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Unnamed Task")
    except Exception as e:
        return "Unnamed Task"

def prompt_due_date(task_name):
    """
    Prompt the user to enter a due date when it's missing.
    The input can be a weekday name (e.g., 'monday') or a date string (e.g., 'March 3').
    Returns a date object.
    """
    input_str = input(f"Enter due date for '{task_name}' (e.g., 'monday' or 'March 3'): ").strip()
    due_date = None
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if input_str.lower() in weekdays:
        today = datetime.datetime.now().date()
        target_day = weekdays.index(input_str.lower())
        today_weekday = today.weekday()  # Monday = 0
        days_ahead = (target_day - today_weekday) % 7
        if days_ahead == 0:
            days_ahead = 7
        due_date = today + datetime.timedelta(days=days_ahead)
    else:
        try:
            due_date = datetime.datetime.strptime(input_str, "%B %d").date()
            today = datetime.datetime.now().date()
            due_date = due_date.replace(year=today.year)
            if due_date < today:
                due_date = due_date.replace(year=today.year + 1)
        except ValueError:
            logger.error("Invalid date format. Expected a weekday name or 'Month day' format (e.g., 'March 3').")
    return due_date

def fetch_academic_tasks_due_from_today():
    """
    Fetch all academic tasks (Class = Academics) with relevant filters, handling pagination.
    Only tasks that have a "Class" property set to "Academics" are returned.
    """
    today = datetime.datetime.now().date().isoformat()
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    filter_payload = {
        "filter": {
            "and": [
                {"property": "Class", "select": {"equals": "Academics"}},
                {"property": "Priority", "status": {"does_not_equal": "Someday"}},
                {"property": "Status", "status": {"does_not_equal": "Done"}},
                {"property": "Status", "status": {"does_not_equal": "Handed Off"}},
                {"property": "Status", "status": {"does_not_equal": "Deprecated"}},
                {"property": "Status", "status": {"does_not_equal": "Waiting on Reply"}},
                {"property": "Status", "status": {"does_not_equal": "Waiting on other task"}},
                {"property": "Done", "checkbox": {"equals": False}},
            ]
        }
    }
    all_tasks = []
    has_more = True
    next_cursor = None
    while has_more:
        payload = filter_payload.copy()
        if next_cursor:
            payload["start_cursor"] = next_cursor
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            logger.error(f"Error fetching tasks: {response.status_code} - {response.text}")
            break
        data = response.json()
        tasks = data.get("results", [])
        all_tasks.extend(tasks)
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")
    return all_tasks

def print_tasks_actually_due(tasks):
    """
    Print out the task name and 'Actually Due' date for each task.
    """
    print("Tasks were fetched successfully. I'll prompt you if any due dates are missing.")
    # print("Academic tasks with their 'Actually Due' dates:")
    # for task in tasks:
    #     properties = task.get("properties", {})
    #     task_name = get_task_name(properties)
    #     actually_due_prop = properties.get("Actually Due")
    #     if actually_due_prop and actually_due_prop.get("date"):
    #         actually_due = actually_due_prop.get("date", {}).get("start", "No date")
    #     else:
    #         actually_due = "No date"
    #     print(f"- {task_name}: {actually_due}")

def get_due_date(task):
    """
    Extract the start due date from a task's "Actually Due" property.
    If the due date is missing or empty, return None so that we can prompt later.
    """
    properties = task.get("properties")
    if not properties:
        return None
    task_name = get_task_name(properties)
    actually_due_prop = properties.get("Actually Due")
    if not actually_due_prop:
        return None
    date_info = actually_due_prop.get("date") if isinstance(actually_due_prop, dict) else None
    if not date_info:
        return None
    start_date_str = date_info.get("start")
    if not start_date_str or start_date_str == "No date":
        return None
    try:
        dt = datetime.datetime.fromisoformat(start_date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception as e:
        return None

def update_task_priority_and_due(task_id, new_priority, due_date):
    """
    Update the 'Priority' property and the 'Actually Due' date of a task.
    The due_date is assumed to be in local time. It is combined with midnight in the local timezone,
    then converted to UTC before sending it to Notion.
    """
    local_tz = tzlocal.get_localzone()
    dt_local = datetime.datetime.combine(due_date, datetime.time(0, 0), tzinfo=local_tz)
    dt_utc = dt_local.astimezone(datetime.timezone.utc)
    url = f"https://api.notion.com/v1/pages/{task_id}"
    payload = {
        "properties": {
            "Priority": {"status": {"name": new_priority}},
            "Actually Due": {
                "date": {
                    "start": dt_utc.isoformat()
                }
            }
        }
    }
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code == 200:
        logger.info(f"Task {task_id} updated successfully with due date {dt_utc.isoformat()}.")
    else:
        logger.error(f"Failed to update task {task_id}: {response.status_code} - {response.text}")

def update_task_with_due_date(task, due_date):
    """
    Update the task's priority and post the user-entered due date (converted from local to UTC)
    to Notion.
    """
    update_task_priority_and_due(task["id"], "Must Be Done Today", due_date)
    task_name = get_task_name(task.get("properties", {}))
    local_tz = tzlocal.get_localzone()
    dt_local = datetime.datetime.combine(due_date, datetime.time(0, 0), tzinfo=local_tz)
    dt_utc = dt_local.astimezone(datetime.timezone.utc)
    print(f"Task '{task_name}' (ID: {task['id']}) updated to 'Must Be Done Today' with due date {dt_utc.isoformat()}.")

def prompt_due_dates_for_tasks(tasks):
    """
    For each task missing a due date, prompt the user one at a time.
    As soon as a due date is entered, update the task in a background thread
    so that the prompt for the next task appears immediately.
    """
    for task in tasks:
        task_name = get_task_name(task.get("properties", {}))
        due_date = None
        while due_date is None:
            due_date = prompt_due_date(task_name)
        t = threading.Thread(target=update_task_with_due_date, args=(task, due_date))
        t.start()

def double_check_academic_due_dates():
    """
    Re-fetch academic tasks and check if any tasks with class Academics
    are missing a due date in the "Actually Due" field.
    """
    tasks = fetch_academic_tasks_due_from_today()
    missing_due = []
    for task in tasks:
        if get_due_date(task) is None:
            task_name = get_task_name(task.get("properties", {}))
            missing_due.append(task_name)
    if missing_due:
        print("\nWARNING: The following academic tasks are still missing 'Actually Due' dates:")
        for name in missing_due:
            print(f"- {name}")
    else:
        print("\nAll academic tasks have a valid 'Actually Due' date.")

def process_tasks():
    """
    Fetch academic tasks due today and after.
    For tasks that already have a due date within the next 3 days, update their priority
    to 'Must Be Done Today' only if not already set.
    For tasks missing a due date, prompt the user one at a time while updating in the background.
    Finally, double-check that no academic tasks remain with a missing due date.
    """
    tasks = fetch_academic_tasks_due_from_today()
    print_tasks_actually_due(tasks)
    
    tasks_with_due = []
    tasks_missing_due = []
    now = datetime.datetime.now(datetime.timezone.utc)
    three_days_later = now + datetime.timedelta(days=3)
    
    for task in tasks:
        due_date = get_due_date(task)
        if due_date:
            tasks_with_due.append((task, due_date))
        else:
            tasks_missing_due.append(task)
    
    for task, due_date in tasks_with_due:
        current_priority = task.get("properties", {}).get("Priority", {}).get("status", {}).get("name", "")
        if current_priority != "Must Be Done Today" and now <= due_date < three_days_later:
            update_task_priority_and_due(task["id"], "Must Be Done Today", due_date)
            task_name = get_task_name(task.get("properties", {}))
            print(f"Task '{task_name}' (ID: {task['id']}) updated to 'Must Be Done Today'")
    
    if tasks_missing_due:
        prompt_due_dates_for_tasks(tasks_missing_due)
    
    # Final double-check: re-fetch and verify no academic tasks are missing a due date.
    double_check_academic_due_dates()
    
    # print("🎉 All done!")

if __name__ == "__main__":
    process_tasks()