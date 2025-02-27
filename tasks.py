import re

def clean_task_list(messy_input):
    """Extracts issue titles from messy text and formats them for kyros.sh"""
    issues = re.findall(r'Issue\s+(.*?)\n', messy_input)  # Extract issue titles
    issues = [issue.strip() for issue in issues if issue.strip()]  # Remove extra spaces

    # Generate the formatted command
    command = './kyros.sh \\\n    ' + ' \\\n    '.join(f'"{issue}"' for issue in issues)
    return command

# Read messy input from a file (or paste directly into this variable)
with open("messy_input.txt", "r") as file:
    messy_text = file.read()

# Generate and print the cleaned command
cleaned_command = clean_task_list(messy_text)
print("\nGenerated Command:\n")
print(cleaned_command)