import datetime
import requests
from dotenv import load_dotenv
import os
import logging
import pytz  # Add this import at the top of the script

# Replace this with your desired timezone
LOCAL_TIMEZONE = pytz.timezone("America/New_York")

# Load environment variables
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID")

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

# Priority-to-time-block mapping (in minutes)
priority_to_time_block = {
    "Low": 30,
    "Medium": 60,
    "High": 120,
    "Must Be Done Today": 120
}

# Headers for Notion API
headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def get_task_name(properties):
    try:
        return properties.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Unnamed Task")
    except IndexError:
        return "Unnamed Task"


def fetch_all_tasks_sorted_by_priority_created():
    """Fetch all tasks sorted by priority ascending and creation time ascending."""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "sorts": [
            {
                "property": "Priority",
                "direction": "ascending"
            },
            {
                "timestamp": "created_time",
                "direction": "ascending"
            }
        ]
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["results"]
    else:
        logger.error(f"Failed to fetch tasks. Status Code: {response.status_code}, Response: {response.text}")
        return []


def fetch_all_tasks_sorted_by_created():
    """Fetch all tasks sorted by creation time (oldest to newest)."""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "sorts": [
            {
                "timestamp": "created_time",
                "direction": "ascending"
            }
        ]
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["results"]
    else:
        logger.error(f"Failed to fetch tasks. Status Code: {response.status_code}, Response: {response.text}")
        return []


def fetch_unassigned_tasks():
    """Fetch tasks with 'Unassigned' status."""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "filter": {
            "and": [
                {"property": "Priority", "status": {"equals": "Unassigned"}}
            ]
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["results"]
    else:
        logger.error(f"Failed to fetch unassigned tasks. Status Code: {response.status_code}, Response: {response.text}")
        return []


def create_schedule_day_task():
    now = datetime.datetime.now(datetime.timezone.utc)  # Current UTC time
    due = (now + datetime.timedelta(minutes=30)).isoformat()  # 30 minutes from now

    url = f"https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": "Schedule Day"}}]},
            "Class": {
            "select": {
                "name": "Admin"
            }
        },
            "Due": {"date": {"start": now.isoformat(), "end": due}},
            "Priority": {"status": {"name": "High"}}
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        logger.info("'Schedule Day' task created successfully.")
    else:
        logger.error(f"Failed to create 'Schedule Day' task. Status Code: {response.status_code}, Response: {response.text}")


def update_task(task_id, start_time=None, end_time=None, task_name=None, priority=None, status=None):
    url = f"https://api.notion.com/v1/pages/{task_id}"
    payload = {"properties": {}}

    if start_time:
        payload["properties"]["Start Time"] = {"date": {"start": start_time}}
    if end_time:
        payload["properties"]["End Time"] = {"date": {"start": end_time}}
    if priority:
        payload["properties"]["Priority"] = {"status": {"name": priority}}
    if status:
        payload["properties"]["Status"] = {"status": {"name": status}}

    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code == 200:
        logger.info(f"Updated Task: '{task_name}' with changes: {payload['properties']}")
    else:
        logger.error(f"Failed to update Task: '{task_name}'. Status Code: {response.status_code}, Response: {response.text}")

def triage_unassigned_tasks():
    # Mapping from numeric input to priority strings
    priority_mapping = {
        "1": "Low",                   # 1 is Low
        "0": "High",                  # 0 is High
        "c": "Deprecated",            # c is Deprecated (mark as archived)
        " ": "Someday"                # space is Someday (save for later)
    }

    unassigned_tasks = fetch_unassigned_tasks()
    print(f"\nYou have {len(unassigned_tasks)} unassigned tasks.")
    
    for task in unassigned_tasks:
        props = task.get("properties", {})
        task_id = task["id"]
        task_name = get_task_name(props)

        print(f"\nTask: '{task_name}' is currently 'Unassigned'.")
        print("\nPlease choose one of the following options to set a priority or to delete the task:")
        print("[1] Low (Minor priority)")
        print("[0] High (Urgent, needs attention soon)")
        print("[c] Deprecated (Mark as archived)")
        print("[ ] (Space) Someday (Save for later)")

        user_choice = input("\nYour choice: ").strip().lower()

        if user_choice == "c":  # Mark as delete
            update_task(task_id, task_name=task_name, status="Deprecated")
            print(f"Task '{task_name}' has been marked as 'Deprecated' and deleted.")
        
        elif user_choice in priority_mapping:  # Update priority
            chosen_priority = priority_mapping[user_choice]
            update_task(task_id, task_name=task_name, priority=chosen_priority)
            print(f"Task '{task_name}' has been updated to priority: {chosen_priority}.")
        
        else:  # Handle invalid input
            print(f"Invalid choice entered for task '{task_name}'. Please try again.")

