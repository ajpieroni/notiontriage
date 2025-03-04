#!/usr/bin/env python3
import os
import datetime
import requests
import logging
import threading
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging to show DEBUG messages for detailed output
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID")

if not NOTION_API_KEY or not DATABASE_ID:
    logger.error("Missing NOTION_API_KEY or DATABASE_ID environment variables.")
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
        logger.error(f"Error retrieving task name: {e}")
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
        today_weekday = today.weekday()  # Monday=0
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
    logger.info(f"Fetching academic tasks due on or after: {today}")
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    filter_payload = {
        "filter": {
            "and": [
                {
                    "property": "Class",
                    "select": {"equals": "Academics"}
                },
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
        logger.debug(f"Fetched {len(tasks)} tasks in this batch.")
        all_tasks.extend(tasks)
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")
    logger.info(f"Total academic tasks fetched: {len(all_tasks)}")
    return all_tasks

def print_tasks_actually_due(tasks):
    """
    Print out the task name and 'Actually Due' date for each task.
    """
    print("Academic tasks with their 'Actually Due' dates:")
    for task in tasks:
        properties = task.get("properties", {})
        task_name = get_task_name(properties)
        actually_due_prop = properties.get("Actually Due")
        if actually_due_prop and actually_due_prop.get("date"):
            actually_due = actually_due_prop.get("date", {}).get("start", "No date")
        else:
            actually_due = "No date"
        print(f"- {task_name}: {actually_due}")

def get_due_date(task):
    """
    Extract the start due date from a task's "Actually Due" property.
    If the due date is missing or empty, return None so that we can batch-prompt later.
    """
    properties = task.get("properties")
    if not properties:
        logger.error("Task is missing properties.")
        return None
    task_name = get_task_name(properties)
    actually_due_prop = properties.get("Actually Due")
    if not actually_due_prop:
        logger.info(f"'Actually Due' property is missing for task '{task_name}'.")
        return None
    date_info = actually_due_prop.get("date") if isinstance(actually_due_prop, dict) else None
    if not date_info:
        logger.info(f"'Actually Due' date info is missing for task '{task_name}'.")
        return None
    start_date_str = date_info.get("start")
    if not start_date_str or start_date_str == "No date":
        logger.info(f"'Actually Due' start date is empty for task '{task_name}'.")
        return None
    try:
        dt = datetime.datetime.fromisoformat(start_date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception as e:
        logger.error(f"Error parsing start date for task '{task_name}': {e}")
        return None

def update_task_priority(task_id, new_priority):
    """
    Update the 'Priority' property of a task.
    """
    logger.info(f"Updating task {task_id} to priority '{new_priority}'")
    url = f"https://api.notion.com/v1/pages/{task_id}"
    payload = {
        "properties": {
            "Priority": {
                "status": {"name": new_priority}
            }
        }
    }
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code == 200:
        logger.info(f"Task {task_id} updated successfully.")
    else:
        logger.error(f"Failed to update task {task_id}: {response.status_code} - {response.text}")

def update_task_with_due_date(task, due_date):
    """
    Combine the given due_date with time and update the task's priority.
    """
    dt = datetime.datetime.combine(due_date, datetime.time(0, 0), tzinfo=datetime.timezone.utc)
    # Optionally, update the task's "Actually Due" field via a separate PATCH call here.
    update_task_priority(task["id"], "Must Be Done Today")
    task_name = get_task_name(task.get("properties", {}))
    print(f"Task '{task_name}' (ID: {task['id']}) updated to 'Must Be Done Today' with due date {dt.isoformat()}.")

def prompt_due_dates_for_tasks(tasks, batch_size=3):
    """
    Process tasks that need due date input in batches.
    For each batch, display the task names and prompt the user for due dates.
    As soon as the user inputs a due date, update that task in a background thread.
    """
    from math import ceil
    total = len(tasks)
    num_batches = ceil(total / batch_size)
    for i in range(num_batches):
        batch = tasks[i * batch_size:(i + 1) * batch_size]
        print("\nPlease provide due dates for the following tasks:")
        for idx, task in enumerate(batch, start=1):
            task_name = get_task_name(task.get("properties", {}))
            print(f"{idx}. {task_name}")
        # For each task in the batch, prompt for input and spawn a thread for updating
        for task in batch:
            task_name = get_task_name(task.get("properties", {}))
            due_date = None
            while due_date is None:
                due_date = prompt_due_date(task_name)
            # Spawn a thread to update the task while allowing next prompts
            t = threading.Thread(target=update_task_with_due_date, args=(task, due_date))
            t.start()

def process_tasks():
    """
    Fetch academic tasks due today and after.
    For tasks that already have a due date within the next 3 days, update their priority.
    For tasks missing a due date, group them in batches (e.g., 2-3) and prompt the user for input,
    updating the tasks in the background.
    """
    tasks = fetch_academic_tasks_due_from_today()
    print_tasks_actually_due(tasks)
    
    # Split tasks into two groups: those with due dates and those missing them.
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
    
    # Update tasks that already have due dates
    for task, due_date in tasks_with_due:
        if now <= due_date < three_days_later:
            update_task_priority(task["id"], "Must Be Done Today")
            task_name = get_task_name(task.get("properties", {}))
            print(f"Task '{task_name}' (ID: {task['id']}) updated to 'Must Be Done Today'")
    
    # Process tasks missing due dates in batches
    if tasks_missing_due:
        prompt_due_dates_for_tasks(tasks_missing_due, batch_size=3)
    
    print("🎉 All done!")

if __name__ == "__main__":
    process_tasks()