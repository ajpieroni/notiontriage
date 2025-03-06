import datetime
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
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

# Headers for Notion API
headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# Function to fetch tasks that meet the criteria
def fetch_incomplete_assigned_tasks():
    tasks = []
    next_cursor = None
    today_iso = datetime.date.today().isoformat()

    filter_payload = {
        "and": [
            {"property": "Assigned time", "checkbox": {"equals": True}},
            {"property": "Status", "status": {"does_not_equal": "Done"}},
            {"property": "Status", "status": {"does_not_equal": "Completed"}},
            {"property": "Status", "status": {"does_not_equal": "Archived"}},
            {"property": "Status", "status": {"does_not_equal": "Cancelled"}},
            {"property": "Done", "checkbox": {"equals": False}},
            # {"property": "Due", "date": {"on_or_after": today_iso}},
            {"property": "Due", "date": {"on_or_before": today_iso}}
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

        # Stop if no more pages or 1000 tasks reached
        if not data.get("has_more") or len(tasks) >= 1000:
            break

        next_cursor = data.get("next_cursor")

    # Return only up to 1000 tasks
    return tasks[:1000]
# Function to extract the task name safely
def get_task_name(task):
    try:
        return task["properties"]["Name"]["title"][0]["plain_text"]
    except (KeyError, IndexError, TypeError):
        return "Unnamed Task"

# Function to update the due date of tasks to today without a time
def update_due_date_to_today(task_id, task_name):
    today_iso = datetime.date.today().isoformat()
    url = f"https://api.notion.com/v1/pages/{task_id}"
    payload = {"properties": {"Due": {"date": {"start": today_iso}}}}
    
    response = requests.patch(url, headers=headers, json=payload)

    if response.status_code == 200:
        logger.info(f"Updated task '{task_name}' due date to {today_iso}")
    else:
        logger.error(f"Failed to update task '{task_name}': {response.status_code} - {response.text}")

# Main execution using multithreading
def main():
    tasks = fetch_incomplete_assigned_tasks()
    if not tasks:
        logger.info("No tasks found that meet the criteria.")
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