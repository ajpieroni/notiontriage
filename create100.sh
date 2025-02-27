#!/bin/bash

# Notion API Variables
NOTION_API_KEY="secret_9G2s7Fe6NNOwPzo48y51xxxPl0vRtS8qV4LG7c3t5qw"
DATABASE_ID="7dc24a1a872f4975a0c65203652ad54a"
NOTION_API_VERSION="2022-06-28"
NOTION_URL="https://api.notion.com/v1/pages"

# Loop to create 100 tasks
for i in {1..100}; do
    TASK_TITLE="test$i"
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
                     "select": { "name": "Kyros" }
                 }
             }
         }'

    echo -e "\nTask \"$TASK_TITLE\" added to Notion database."
done
