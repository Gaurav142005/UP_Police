import os
import subprocess
from Scraper import Circulars
from pdf_to_jpg import PDFtoJPG


class data_fetch:
    def __init__(self,years):
        """"years: List of years to download circulars for"""
        self.years = years

    def fetch(self,already_indexed):
        print(self.years)
        circ = Circulars()
        circ.download(self.years)
        
        pdf_to_image = PDFtoJPG()
        pdf_to_image.convert(self.years,already_indexed)

        subprocess.run([
            "./venv_openai/bin/python", "run_jpg_to_text.py", *self.years
        ], check=True)

        subprocess.run([
            "./venv_translate/bin/python", "run_translate.py"
        ], check=True)


        
