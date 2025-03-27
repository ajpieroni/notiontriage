import datetime
import pytz
import requests
import os
import logging
from dotenv import load_dotenv
import concurrent.futures

# Load environment variables
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# Time zones
UTC = pytz.utc
ET = pytz.timezone("America/New_York")  # Eastern Time Zone

def fetch_incomplete_assigned_tasks():
    """Fetches tasks that are overdue (due date before the current moment)."""
    tasks = []
    next_cursor = None
    now_iso = datetime.datetime.now(UTC).isoformat()
    # logger.info(f"Current UTC time for filtering tasks: {now_iso}")

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    filter_payload = {
        "and": [
            {"property": "Assigned time", "checkbox": {"equals": True}},
            {"property": "Status", "status": {"does_not_equal": "Done"}},
            {"property": "Status", "status": {"does_not_equal": "Completed"}},
            {"property": "Status", "status": {"does_not_equal": "Deprecated"}},
            {"property": "Status", "status": {"does_not_equal": "Handed Off"}},
            {"property": "Status", "status": {"does_not_equal": "In progress"}},
            {"property": "Done", "checkbox": {"equals": False}},
            # Only apply to tasks with a due date before the current time
            {"property": "Due", "date": {"before": now_iso}}
        ]
    }
    
    # logger.info(f"Using filter payload: {filter_payload}")

    while True:
        payload = {"filter": filter_payload}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            logger.error(f"Failed to fetch tasks: {response.status_code} - {response.text}")
            break

        data = response.json()
        # logger.info(f"Fetched {len(data.get('results', []))} tasks in this batch.")
        tasks.extend(data.get("results", []))

        if not data.get("has_more") or len(tasks) >= 1000:
            break

        next_cursor = data.get("next_cursor")

    # logger.info(f"✅ Total overdue tasks fetched: {len(tasks)}")
    return tasks[:1000]

def get_task_name(task):
    """Extracts the task name safely."""
    try:
        return task["properties"]["Name"]["title"][0]["plain_text"]
    except (KeyError, IndexError, TypeError):
        return "Unnamed Task"

def update_due_date_to_today(task):
    """Updates the task's due date to today in ET while logging the response. Skips tasks whose due start is after now."""
    task_id = task["id"]
    task_name = get_task_name(task)
    
    # Check if the task has a Due date and extract the start date
    due_date_str = None
    if "Due" in task["properties"] and task["properties"]["Due"]["date"] and "start" in task["properties"]["Due"]["date"]:
        due_date_str = task["properties"]["Due"]["date"]["start"]

    now_utc = datetime.datetime.now(UTC)
    
    if due_date_str:
        try:
            # Convert due_date_str to a datetime object (handle potential 'Z' suffix)
            due_date = datetime.datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
        except Exception as e:
            logger.error(f"Error parsing due date for task '{task_name}': {e}")
            due_date = None
        
        if due_date and due_date > now_utc:
            # logger.info(f"Task '{task_name}' due start ({due_date}) is after now ({now_utc}). Running UNASSIGNED BEFORE NOW...")
            return  # Skip updating if the due start is in the future
    else:
        logger.info(f"Task '{task_name}' has no due date; proceeding with update.")
    
    # logger.info(f"Attempting to update task {task_id} ('{task_name}') to new due date.")
    today_iso = datetime.datetime.now(UTC).date().isoformat()
    url = f"https://api.notion.com/v1/pages/{task_id}"
    
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    
    payload = {
        "properties": {
            "Due": {
                "date": {
                    "start": today_iso,
                }
            }
        }
    }
    
    logger.debug(f"Payload for updating task {task_id}: {payload}")

    response = requests.patch(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        print(f"'\033[1m{task_name}\033[0m' has been pushed.")
    else:
        logger.error(f"Failed to update task '{task_name}': {response.status_code} - {response.text}")

def main():
    """Main execution."""
    # logger.info("Starting main execution to update overdue tasks (excluding tasks 'In progress').")
    print("📌 Fetching overdue tasks...")
    tasks = fetch_incomplete_assigned_tasks()
    
    if not tasks:
        # logger.info("🎉 No tasks to update!")
        print("✅ There are no tasks to update")
        return

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for task in tasks:
            futures.append(executor.submit(update_due_date_to_today, task))
        concurrent.futures.wait(futures)

    # logger.info("Finished updating tasks.")

if __name__ == "__main__":
    main()