from urllib.parse import unquote
import re
import os
import json
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# fetch once at module level
t = requests.get("https://uppolice.gov.in/pages/en/topmenu/police-units/dg-police-hqrs/en-dgp-up-circulars")
soup = BeautifulSoup(t.text, 'html.parser')

class Circulars:
    def __init__(self):
        pass

    def _sanitize_filename(self, raw_name: str) -> str:
        """
        1) URLâ€‘decode (â€œ%20â€ â†’ â€œ â€, etc.)
        2) remove spaces
        3) keep only Unicode word characters (letters from any language, digits, underscore),
           plus dot and hyphen.
        """
        # 1) Decode percentâ€‘encodings
        name = unquote(raw_name)

        # 2) Remove spaces
        name = name.replace(' ', '')

        # 3) Strip anything that's not letter/number/underscore/dot/hyphen
        name = re.sub(r'[^\w\.-]', '', name)

        return name

    def download(self, years):        
        all_pdfs = {}
        for year in years:
            pdfs = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.lower().startswith('site') and href.lower().endswith('.pdf'):
                    if str(year) in href:
                        pdf_url = "https://uppolice.gov.in/" + href.replace(' ', '%20')
                        pdfs.append(pdf_url)

            already_in_folder = os.listdir(os.path.join('downloads', 'pdfs', year)) if os.path.exists(os.path.join('downloads', 'pdfs', year)) else []


            for pdf_url in tqdm(pdfs, desc=f'Downloading PDFs of year {year}'):
                raw_name = pdf_url.rsplit('/', 1)[-1]
                filename = self._sanitize_filename(raw_name)
                # Check if the file already exists in the folder
                if filename in already_in_folder:
                    all_pdfs[filename] = pdf_url
                    print(f"Skipping {filename}, already exists.")
                    continue

                all_pdfs[filename] = pdf_url

                folder_path = os.path.join('downloads', 'pdfs', str(year))
                os.makedirs(folder_path, exist_ok=True)
                file_path = os.path.join(folder_path, filename)

                resp = requests.get(pdf_url)
                with open(file_path, 'wb') as f:
                    f.write(resp.content)

        # merge with existing JSON (if any)
        json_file_path = os.path.join('downloads', 'pdf_links.json')
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r', encoding='utf-8') as jf:
                existing = json.load(jf)
            existing.update(all_pdfs)
            all_pdfs = existing

        # save JSON
        with open(json_file_path, 'w', encoding='utf-8') as jf:
            json.dump(all_pdfs, jf, indent=4, ensure_ascii=False)

        print('All PDFs downloaded successfully and links saved to JSON!')
