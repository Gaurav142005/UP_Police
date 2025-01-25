from bs4 import BeautifulSoup
import requests
from tqdm import tqdm
import os

t = requests.get("https://uppolice.gov.in/pages/en/topmenu/police-units/dg-police-hqrs/en-dgp-up-circulars")

soup = BeautifulSoup(t.text, 'html.parser')


class Circulars:
    def __init__(self):
        pass
    def download(self,years):
        ''' a list of years to download the circulars for'''
        for year in years:
            pdfs = []
            for link in soup.find_all('a'):
                if link.get('href')[-3:] == 'pdf' and link.get('href')[:4] == 'site':
                    if str(year) in link.get('href'):
                        pdfs.append("https://uppolice.gov.in/"+link.get('href'))
            for p in tqdm(pdfs, desc='Downloading PDFs of year '+str(year)):
                response = requests.get(p)
                filename = p.split('/')[-1]
                folder_path = f"downloads/pdfs/{year}"
                os.makedirs(folder_path, exist_ok=True)
                file_path = f"{folder_path}/{filename}"
                with open(file_path, 'wb') as pdf_file:
                  pdf_file.write(response.content)
        print('All PDFs downloaded successfully!')


