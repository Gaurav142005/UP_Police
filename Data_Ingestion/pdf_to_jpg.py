import os 
from pdf2image import convert_from_path
import tqdm


cwd = os.getcwd()
pdf_path = cwd + '/downloads/pdfs'
jpg_path = cwd + '/downloads/jpgs'

years = os.listdir(pdf_path)
class PDFtoJPG:
    def __init__(self):
        pass
    def convert(self):
        for year in years:
            pdfs = os.listdir(pdf_path + '/' + year)
            for pdf in tqdm.tqdm(pdfs, desc=f"Converting pdfs of {year} to jpgs"):
                images = convert_from_path(pdf_path + '/' + year + '/' + pdf)
                os.makedirs(jpg_path + '/' + year + '/' + pdf[:-4], exist_ok=True)
                for i, image in enumerate(images):

                    image.save(jpg_path + '/' + year + '/' + pdf[:-4] + '/' + pdf[:-4] + f'_{i}.jpg', 'JPEG')

if __name__ == '__main__':
    p = PDFtoJPG()
    p.convert()
