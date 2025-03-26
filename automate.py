import subprocess
import requests
import json
import os
import logging
import time
import re
from collections import defaultdict
from dotenv import load_dotenv

# ----- Logging Setup -----
load_dotenv()  # Load environment variables from .env
NOTION_API_KEY = os.getenv("NOTION_API_KEY")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ----- LLM CALL FUNCTIONS -----

def call_ollama(task_title):
    logging.info(f"Calling ollama for task title: {task_title}")
    start_time = time.perf_counter()
    prompt = f"""You are an expert task assessor. Given an input string 'title' that represents a task name, evaluate the task and output two variables in JSON format:
"new_priority": (High, Medium, or Low) based on the task's intrinsic importance, complexity, and impact,
"new_estimated_time": a human-readable time estimate (e.g., '5 minutes', '15 minutes', '1 hour', etc) based on the typical duration for similar tasks.
For example, if the input 'title' is '1 Hr of GMAT Prep', the output should be:
{{"new_priority": "High", "new_estimated_time": "1 hour"}}
Now, process the following input:
title: {task_title}"""
    
    result = subprocess.run(
        ["ollama", "run", "llama3.2"],
        input=prompt.encode('utf-8'),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    duration = time.perf_counter() - start_time
    logging.info(f"Ollama call took {duration:.2f} seconds")
    if result.returncode != 0:
        error_msg = result.stderr.decode('utf-8')
        logging.error(f"Ollama call failed: {error_msg}")
        raise RuntimeError(f"Ollama call failed: {error_msg}")
    
    output = result.stdout.decode('utf-8').strip()
    logging.debug(f"Ollama output: {output}")
    return output

def parse_json_output(json_output):
    logging.info("Parsing JSON output from ollama")
    try:
        data = json.loads(json_output)
        # Check that the required keys exist
        if "new_priority" in data and "new_estimated_time" in data:
            return data["new_priority"], data["new_estimated_time"]
        else:
            logging.error("JSON decoded but missing required keys.")
            raise ValueError("Missing required keys in JSON output")
    except Exception as e:
        logging.warning("JSON parsing failed, attempting regex extraction.")
        return parse_json_output_with_regex(json_output)

def parse_json_output_with_regex(text):
    # Use regex to extract new_priority and new_estimated_time from the text
    priority_match = re.search(r'"new_priority":\s*"([^"]+)"', text)
    time_match = re.search(r'"new_estimated_time":\s*"([^"]+)"', text)
    if priority_match and time_match:
        new_priority = priority_match.group(1)
        new_estimated_time = time_match.group(1)
        logging.info("Regex extraction succeeded.")
        return new_priority, new_estimated_time
    else:
        logging.error("Regex extraction failed. Parsed output: " + text)
        raise ValueError("Regex extraction failed. Parsed output: " + text)

# ----- Notion API FUNCTIONS -----

def fetch_tasks(filter_payload, sorts_payload, notion_api_key, database_id):
    logging.info("Fetching tasks from Notion")
    start_time = time.perf_counter()
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    payload = {
        "filter": filter_payload,
        "sorts": sorts_payload
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        logging.error(f"Error fetching tasks: {response.status_code} {response.text}")
        raise RuntimeError(f"Error fetching tasks: {response.status_code} {response.text}")
    duration = time.perf_counter() - start_time
    logging.info(f"Fetched tasks in {duration:.2f} seconds")
    return response.json().get("results", [])

def fetch_unassigned_tasks(notion_api_key, database_id):
    logging.info("Fetching unassigned tasks from Notion database")
    filter_payload = {
        "and": [
            {"property": "Priority", "status": {"equals": "Unassigned"}},
            {"property": "Status", "status": {"does_not_equal": "Done"}},
            {"property": "Status", "status": {"does_not_equal": "Handed Off"}},
            {"property": "Status", "status": {"does_not_equal": "Deprecated"}},
            {"property": "Status", "status": {"does_not_equal": "Waiting on Reply"}},
            {"property": "Status", "status": {"does_not_equal": "Waiting on other task"}},
            {"property": "Done", "checkbox": {"equals": False}}
        ]
    }
    sorts_payload = [{"timestamp": "created_time", "direction": "ascending"}]
    return fetch_tasks(filter_payload, sorts_payload, notion_api_key, database_id)

def update_task_priority_and_estimated_time(task_id, new_priority, new_estimated_time, notion_api_key):
    logging.info(f"Updating task {task_id} with new priority '{new_priority}' and estimated time '{new_estimated_time}'")
    start_time = time.perf_counter()
    url = f"https://api.notion.com/v1/pages/{task_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    payload = {
        "properties": {
            "Priority": {"status": {"name": new_priority}},
            "Level of Effort": {"select": {"name": new_estimated_time}}
        }
    }
    response = requests.patch(url, headers=headers, json=payload)
    duration = time.perf_counter() - start_time
    if response.status_code != 200:
        logging.error(f"Error updating task {task_id}: {response.status_code} {response.text}")
    else:
        logging.info(f"Task {task_id} updated successfully in {duration:.2f} seconds!")
    return response.json()

# ----- Helper Function to Get Task Title -----

def get_task_title(task):
    try:
        title_parts = task["properties"]["Name"]["title"]
        return "".join([part["plain_text"] for part in title_parts])
    except KeyError:
        return "Unknown"

# ----- MAIN PROCESSING FUNCTION -----

def main():

    notion_api_key = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("DATABASE_ID")
    
    logging.info("Starting task update process")
    tasks = fetch_unassigned_tasks(notion_api_key, database_id)
    if not tasks:
        logging.info("No unassigned tasks found.")
        return

    # Group tasks by their title to batch process similar tasks.
    grouped_tasks = {}
    for task in tasks:
        title = get_task_title(task)
        grouped_tasks.setdefault(title, []).append(task)
    
    # Process each group of similar tasks.
    for title, task_list in grouped_tasks.items():
        logging.info(f"Found {len(task_list)} task(s) with title: '{title}'")
        update_group = input("Do you want to update all tasks with this title? (Y/n): ").strip().lower()
        if update_group in ("", "y", "yes"):
            try:
                start_llm = time.perf_counter()
                json_output = call_ollama(title)
                llm_duration = time.perf_counter() - start_llm
                logging.info(f"LLM evaluation for '{title}' completed in {llm_duration:.2f} seconds")
                logging.debug(f"Ollama output (JSON): {json_output}")
                new_priority, new_estimated_time = parse_json_output(json_output)
                logging.info(f"Evaluation for '{title}': New Priority: {new_priority}, New Estimated Time: {new_estimated_time}")
            except Exception as e:
                logging.error(f"Error processing title '{title}': {e}")
                continue

            confirm = input("Apply this update to all these tasks? (Y/n): ").strip().lower()
            if confirm in ("", "y", "yes"):
                for task in task_list:
                    task_id = task["id"]
                    update_start = time.perf_counter()
                    update_task_priority_and_estimated_time(task_id, new_priority, new_estimated_time, notion_api_key)
                    update_duration = time.perf_counter() - update_start
                    logging.info(f"Updated task {task_id} in {update_duration:.2f} seconds")
            else:
                logging.info(f"Skipping update for tasks with title '{title}'")
        else:
            logging.info(f"Skipping tasks with title '{title}'")
    
    logging.info("Finished processing all tasks.")

if __name__ == "__main__":
    main()