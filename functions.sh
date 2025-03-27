#!/bin/zsh
# functions.sh – Custom project management and scheduling functions for notiontriage

# ---------------------------
# Project Management Functions
# ---------------------------
function triage() {
    PROJECT_DIR=~/Documents/Brain/Projects/notiontriage
    if [ ! -d "$PROJECT_DIR" ]; then
        echo "❌ Project not found. Please ensure 'notiontriage' exists in '~/Documents/Brain/Projects'."
        return 1
    fi
    cd "$PROJECT_DIR" || { echo "❌ Failed to navigate to project directory."; return 1; }
    if ! command -v python3 &>/dev/null; then
        echo "❌ Python 3 is not installed. Please install Python 3 to continue."
        return 1
    fi
    echo "🔧 Setting up your environment for triage..."
    [ -d "venv" ] && { echo "🗑️ Removing existing virtual environment..."; rm -rf venv; }
    python3 -m venv venv || { echo "❌ Failed to create virtual environment."; return 1; }
    source venv/bin/activate || { echo "❌ Failed to activate virtual environment."; return 1; }
    echo "📥 Installing dependencies for triage..."
    pip install -r requirements.txt > install.log 2>&1 || { echo "❌ Error installing dependencies. Check install.log for details."; deactivate; return 1; }
    echo "✅ Environment ready."
    echo "🚀 Starting triage..."
    python3 main.py
    [ $? -ne 0 ] && echo "❌ The script encountered an issue. Check logs for details." || echo "🎉 All done!"
    deactivate
    rm -rf ./venv
}

function capture() {
    PROJECT_DIR=~/Documents/Brain/Projects/notiontriage
    if [ ! -d "$PROJECT_DIR" ]; then
        echo "❌ Project not found: $PROJECT_DIR"
        return 1
    fi
    cd "$PROJECT_DIR" || { echo "❌ Failed to navigate to project directory."; return 1; }
    if ! command -v python3 &>/dev/null; then
        echo "❌ Python 3 is not installed. Please install Python 3 to continue."
        return 1
    fi
    [ ! -d "venv" ] && { echo "🔧 Creating virtual environment..."; python3 -m venv venv; }
    source venv/bin/activate || { echo "❌ Failed to activate virtual environment."; return 1; }
    if [ ! -f "requirements.txt" ]; then
        echo "❌ Missing requirements.txt!"
        deactivate
        return 1
    fi
    echo "📥 Installing dependencies for capture..."
    pip install -r requirements.txt > install.log 2>&1
    echo "📝 Paste your messy task list below (Press ENTER, then CTRL+D when done):"
    input_text=$(cat)
    [ -z "$input_text" ] && { echo "❌ No input detected. Exiting..."; deactivate; return; }
    cleaned_tasks=$(python3 - <<END
import re
messy_input = '''$input_text'''
tasks = re.findall(r'^\s*Issue\s*(.*)', messy_input, re.MULTILINE)
tasks = [task.strip() for task in tasks if task.strip() and len(task.strip()) >= 10]
print("\n".join(tasks))
END
)
    [ -z "$cleaned_tasks" ] && { echo "❌ No valid tasks extracted. Please check your input format."; deactivate; return; }
    echo -e "\n📋 Cleaned Task List:\n"
    echo "$cleaned_tasks"
    echo -e "\nRun tasks.py with these tasks? (y/n)"
    read -r confirm
    if [[ "$confirm" == "y" ]]; then
        echo "$cleaned_tasks" > messy_input.txt
        echo "🚀 Running tasks.py..."
        python3 tasks.py
        rm messy_input.txt
    else
        echo "❌ Task execution canceled."
    fi
    deactivate
}

function duplicates() {
    PROJECT_DIR=~/Documents/Brain/Projects/notiontriage
    if [ ! -d "$PROJECT_DIR" ]; then
        echo "❌ Project not found. Please ensure 'notiontriage' exists in '~/Documents/Brain/Projects'."
        return 1
    fi
    cd "$PROJECT_DIR" || { echo "❌ Failed to navigate to project directory."; return 1; }
    if ! command -v python3 &>/dev/null; then
        echo "❌ Python 3 is not installed. Please install Python 3 to continue."
        return 1
    fi
    echo "🔧 Setting up your environment for duplicates..."
    [ -d "venv" ] && { echo "🗑️ Removing existing virtual environment..."; rm -rf venv; }
    python3 -m venv venv || { echo "❌ Failed to create virtual environment."; return 1; }
    source venv/bin/activate || { echo "❌ Failed to activate virtual environment."; return 1; }
    echo "�� Installing dependencies for duplicates..."
    pip install -r requirements.txt > install.log 2>&1 || { echo "❌ Error installing dependencies. Check install.log for details."; deactivate; return 1; }
    echo "✅ Environment ready."
    echo "🚀 Starting duplicates..."
    python3 duplicates.py
    [ $? -ne 0 ] && echo "❌ The script encountered an issue. Check logs for details." || echo "🎉 All done!"
    deactivate
}

