import re
import subprocess
def clean_task_list(messy_input):
    print("messy input:", messy_input)
    """Extracts issue titles from messy text and formats them for kyros.sh"""
    
    # split messy input by ne
    issues = messy_input.split("\n")
    # issues = re.findall(r'Issue\s+(.*?)\n', messy_input)  # Extract issue titles
    print("issues 1:", issues)
    issues = [issue.strip() for issue in issues if issue.strip()]  # Remove extra spaces
    print("issues 2:", issues)

    # Generate the formatted command
    command = './kyros.sh \\\n    ' + ' \\\n    '.join(f'"{issue}"' for issue in issues)
    return command

# Read messy input from the file once
with open("messy_input.txt", "r") as file:
    messy_text = file.read()
    print("DEBUG: Content of messy_input.txt:")
    print(messy_text)

# Generate and print the cleaned command
cleaned_command = clean_task_list(messy_text)
print("\nGenerated Command:\n")
print(cleaned_command)

# Ask user if they want to run the command
run_choice = input("\nRun tasks.py with these tasks? (y/n): ")
if run_choice.lower() == "y":
    print("🚀 Running command...")
    # Run the cleaned command using subprocess
    subprocess.call(cleaned_command, shell=True)
else:
    print("Command not executed.")