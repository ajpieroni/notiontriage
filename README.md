# Notion Triage

A Python-based task management and scheduling system that integrates with Notion and Google Calendar to help organize and schedule your tasks efficiently.

## Features

- Integration with Notion for task management
- Google Calendar integration for schedule management
- Automatic task scheduling based on priority and availability
- Time block management and optimization
- Command-line interface for task management
- Support for multiple calendar sources
- Timezone-aware scheduling

## Prerequisites

- Python 3.x
- Notion API key
- Google Calendar API credentials
- Virtual environment (recommended)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd notiontriage
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with the following variables:
```
NOTION_API_KEY=your_notion_api_key
DATABASE_ID=your_notion_database_id
```

5. Set up Google Calendar credentials:
- Place your `credentials.json` file in the project root
- Run the application once to authenticate with Google Calendar

## Usage

### Running the Triage System

1. Activate the virtual environment:
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Run the main script:
```bash
python main.py
```

### Available Scripts

- `run_triage.sh`: Main script for running the triage system
- `concurrent_run_triage.sh`: Run multiple triage instances concurrently
- `run_venv.sh`: Script to run the application in a virtual environment

### Key Features

- Task prioritization and scheduling
- Calendar integration
- Time block management
- Task status tracking
- Due date management

## Project Structure

- `main.py`: Core application logic
- `timebudget.py`: Time management utilities
- `priority.py`: Task prioritization logic
- `cleanbeforenow.py`: Task cleanup utilities
- `cleanslate.py`: Task reset utilities
- `duplicates.py`: Duplicate task management
- `notes.py`: Note management
- `tasks.py`: Task management utilities

## Notes

- The `run_triage.sh` script used in daily operations is located at `/Users/Shared`
- Make sure to keep your API keys and credentials secure
- Regular backups of your task database are recommended

## License

[Add your license information here]

