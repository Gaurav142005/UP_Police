import requests
import os
from dotenv import load_dotenv
import subprocess
load_dotenv()

def convert_to_html(content):
    # Save content to a markdown file
    with open('Response.md', 'w') as file:
        file.write(content)

    try:
        # Execute the command
        result = subprocess.run(
            ['grip', 'Response.md', '--export', 'Response.html'],  # Command and arguments as a list
            check=True,                                   # Raise an exception if the command fails
            capture_output=True,                          # Capture the command's output
            text=True                                     # Ensure output is in text format, not bytes
        )
        print("Command executed successfully!")
        print(result.stdout)  # Print any output
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e.stderr}")
    except FileNotFoundError:
        print("The 'grip' command was not found. Ensure it is installed and available in your PATH.")