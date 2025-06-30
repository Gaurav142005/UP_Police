
import json
from translate import Translate

input_path = './already_indexed.json'
already_indexed=json.load(open(input_path, 'r', encoding='utf-8'))

t = Translate()
t.translate(already_indexed)
