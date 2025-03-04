#!/usr/bin/env python3
import os
import datetime
import requests
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging to show only INFO level messages
logging.basicConfig(level=logging.INFO)
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
        return name
    except Exception as e:
        logger.error(f"Error retrieving task name: {e}")
        return "Unnamed Task"

def fetch_tasks_due_today():
    """
    Fetch all tasks from the Notion database that are incomplete (Done: false)
    and have a Due date equal to or after today, handling pagination.
    """
    today = datetime.datetime.now().date().isoformat()
    logger.info(f"Fetching tasks for today: {today}")
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    filter_payload = {
        "filter": {
            "and": [
                {
                    "property": "Due",
                    "date": {"on_or_after": today}
                },
                {"property": "Status", "status": {"does_not_equal": "Done"}},
                {"property": "Status", "status": {"does_not_equal": "Handed Off"}},
                {"property": "Status", "status": {"does_not_equal": "Deprecated"}},
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
        if response.status_code == 200:
            data = response.json()
            tasks = data.get("results", [])
            all_tasks.extend(tasks)
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor", None)
        else:
            logger.error(f"Failed to fetch tasks: {response.status_code} {response.text}")
            break

    logger.info(f"Total fetched tasks: {len(all_tasks)}")
    return all_tasks

def update_task_status(task_id, new_status):
    """
    Update the Status property of a task.
    """
    url = f"https://api.notion.com/v1/pages/{task_id}"
    payload = {"properties": {"Status": {"status": {"name": new_status}}}}
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code == 200:
        logger.info(f"Task {task_id} updated to status '{new_status}'.")
    else:
        logger.error(f"Failed to update task {task_id}: {response.status_code} {response.text}")

def mark_duplicate_tasks_as_deprecated(tasks):
    """
    For tasks with the same name, mark every task (except the oldest) as Deprecated.
    Returns a tuple (duplicate_count, duplicates_summary) where:
      - duplicate_count is the total number of tasks marked as duplicates.
      - duplicates_summary is a dict mapping task names to a list of deprecated task IDs.
    """
    duplicate_count = 0
    duplicates_summary = {}
    # Group tasks by their name.
    task_groups = {}
    for task in tasks:
        name = get_task_name(task.get("properties", {}))
        task_groups.setdefault(name, []).append(task)

    for name, group in task_groups.items():
        if len(group) > 1:
            # Sort tasks by created_time (oldest first)
            sorted_group = sorted(group, key=lambda t: t.get("created_time"))
            # Mark all but the oldest task as Deprecated
            duplicates = sorted_group[:-1]
            duplicate_count += len(duplicates)
            duplicates_summary[name] = [t["id"] for t in duplicates]
            for task in duplicates:
                update_task_status(task["id"], "Deprecated")
    return duplicate_count, duplicates_summary

def main():
    logger.info("Starting script to deprecate duplicate tasks.")
    tasks = fetch_tasks_due_today()
    if not tasks:
        logger.info("No incomplete tasks due today found.")
        return

    duplicate_count, duplicates_summary = mark_duplicate_tasks_as_deprecated(tasks)
    logger.info("Finished processing tasks.")
    
    # Print summary of duplicate tasks
    print("Total number of duplicated tasks marked as Deprecated:", duplicate_count)
    if duplicates_summary:
        print("Summary of duplicate tasks:")
        for task_name, ids in duplicates_summary.items():
            print(f" - {task_name}: {len(ids)} duplicates, IDs: {ids}")
    else:
        print("No duplicate tasks were found.")

if __name__ == "__main__":
    main()