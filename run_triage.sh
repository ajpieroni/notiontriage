#!/bin/zsh
# Define project directory
PROJECT_DIR="/Users/alexpieroni/Documents/Brain/Projects/notiontriage"
cd "$PROJECT_DIR" || { echo "❌ Cannot change to project directory."; exit 1; }

# (Optional) Source a file with function definitions if needed:
# source ./functions.sh

# Create the virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv || { echo "❌ Failed to create virtual environment."; exit 1; }
fi

# Activate the virtual environment
source venv/bin/activate || { echo "❌ Failed to activate virtual environment."; exit 1; }

echo "🚀 Running master (skipping priority): scheduling (timebudget) -> triage -> duplicates..."

# Run the scheduling step (timebudget integration)
echo "Running timebudget..."
timebudget
if [ $? -ne 0 ]; then
    echo "❌ Scheduling (timebudget) failed. Aborting master."
    deactivate
    exit 1
fi

# Run the triage step
echo "Running triage..."
triage
if [ $? -ne 0 ]; then
    echo "❌ Triage failed. Aborting master."
    deactivate
    exit 1
fi

# Run the duplicates step
echo "Running duplicates..."
duplicates
if [ $? -ne 0 ]; then
    echo "❌ Duplicates failed. Aborting master."
    deactivate
    exit 1
fi

echo "✅ All steps completed successfully!"

# Optionally, if main.py does additional work (and accepts a --today flag),
# you can run it non-interactively. For example:
# printf "today\n" | python3 main.py --today

# Deactivate the virtual environment after execution
deactivate