def schedule_tasks_in_pattern(tasks, test_mode=True):
    # Separate tasks into high priority and low priority based on their Priority
    # Consider "High" and "Must Be Done Today" as high priority
    # Consider "Medium" and "Low" as lower priority
    high_priority_tasks = []
    low_priority_tasks = []

    for task in tasks:
        props = task.get("properties", {})
        priority = props.get("Priority", {}).get("status", {}).get("name", "Low")
        if priority in ["High", "Must Be Done Today"]:
            high_priority_tasks.append(task)
        else:
            low_priority_tasks.append(task)

    # Get current time and round up to the next 30-minute mark
    now = datetime.datetime.now(datetime.timezone.utc)
    current_time = now.replace(second=0, microsecond=0, minute=0) + datetime.timedelta(
        minutes=(30 - now.minute) % 30
    )

    # Alternate scheduling between high and low priority tasks
    # If one list runs out, schedule the remainder of the other list
    while high_priority_tasks or low_priority_tasks:
        # Take from high priority first if available
        if high_priority_tasks:
            task = high_priority_tasks.pop(0)
            current_time = schedule_single_task(task, current_time, test_mode)

        # Then take from low priority if available
        if low_priority_tasks:
            task = low_priority_tasks.pop(0)
            current_time = schedule_single_task(task, current_time, test_mode)


def schedule_single_task(task, current_time, test_mode):
    props = task.get("properties", {})
    task_id = task["id"]
    task_name = get_task_name(props)
    priority = props.get("Priority", {}).get("status", {}).get("name", "Low")
    time_block_minutes = priority_to_time_block.get(priority, 30)

    start_time = current_time.isoformat()
    end_time = (current_time + datetime.timedelta(minutes=time_block_minutes)).isoformat()

    # Convert times to local timezone
    start_time_utc = datetime.datetime.fromisoformat(start_time)
    end_time_utc = datetime.datetime.fromisoformat(end_time)
    start_time_local = start_time_utc.astimezone(LOCAL_TIMEZONE).strftime("%Y-%m-%d %I:%M %p %Z")
    end_time_local = end_time_utc.astimezone(LOCAL_TIMEZONE).strftime("%Y-%m-%d %I:%M %p %Z")

    print(f"\nTask: '{task_name}' (Priority: {priority})")
    print(f"Proposed Start Time (Local): {start_time_local}")
    print(f"Proposed End Time (Local): {end_time_local}")
    print(f"Proposed Time Block: {time_block_minutes} minutes")
    user_input = input("Apply these changes? (Y/N/High/Delete): ").strip().upper()

    if user_input == "Y":
        if not test_mode:
            update_task(task_id, start_time, end_time, task_name, priority)
        else:
            logger.info(
                f"[TEST MODE] Task: '{task_name}' with Start Time: {start_time_local}, End Time: {end_time_local} would be updated."
            )
    elif user_input == "HIGH":
        if not test_mode:
            update_task(task_id, priority="High", task_name=task_name)
        else:
            logger.info(
                f"[TEST MODE] Task: '{task_name}' would have its priority set to High."
            )
    elif user_input == "DELETE":
        if not test_mode:
            update_task(task_id, status="Deprecated", task_name=task_name)
        else:
            logger.info(
                f"[TEST MODE] Task: '{task_name}' would be marked as Deprecated."
            )
    else:
        logger.info(f"Skipped Task: '{task_name}' - User chose not to update.")

    return current_time + datetime.timedelta(minutes=time_block_minutes)


def assign_dues_and_blocks(test_mode=True):
    # Fetch initial tasks and create a 'Schedule Day' task
    logger.info("Fetching all tasks.")
    tasks = fetch_all_tasks_sorted_by_priority_created()
    create_schedule_day_task()

    # Triage all unassigned tasks
    logger.info("Triage unassigned tasks.")
    triage_unassigned_tasks()

    # After triage, fetch tasks again but sorted by creation time
    logger.info("Refetching tasks after triage and sorting by creation time.")
    tasks_post_triage = fetch_all_tasks_sorted_by_created()

    # Schedule tasks in pattern: high priority, low priority, repeat
    schedule_tasks_in_pattern(tasks_post_triage, test_mode=test_mode)


if __name__ == "__main__":
    assign_dues_and_blocks(test_mode=True)