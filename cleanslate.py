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

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# Time zones
UTC = pytz.utc
ET = pytz.timezone("America/New_York")  # Eastern Time Zone

def get_today_datetime_range():
    """Returns today's start and end time in UTC, ensuring correct handling of ET timezone shifts."""
    now_utc = datetime.datetime.now(UTC)

    # Start of today in ET, converted to UTC
    start_of_today_et = now_utc.astimezone(ET).replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_today_utc = start_of_today_et.astimezone(UTC)

    # End of today in ET (23:59:59), converted to UTC
    end_of_today_et = now_utc.astimezone(ET).replace(hour=23, minute=59, second=59, microsecond=999999)
    end_of_today_utc = end_of_today_et.astimezone(UTC)

    logger.debug(f"Today's Start Time (ET): {start_of_today_et.isoformat()} | (UTC): {start_of_today_utc.isoformat()}")
    logger.debug(f"Today's End Time (ET): {end_of_today_et.isoformat()} | (UTC): {end_of_today_utc.isoformat()}")

    return start_of_today_utc.isoformat(), end_of_today_utc.isoformat()

def fetch_incomplete_assigned_tasks():
    """Fetches all tasks that are due today in ET and meet the criteria."""
    tasks = []
    next_cursor = None
    start_of_today, end_of_today = get_today_datetime_range()

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
            {"property": "Due", "date": {"on_or_after": start_of_today}},
            {"property": "Due", "date": {"on_or_before": end_of_today}}
        ]
    }

    logger.debug(f"Filter Payload: {filter_payload}")

    while True:
        payload = {"filter": filter_payload}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        response = requests.post(url, headers=headers, json=payload)

        logger.debug(f"Request sent to Notion API: {url}")
        logger.debug(f"Payload: {payload}")

        if response.status_code != 200:
            logger.error(f"Failed to fetch tasks: {response.status_code} - {response.text}")
            break

        data = response.json()
        tasks.extend(data.get("results", []))
        logger.debug(f"Fetched {len(data.get('results', []))} tasks from Notion.")

        # Stop if no more pages or max 1000 tasks reached
        if not data.get("has_more") or len(tasks) >= 1000:
            break

        next_cursor = data.get("next_cursor")

    logger.info(f"Total tasks fetched: {len(tasks)}")
    return tasks[:1000]

def get_task_name(task):
    """Extracts the task name safely with debugging."""
    try:
        task_name = task["properties"]["Name"]["title"][0]["plain_text"]
        logger.debug(f"Extracted Task Name: {task_name}")
        return task_name
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Error extracting task name: {e}")
        return "Unnamed Task"

def update_due_date_to_today(task_id, task_name):
    """Updates the task's due date to today in ET while logging the response."""
    today_iso = datetime.datetime.now(UTC).date().isoformat()
    today_et = datetime.datetime.now(ET).date().isoformat()
    url = f"https://api.notion.com/v1/pages/{task_id}"

    # Define headers inside function
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    # Ensure the correct payload structure
    payload = {
        "properties": {
            "Due": {
                "date": {
                    "start": today_iso,
                    # "time_zone": "America/New_York"  # Explicitly set ET
                }
            }
        }
    }

    logger.debug(f"Updating Task '{task_name}' to Due Date (ET): {today_et}")
    logger.debug(f"PATCH Request URL: {url}")
    logger.debug(f"PATCH Payload: {payload}")

    response = requests.patch(url, headers=headers, json=payload)

    if response.status_code == 200:
        logger.info(f"✅ Successfully updated task '{task_name}' due date to {today_et} (ET)")
    else:
        logger.error(f"❌ Failed to update task '{task_name}': {response.status_code} - {response.text}")

def main():
    """Main execution with detailed debugging."""
    logger.info("Fetching incomplete assigned tasks...")
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