#!/bin/bash

# Load environment variables from the .env file if it exists
if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
fi

# Verify that the required environment variables are set
if [ -z "$NOTION_API_KEY" ] || [ -z "$DATABASE_ID" ] || [ -z "$NOTION_API_VERSION" ]; then
  echo "Error: NOTION_API_KEY, DATABASE_ID, and NOTION_API_VERSION must be set."
  exit 1
fi

NOTION_URL="https://api.notion.com/v1/pages"

# Ensure at least one task title is passed as an argument
if [ "$#" -eq 0 ]; then
  echo "Usage: $0 \"Task Title 1\" \"Task Title 2\" ..."
  exit 1
fi

# Process each task title and send it to Notion
for TASK_TITLE in "$@"; do
  TASK_TITLE=$(echo "$TASK_TITLE" | xargs)  # Trim leading/trailing spaces

  echo "Adding task: $TASK_TITLE"

  curl -X POST "$NOTION_URL" \
    -H "Authorization: Bearer $NOTION_API_KEY" \
    -H "Content-Type: application/json" \
    -H "Notion-Version: $NOTION_API_VERSION" \
    --data '{
      "parent": { "database_id": "'"$DATABASE_ID"'" },
      "properties": {
        "Name": {
          "title": [
            { "text": { "content": "'"$TASK_TITLE"'" } }
          ]
        },
        "Class": {
          "select": { "name": "Kyros" }
        }
      }
    }'

  echo -e "\nTask \"$TASK_TITLE\" added to Notion database."
done
