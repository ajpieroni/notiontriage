#!/bin/zsh

# Define project directory
PROJECT_DIR="/Users/alexpieroni/Documents/Brain/Projects/notiontriage"
cd "$PROJECT_DIR" || { echo "❌ Cannot change to project directory."; exit 1; }

# Check if a Python script argument is provided
if [ -z "$1" ]; then
    echo "❌ No Python script provided. Usage: run_venv <script.py>"
    exit 1
fi

SCRIPT="$1"

# Create the virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv || { echo "❌ Failed to create virtual environment."; exit 1; }
fi

# Activate the virtual environment
source venv/bin/activate || { echo "❌ Failed to activate virtual environment."; exit 1; }

# Run the provided Python script
echo "🚀 Running $SCRIPT..."
python3 "$SCRIPT"
STATUS=$?

if [ $STATUS -ne 0 ]; then
    echo "❌ $SCRIPT failed. Aborting."
    deactivate
    exit 1
fi

echo "✅ $SCRIPT completed successfully!"

# Deactivate the virtual environment after execution
deactivate