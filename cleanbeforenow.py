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
            {"property": "Done", "checkbox": {"equals": False}},
            # Only apply to tasks with a due date before the current time
            {"property": "Due", "date": {"before": now_iso}}
        ]
    }

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
        tasks.extend(data.get("results", []))

        if not data.get("has_more") or len(tasks) >= 1000:
            break

        next_cursor = data.get("next_cursor")

    logger.info(f"✅ Total overdue tasks fetched: {len(tasks)}")
    return tasks[:1000]

def get_task_name(task):
    """Extracts the task name safely."""
    try:
        return task["properties"]["Name"]["title"][0]["plain_text"]
    except (KeyError, IndexError, TypeError):
        return "Unnamed Task"

def update_due_date_to_today(task_id, task_name):
    """Updates the task's due date to today in ET while logging the response."""
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

    response = requests.patch(url, headers=headers, json=payload)

    if response.status_code == 200:
        logger.info(f"✅ Updated: '{task_name}'")
    else:
        logger.error(f"❌ Failed to update '{task_name}': {response.status_code} - {response.text}")

def main():
    """Main execution."""
    print("📌 Fetching overdue tasks...")
    tasks = fetch_incomplete_assigned_tasks()
    
    if not tasks:
        logger.info("🎉 No tasks to update!")
        return

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for task in tasks:
            task_id = task["id"]
            task_name = get_task_name(task)
            futures.append(executor.submit(update_due_date_to_today, task_id, task_name))
        concurrent.futures.wait(futures)

if __name__ == "__main__":
    main()