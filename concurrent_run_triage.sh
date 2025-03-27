#!/bin/zsh
# Check if the script was invoked with the argument 'Daily'

# Define color variables
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Record start time
start_time=$(date +%s)
echo -e "${GREEN}⏰ Script started at: $(date)${NC}"

# Define project directory
PROJECT_DIR="/Users/alexpieroni/Documents/Brain/Projects/notiontriage"
cd "$PROJECT_DIR" || { echo -e "${RED}❌ Cannot change to project directory.${NC}"; exit 1; }

if [ -f requirements.txt ]; then
    echo -e "${YELLOW}📥 Installing dependencies from requirements.txt...${NC}"
    pip install -q -r requirements.txt || { echo -e "${RED}❌ Failed to install dependencies from requirements.txt.${NC}"; exit 1; }
else
    echo -e "${RED}❌ requirements.txt file not found. Aborting.${NC}"
    exit 1
fi

echo -e "${GREEN}🚀 Running master concurrently: scheduling (timebudget), triage, duplicates...${NC}"

# Array to hold background process IDs
pids=()

# Run the scheduling step (cleanbeforenow) by executing cleanbeforenow.py directly
echo -e "${YELLOW}Running UNASSIGNED BEFORE NOW...${NC}"
python3 cleanbeforenow.py &
pids+=($!)

# Run the scheduling step (timebudget integration) by executing timebudget.py directly
echo -e "${YELLOW}🗓️ Running timebudget...${NC}"
python3 timebudget.py &
pids+=($!)

# Run the triage step by executing main.py directly
echo -e "${YELLOW}🚦 Running triage...${NC}"
python3 main.py --today &
pids+=($!)

# Run the duplicates step by executing duplicates.py directly
echo -e "${YELLOW}🧹 Running duplicates...${NC}"
python3 duplicates.py &
pids+=($!)

# Wait for all background processes and capture errors
error=0
for pid in "${pids[@]}"; do
    wait "$pid" || error=1
done

if [ $error -ne 0 ]; then
    echo -e "${RED}❌ One or more steps failed. Aborting master.${NC}"
    conda deactivate
    exit 1
fi

echo -e "${GREEN}✅ All steps completed successfully!${NC}"

# Record end time and compute elapsed time
end_time=$(date +%s)
elapsed=$(( end_time - start_time ))
echo -e "${GREEN}⏰ Finished at: $(date)${NC}"
echo -e "${GREEN}⏱ Total elapsed time: ${elapsed} seconds.${NC}"

# Deactivate the virtual environment after execution
conda deactivate