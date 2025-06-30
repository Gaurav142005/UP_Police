import os 
from pdf2image import convert_from_path
import tqdm


cwd = os.getcwd()
pdf_path = cwd + '/downloads/pdfs'
jpg_path = cwd + '/downloads/jpgs'

class PDFtoJPG:
    def __init__(self):
        pass
    def convert(self,years,already_indexed=None):
        for year in years:
            pdfs = os.listdir(pdf_path + '/' + year)
            # already_exists = os.listdir(jpg_path + '/' + year) if os.path.exists(jpg_path + '/' + year) else []
            for pdf in tqdm.tqdm(pdfs, desc=f"Converting pdfs of {year} to jpgs"):
                if os.path.exists(jpg_path + '/' + year + '/' + pdf[:-4]):
                    print(f"Skipping {pdf}, already exists.")
                    continue
                if already_indexed is None:
                    already_indexed = []
                if pdf in already_indexed:
                    continue
                images = convert_from_path(pdf_path + '/' + year + '/' + pdf)
                os.makedirs(jpg_path + '/' + year + '/' + pdf[:-4], exist_ok=True)
                for i, image in enumerate(images):

                    image.save(jpg_path + '/' + year + '/' + pdf[:-4] + '/' + pdf[:-4] + f'_{i}.jpg', 'JPEG')

if __name__ == '__main__':
    p = PDFtoJPG()
    p.convert()
