import os
from googletrans import Translator


cwd = os.getcwd()
txt_path = cwd + '/downloads/txts'
translated_data = cwd + '/downloads/translated_data'

years = os.listdir(txt_path)

class Translate:
    def __init__(self):
        self.translator = Translator()
    
    def chunk_text(self, text, chunk_size=5000):
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        return chunks

    def translate_chunk(self, chunk):
        # Synchronously translate chunk from Hindi to English
        translation = self.translator.translate(chunk, src='hi', dest='en')
        return translation.text

    def translate(self,already_indexed=None):
        if already_indexed is not None:
            already_indexed_copy = [j.replace('.pdf', '.txt') for j in already_indexed]
        else:
            already_indexed_copy = None

        for year in years:
            txts = os.listdir(txt_path + '/' + year)
            for txt in txts:
                if already_indexed_copy and txt in already_indexed_copy:
                    continue
                with open(txt_path + '/' + year + '/' + txt, 'r', encoding='utf-8') as file:
                    data = file.read()
                
                # Split the data into chunks and translate each one synchronously
                hindi_chunks = self.chunk_text(data, chunk_size=5000)
                translated_chunks = [self.translate_chunk(chunk) for chunk in hindi_chunks]

                # Save the translated text into a new file
                os.makedirs(translated_data + '/' + year, exist_ok=True)
                with open(translated_data + '/' + year + '/' + txt, 'w', encoding='utf-8') as file:
                    file.write('\n\n'.join(translated_chunks))

if __name__ == '__main__':
    t = Translate()
    t.translate()