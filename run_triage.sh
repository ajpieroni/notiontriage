#!/bin/zsh
# Define project directory
PROJECT_DIR="/Users/alexpieroni/Documents/Brain/Projects/notiontriage"
cd "$PROJECT_DIR" || { echo "❌ Cannot change to project directory."; exit 1; }

# Create the virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv || { echo "❌ Failed to create virtual environment."; exit 1; }
fi

# Activate the virtual environment
source venv/bin/activate || { echo "❌ Failed to activate virtual environment."; exit 1; }

# (Optional) Install dependencies if needed; uncomment below if required:
# echo "📥 Installing dependencies..."
# pip install -r requirements.txt || { echo "❌ Dependency installation failed."; deactivate; exit 1; }

# Run main.py with "today" as the default input
python3 main.py <<< "today"

# Deactivate the virtual environment after execution
deactivate