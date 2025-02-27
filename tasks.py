import re
import subprocess

def clean_task_list(messy_input):
    """Extracts issue titles from messy text and formats them for the chosen target script."""
    # Split messy input by newline and filter out empty lines
    issues = messy_input.split("\n")
    issues = [issue.strip() for issue in issues if issue.strip()]
    return issues

# Read messy input from the file once
with open("messy_input.txt", "r") as file:
    messy_text = file.read()
    print("DEBUG: Content of messy_input.txt:")
    print(messy_text)

# Extract the issues from the messy input
issues = clean_task_list(messy_text)

# For debugging, show all extracted lines
print("\nExtracted Lines:")
for line in issues:
    print(f'- {line}')

# Ask the user which target they want to run
target = input("\nWhich command do you want to run? (colab, kyros, class): ").strip().lower()
if target not in ["colab", "kyros", "class"]:
    print("Invalid selection. Defaulting to 'kyros'.")
    target = "kyros"

# Generate the command for the chosen target.
# This will call, for example, "./kyros.sh" and pass each issue as an argument.
# Here, we assume every non-empty line in messy_input.txt is a task.
formatted_args = ' \\\n    '.join(f'"{line}"' for line in issues if len(line) >= 10)
command = f'./{target}.sh \\\n    {formatted_args}'
print("\nGenerated Command:\n")
print(command)

# Ask user for confirmation
run_choice = input("\nRun the above command? (y/n): ").strip().lower()
if run_choice == "y":
    print("🚀 Running command...")
    subprocess.call(command, shell=True)
else:
    print("Command not executed.")