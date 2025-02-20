#!/bin/bash

# Notion API Variables
NOTION_API_KEY="secret_9G2s7Fe6NNOwPzo48y51xxxPl0vRtS8qV4LG7c3t5qw"
DATABASE_ID="7dc24a1a872f4975a0c65203652ad54a"
NOTION_API_VERSION="2022-06-28"
NOTION_URL="https://api.notion.com/v1/pages"

# Check if at least one argument is passed
if [ "$#" -eq 0 ]; then
    echo "Usage: $0 \"Task Title 1\" \"Task Title 2\" ..."
    exit 1
fi

# Loop through each task and format it before sending it to Notion
for TASK_TITLE in "$@"; do
    TASK_TITLE=$(echo "$TASK_TITLE" | xargs) # Trim spaces

    echo "Adding task: $TASK_TITLE"

    # Send formatted task to Notion API
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
                    "select": { "name": "Academics" }
                }
            }
        }'

    echo -e "\nTask \"$TASK_TITLE\" added to Notion database."
done
