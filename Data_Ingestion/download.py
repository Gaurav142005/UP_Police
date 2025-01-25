import os
import subprocess
from Scraper import Circulars


def get_years():
    years = input("Enter years separated by commas: ").split(',')
    return [int(year.strip()) for year in years if year.strip().isdigit()]

def run_scripts(years, script_names):
    circ = Circulars()
    circ.download(years)

if __name__ == "__main__":
    years = get_years()
    print(years)
    circ = Circulars()
    circ.download(years)

    script_names = ["pdf_to_jpg.py", 'jpg_to_text.py', "translate.py"]

    for script in script_names:
        try:
            print(f"Running {script}")
            subprocess.run(["python", script], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running {script}")
            break