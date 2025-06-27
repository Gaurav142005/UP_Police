from bs4 import BeautifulSoup
import requests
from tqdm import tqdm
import os
import json

t = requests.get("https://uppolice.gov.in/pages/en/topmenu/police-units/dg-police-hqrs/en-dgp-up-circulars")

soup = BeautifulSoup(t.text, 'html.parser')


class Circulars:
    def __init__(self):
        pass

    def download(self, years):
        ''' a list of years to download the circulars for'''
        all_pdfs = {}
        for year in years:
            pdfs = []
            for link in soup.find_all('a'):
                if link.get('href')[-3:] == 'pdf' and link.get('href')[:4] == 'site':
                    if str(year) in link.get('href'):
                        pdf_url = "https://uppolice.gov.in/" + link.get('href').replace(' ', '%20')
                        pdfs.append(pdf_url)
                        filename = pdf_url.split('/')[-1]
                        all_pdfs[filename] = pdf_url
            for p in tqdm(pdfs, desc='Downloading PDFs of year ' + str(year)):
                response = requests.get(p)
                filename = p.split('/')[-1]
                folder_path = f"downloads/pdfs/{year}"
                os.makedirs(folder_path, exist_ok=True)
                file_path = f"{folder_path}/{filename}"
                with open(file_path, 'wb') as pdf_file:
                    pdf_file.write(response.content)
        # Save the dictionary as a JSON file
        with open("downloads/pdf_links.json", "w", encoding='utf-8') as json_file:
            json.dump(all_pdfs, json_file, indent=4, ensure_ascii=False)

        print('All PDFs downloaded successfully and links saved to JSON!')


