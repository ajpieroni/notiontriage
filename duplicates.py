#!/usr/bin/env python3
import os
import datetime
import requests
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging to include debugging output
logging.basicConfig(level=logging.DEBUG)
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
    Retrieve the task name from the properties.
    """
    try:
        name = properties.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Unnamed Task")
        logger.debug(f"Retrieved task name: {name}")
        return name
    except Exception as e:
        logger.error(f"Error retrieving task name: {e}")
        return "Unnamed Task"

def fetch_tasks_due_today():
    """
    Fetch all tasks from the Notion database that are incomplete (Done: false)
    and have a Due date equal to today.
    """
    today = datetime.datetime.now().date().isoformat()
    logger.debug(f"Today's date: {today}")
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    filter_payload = {
    #     "sorts": [
    #     {"timestamp": "created_time", "direction": "ascending"}
    # ],

        "filter": {
            "and": [
                # {
                #     "property": "Due",
                #     "date": {
                #         "on_or_before": today
                #     }
                # },
                {
                    "property": "Due",
                    "date": {
                        "on_or_after": today
                    }
                },
                # {
                #     "property": "Status",
                #     "checkbox": {
                #         "does_not_equal": "Done"
                #     }
                # },
            {"property": "Status", "status": {"does_not_equal": "Done"}},
            {"property": "Status", "status": {"does_not_equal": "Handed Off"}},
            {"property": "Status", "status": {"does_not_equal": "Deprecated"}},
            {"property": "Done", "checkbox": {"equals": False}},
            ]
        }
    }
    logger.debug(f"Filter payload: {filter_payload}")
    response = requests.post(url, headers=headers, json=filter_payload)
    logger.debug(f"Response status code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        logger.debug(f"Response JSON: {data}")
        tasks = data.get("results", [])
        logger.info(f"Fetched {len(tasks)} tasks due today.")
        return tasks
    else:
        logger.error(f"Failed to fetch tasks: {response.status_code} {response.text}")
        return []

def update_task_status(task_id, new_status):
    """
    Update the Status property of a task.
    """
    url = f"https://api.notion.com/v1/pages/{task_id}"
    payload = {
        "properties": {
            "Status": {
                "status": {"name": new_status}
            }
        }
    }
    logger.debug(f"Updating task {task_id} with payload: {payload}")
    response = requests.patch(url, headers=headers, json=payload)
    logger.debug(f"Response status code for update: {response.status_code}")
    if response.status_code == 200:
        logger.info(f"Task {task_id} updated to status '{new_status}'.")
    else:
        logger.error(f"Failed to update task {task_id}: {response.status_code} {response.text}")

def mark_duplicate_tasks_as_deprecated(tasks, deprecated):
    """
    For tasks with the same name, mark every task (except the oldest) as Deprecated.
    """
    # Group tasks by their name.
    task_groups = {}
    for task in tasks:
        name = get_task_name(task.get("properties", {}))
        task_groups.setdefault(name, []).append(task)
        logger.debug(f"Added task ID {task['id']} to group '{name}'.")

    # For any group with duplicate names, mark the newer ones as deprecated.
    for name, group in task_groups.items():
        logger.debug(f"Processing group '{name}' with {len(group)} tasks.")
        if len(group) > 1:
            # Sort tasks by created_time (oldest first)
            sorted_group = sorted(group, key=lambda t: t.get("created_time"))
            logger.debug(f"Sorted group '{name}' by created_time.")
            # Log created times for debugging purposes
            for task in sorted_group:
                logger.debug(f"Task ID {task['id']} created at {task.get('created_time')}")
            # Keep the first (oldest) and mark all others as Deprecated.
            for task in sorted_group[1:]:
                task_id = task["id"]
                logger.info(f"Marking task '{name}' (ID: {task_id}) as Deprecated.")
                deprecated += 1;
                update_task_status(task_id, "Deprecated")
        else:
            logger.debug(f"No duplicates found for task '{name}'.")

def main():
    logger.info("Starting script to deprecate duplicate tasks.")
    tasks = fetch_tasks_due_today()
    if not tasks:
        logger.info("No incomplete tasks due today found.")
        return
    deprecated = 0
    mark_duplicate_tasks_as_deprecated(tasks, deprecated)
    logger.info("Finished processing tasks.")
    # print length of tasks marked as deprecated
    print("Number of tasks marked as deprecated: ", deprecated)
    

if __name__ == "__main__":
    main()