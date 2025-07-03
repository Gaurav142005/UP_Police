import os
import time
from googletrans import Translator

cwd = os.getcwd()
txt_path = cwd + '/downloads/txts'
translated_data = cwd + '/downloads/translated_data'

years = os.listdir(txt_path)

class Translate:
    def __init__(self):
        self.translator = Translator()

    def chunk_text(self, text, chunk_size=5000):
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    def safe_translate_chunk(self, chunk, retries=3, delay=2):
        for attempt in range(retries):
            try:
                return self.translator.translate(chunk, src='hi', dest='en').text
            except Exception as e:
                print(f"[Retry {attempt+1}] Error translating chunk: {e}")
                time.sleep(delay)
        return "[Translation Failed]"

    def translate(self, already_indexed=None):
        already_indexed_copy = [j.replace('.pdf', '.txt') for j in already_indexed] if already_indexed else None

        for year in years:
            txts = os.listdir(os.path.join(txt_path, year))
            for txt in txts:
                if already_indexed_copy and txt in already_indexed_copy:
                    continue

                txt_file_path = os.path.join(txt_path, year, txt)
                with open(txt_file_path, 'r', encoding='utf-8') as file:
                    data = file.read()

                hindi_chunks = self.chunk_text(data, chunk_size=5000)
                translated_chunks = [self.safe_translate_chunk(chunk) for chunk in hindi_chunks]

                save_path = os.path.join(translated_data, year)
                os.makedirs(save_path, exist_ok=True)
                with open(os.path.join(save_path, txt), 'w', encoding='utf-8') as file:
                    file.write('\n\n'.join(translated_chunks))

if __name__ == '__main__':
    t = Translate()
    t.translate()