function priority() {
    PROJECT_DIR=~/Documents/Brain/Projects/notiontriage
    if [ ! -d "$PROJECT_DIR" ]; then
        echo "❌ Project not found. Please ensure 'notiontriage' exists in '~/Documents/Brain/Projects'."
        return 1
    fi
    cd "$PROJECT_DIR" || { echo "❌ Failed to navigate to project directory."; return 1; }
    if ! command -v python3 &>/dev/null; then
        echo "❌ Python 3 is not installed. Please install Python 3 to continue."
        return 1
    fi
    echo "🔧 Setting up your environment for priority..."
    [ -d "venv" ] && { echo "🗑️ Removing existing virtual environment..."; rm -rf venv; }
    python3 -m venv venv || { echo "❌ Failed to create virtual environment."; return 1; }
    source venv/bin/activate || { echo "❌ Failed to activate virtual environment."; return 1; }
    echo "📥 Installing dependencies for priority..."
    pip install -r requirements.txt > install.log 2>&1 || { echo "❌ Error installing dependencies. Check install.log for details."; deactivate; return 1; }
    echo "✅ Environment ready."
    echo "🚀 Starting priority..."
    python3 priority.py
    [ $? -ne 0 ] && echo "❌ The script encountered an issue. Check logs for details." || echo "🎉 All done!"
    deactivate
}

function timebudget() {
    PROJECT_DIR=~/Documents/Brain/Projects/notiontriage
    if [ ! -d "$PROJECT_DIR" ]; then
        echo "❌ Project not found. Please ensure 'notiontriage' exists in '~/Documents/Brain/Projects'."
        return 1
    fi
    cd "$PROJECT_DIR" || { echo "❌ Failed to navigate to project directory."; return 1; }
    if ! command -v python3 &>/dev/null; then
        echo "❌ Python 3 is not installed. Please install Python 3 to continue."
        return 1
    fi
    echo "🔧 Setting up your environment for timebudget..."
    [ -d "venv" ] && { echo "🗑️ Removing existing virtual environment..."; rm -rf venv; }
    python3 -m venv venv || { echo "❌ Failed to create virtual environment."; return 1; }
    source venv/bin/activate || { echo "❌ Failed to activate virtual environment."; return 1; }
    echo "📥 Installing dependencies for timebudget..."
    pip install -r requirements.txt > install.log 2>&1 || { echo "❌ Error installing dependencies. Check install.log for details."; deactivate; return 1; }
    echo "✅ Environment ready."
    echo "�� Starting timebudgeting..."
    python3 timebudget.py
    [ $? -ne 0 ] && echo "❌ The script encountered an issue. Check logs for details." || echo "🎉 All done!"
    deactivate
}

function unassigned() {
    PROJECT_DIR=~/Documents/Brain/Projects/notiontriage
    if [ ! -d "$PROJECT_DIR" ]; then
        echo "❌ Project not found. Please ensure 'notiontriage' exists in '~/Documents/Brain/Projects'."
        return 1
    fi
    cd "$PROJECT_DIR" || { echo "❌ Failed to navigate to project directory."; return 1; }
    if ! command -v python3 &>/dev/null; then
        echo "❌ Python 3 is not installed. Please install Python 3 to continue."
        return 1
    fi
    echo "🔧 Setting up your environment for unassignment..."
    [ -d "venv" ] && { echo "🗑️ Removing existing virtual environment..."; rm -rf venv; }
    python3 -m venv venv || { echo "❌ Failed to create virtual environment."; return 1; }
    source venv/bin/activate || { echo "❌ Failed to activate virtual environment."; return 1; }
    echo "📥 Installing dependencies for unassignment..."
    pip install -r requirements.txt > install.log 2>&1 || { echo "❌ Error installing dependencies. Check install.log for details."; deactivate; return 1; }
    echo "✅ Environment ready."
    echo "🚀 Starting unassignment..."
    python3 cleanslate.py
    [ $? -ne 0 ] && echo "❌ The script encountered an issue. Check logs for details." || echo "🎉 All done!"
    deactivate
}

# ---------------------------
# Master Function
# ---------------------------
function master() {
    echo "🚀 Running master: priority -> triage -> scheduling -> duplicates..."

    # Run the priority step
    priority
    if [ $? -ne 0 ]; then
        echo "❌ Priority failed. Aborting master."
        return 1
    fi

    # Ask the user about timeblocking before scheduling
    echo -n "Have you finished timeblocking for today? (YES/NO): "
    read -r answer
    answer=$(echo "$answer" | tr '[:upper:]' '[:lower:]')
    if [[ "$answer" == "no" ]]; then
        echo "Exiting master due to incomplete timeblocking."
        exit 1
    fi

    # Run the scheduling step (timebudget integration)
    echo "Running timebudget..."
    timebudget
    if [ $? -ne 0 ]; then
        echo "❌ Scheduling failed. Aborting master."
        return 1
    fi

    # Run the triage step
    triage
    if [ $? -ne 0 ]; then
        echo "❌ Triage failed. Aborting master."
        return 1
    fi

    # Run the duplicates step
    duplicates
    if [ $? -ne 0 ]; then
        echo "❌ Duplicates failed."
        return 1
    fi

    echo "✅ All steps completed successfully!"
}
