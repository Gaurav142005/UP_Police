import json
from jpg_to_text import JPGtoTEXT
import sys


input_path = './already_indexed.json'
already_indexed=json.load(open(input_path, 'r', encoding='utf-8'))
years = sys.argv[1:]

t = JPGtoTEXT(years)
t.convert(already_indexed)
