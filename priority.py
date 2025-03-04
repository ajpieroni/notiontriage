#!/usr/bin/env python3
import os
import datetime
import requests
import logging
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
        name = properties.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Unnamed Task")
        return name
    except Exception as e:
        logger.error(f"Error retrieving task name: {e}")
        return "Unnamed Task"

def fetch_academic_tasks_due_from_today():
    """
    Fetch all academic tasks (Class = Academics) with an 'Actually Due' date on or after today, handling pagination.
    Only tasks that already have an 'Actually Due' date will be returned.
    """
    today = datetime.datetime.now().date().isoformat()
    logger.info(f"Fetching academic tasks due on or after: {today}")
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    filter_payload = {
        "filter": {
            "and": [
            #     {
            #         "property": "Actually Due",
            #         "date": {
            #             "on_or_after": today
            #         }
            #     },
                {
                    "property": "Class",
                    "select": {
                        "equals": "Academics"
                    }
                }
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
        # Safely get the "Actually Due" date if it exists
        actually_due_prop = properties.get("Actually Due")
        if actually_due_prop and actually_due_prop.get("date"):
            actually_due = actually_due_prop.get("date", {}).get("start", "No date")
        else:
            actually_due = "No date"
        print(f"- {task_name}: {actually_due}")
def get_due_date(task):
    """
    Extract the start due date from a task's "Actually Due" property.
    Since we are filtering for academic tasks with this property, a missing value is unlikely.
    Returns an offset-aware datetime object (UTC) or None.
    """
    try:
        due_info = task.get("properties", {}).get("Actually Due", {}).get("date", {})
        start_date_str = due_info.get("start")
        if start_date_str:
            dt = datetime.datetime.fromisoformat(start_date_str)
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
    Fetch academic tasks due today and after.
    Print out each task's name and 'Actually Due' date.
    For each task with a due date within the next 3 days,
    update its priority to 'Must Be Done Today' and print a summary.
    """
    tasks = fetch_academic_tasks_due_from_today()
    print_tasks_actually_due(tasks)  # Print task names and their 'Actually Due' dates

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
    print("🎉 All done!")

if __name__ == "__main__":
    process_tasks()