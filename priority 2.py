#!/usr/bin/env python3
import os
import datetime
import requests
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging to show INFO messages
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
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

def fetch_tasks_due_from_today():
    """
    Fetch all tasks with a Due date on or after today, handling pagination.
    """
    today = datetime.datetime.now().date().isoformat()
    logger.info(f"Fetching tasks due on or after: {today}")
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    filter_payload = {
        "filter": {
            "property": "Actually Due",
            "date": {
                "on_or_after": today
            }
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
    logger.info(f"Total tasks fetched: {len(all_tasks)}")
    return all_tasks

def get_due_date(task):
    """
    Extract the start due date from a task's properties.
    Returns an offset-aware datetime object (UTC) or None.
    """
    try:
        due_info = task.get("properties", {}).get("Due", {}).get("date", {})
        start_date_str = due_info.get("start")
        if start_date_str:
            dt = datetime.datetime.fromisoformat(start_date_str)
            # If the due date is naive, assume UTC.
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt
    except Exception as e:
        logger.error(f"Error parsing due date: {e}")
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

def process_tasks():
    """
    Fetch tasks due today and after.
    For each task with a due date within the next 3 days,
    update its priority to 'Must Be Done Today' and print a summary.
    """
    tasks = fetch_tasks_due_from_today()
    count_updated = 0
    updated_tasks = []  # list of tuples: (task_id, task_name)
    now = datetime.datetime.now(datetime.timezone.utc)
    three_days_later = now + datetime.timedelta(days=3)

    for task in tasks:
        due_date = get_due_date(task)
        if due_date and now <= due_date < three_days_later:
            task_id = task["id"]
            task_name = get_task_name(task.get("properties", {}))
            update_task_priority(task_id, "Must Be Done Today")
            print(f"Task '{task_name}' (ID: {task_id}) updated to 'Must Be Done Today'")
            updated_tasks.append((task_id, task_name))
            count_updated += 1

    logger.info(f"Total tasks updated: {count_updated}")
    if updated_tasks:
        print("\nSummary of tasks updated:")
        for tid, tname in updated_tasks:
            print(f"- {tname} (ID: {tid})")
    else:
        print("\nNo tasks due within the next 3 days to update.")

if __name__ == "__main__":
    process_tasks()