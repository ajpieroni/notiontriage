import re
import subprocess

def parse_markdown_tasks(text):
    """
    Parse tasks from markdown text.
    
    It extracts tasks starting with a dash. Only items that are incomplete (i.e. either
    with a checkbox [ ] or no checkbox) are included. Nested tasks (indented) are appended
    to the last main task.
    """
    lines = text.splitlines()
    tasks = []
    current_task = None
    for line in lines:
        # Skip lines that don't look like list items
        if not line.strip().startswith('-'):
            continue

        # Match list items with an optional checkbox.
        m = re.match(r'^(\s*)-\s*(\[[xX ]\])?\s*(.+)$', line)
        if not m:
            continue

        indent = len(m.group(1))
        checkbox = m.group(2)  # may be None if no checkbox
        task_text = m.group(3).strip()

        # If the checkbox is present and marked complete, skip this line.
        if checkbox and checkbox.lower() == "[x]":
            continue

        # If indent is small, assume it's a main task; otherwise a subtask.
        if indent < 2:
            current_task = {"text": task_text, "subtasks": []}
            tasks.append(current_task)
        else:
            if current_task is not None:
                current_task["subtasks"].append(task_text)
    return tasks

# Read the messy input from a file
with open("messy_input.txt", "r") as f:
    messy_text = f.read()

# Parse tasks from the file
tasks = parse_markdown_tasks(messy_text)

# For debugging, print out the parsed tasks
print("Extracted Tasks:")
for t in tasks:
    if t["subtasks"]:
        print(f'- {t["text"]}: {"; ".join(t["subtasks"])}')
    else:
        print(f'- {t["text"]}')

# Generate formatted command-line arguments.
# If a task has subtasks, join them with a colon and semicolons.
formatted_args = []
for task in tasks:
    main_text = task["text"]
    if task["subtasks"]:
        subtasks_text = "; ".join(task["subtasks"])
        combined = f"{main_text}: {subtasks_text}"
    else:
        combined = main_text

    # Optionally, ignore tasks that are too short
    if len(combined) >= 3:
        formatted_args.append(f'"{combined}"')

# Ask the user which target command to use.
target = input("\nWhich command do you want to run? (colab, kyros, class, noclass): ").strip().lower()
if target not in ["colab", "kyros", "class", "noclass"]:
    print("Invalid selection. Defaulting to 'noclass'.")
    target = "noclass"

# Build the command string with proper escaping for each argument.
command = f'./{target}.sh \\\n    ' + ' \\\n    '.join(formatted_args)
print("\nGenerated Command:\n")
print(command)

# Confirm before running
run_choice = input("\nRun the above command? (y/n): ").strip().lower()
if run_choice == "y":
    print("🚀 Running command...")
    subprocess.call(command, shell=True)
else:
    print("Command not executed.")