import easyocr
import os 
import tqdm
import numpy as np
from skimage import io
from skimage.color import rgb2gray
from skimage.transform import rotate
from deskew import determine_skew
import re
from openai import OpenAI
from dotenv import load_dotenv
import time

load_dotenv()

reader = easyocr.Reader(['en','hi'])

cwd = os.getcwd()
jpg_path = cwd + '/downloads/jpgs'
txt_path = cwd + '/downloads/txts'

years = os.listdir(jpg_path)


class JPGtoTEXT:
    def __init__(self):
        pass
    def preprocess(self):
        for year in years:
            circulars = os.listdir(jpg_path + '/' + year)
            for circular in tqdm.tqdm(circulars, desc=f"Preprocessing circulars of {year}"):
                for page in os.listdir(jpg_path + '/' + year + '/' + circular):
                    image = io.imread(jpg_path + '/' + year + '/' + circular + '/' + page)
                    grayscale = rgb2gray(image)
                    angle = determine_skew(grayscale)
                    rotated = rotate(image, angle, resize=True) * 255
                    io.imsave(jpg_path + '/' + year + '/' + circular + '/' + page, rotated.astype(np.uint8))
        
        print("Preprocessing done!")


    def remove_unmatched_brackets(self,input_string):
        stack = []
        result = []
        brackets = {'(': ')', '[': ']', '{': '}'}
        open_brackets = brackets.keys()
        close_brackets = brackets.values()
        
        for char in input_string:
            if char in open_brackets:
                stack.append(char)
                result.append(char)
            elif char in close_brackets:
                if stack and brackets[stack[-1]] == char:
                    stack.pop()
                    result.append(char)
                else:
                    # Do not append unmatched closing bracket
                    continue
            else:
                result.append(char)
        print("Brackets removed")
        
        # Remove unmatched opening brackets
        unmatched_open_brackets = set(stack)
        final_result = []
        for char in result:
            if char in open_brackets and char in unmatched_open_brackets:
                unmatched_open_brackets.remove(char)
            else:
                final_result.append(char)
        
        return ''.join(final_result)

    def remove_unmatched_hindi_matras(self,input_string):
        # Define the range for Hindi matras (vowel signs)
        hindi_matras = r'\u093E-\u094D\u0951-\u0957\u0962-\u0963'
        hindi_letters = r'\u0900-\u0914\u0915-\u0939\u0958-\u0961\u0966-\u096F'
        
        # Regular expression to find matras not preceded or followed by a Hindi letter
        pattern = rf'(?<![{hindi_letters}])[{hindi_matras}](?![{hindi_letters}])'
        
        # Remove such matras
        cleaned_string = re.sub(pattern, '', input_string)
        
        return cleaned_string

    def convert_hindi_to_english_numerals(self,input_string):
        hindi_to_english = {
            '०': '0', '१': '1', '२': '2', '३': '3', '४': '4', 
            '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
        }
        return ''.join(hindi_to_english.get(char, char) for char in input_string)

    def replace_specific_sequences(self,input_string):
        def replace_match(match):
            str_match = match.group(1)
            # Check if str_match contains 'विषय', is '०', has no spaces, or no numbers
            if 'विषय' in str_match:
                return match.group(0)  # Keep the whole match if it contains "विषय"
            if str_match == '0' or (not any(char.isdigit() for char in str_match) and ' ' not in str_match):
                return '\n'
            return match.group(0)  # Return the whole match if it doesn't meet the conditions
        
        # Regular expression to find sequences of the type \nstr\n
        pattern = re.compile(r'\n([^\n]+)\n')
        cleaned_string = pattern.sub(replace_match, input_string)
        
        return cleaned_string

    def remove_characters_after_bhavdiya(self,input_string):
        # Regular expression to find 'भवदीय' followed by any characters until the next '('
        pattern = re.compile(r'(भवदीय[^(]*\()')
        
        # Replace the matched pattern with 'भवदीय('
        cleaned_string = pattern.sub('भवदीय (', input_string)
        
        return cleaned_string
    
    def remove_special_characters(self,input_string):
        # Define the regular expression pattern to match unwanted characters
        pattern = r"[^a-zA-Z0-9\u0900-\u097F\[\]\(\)\{\}\/ ,.!|:\n;-]"
        # Remove unwanted characters
        cleaned_string = re.sub(pattern, '', input_string)
        # Remove unmatched brackets
        cleaned_string = self.remove_unmatched_brackets(cleaned_string)
        # Remove Hindi matras without adjoining Hindi letters
        cleaned_string = self.remove_unmatched_hindi_matras(cleaned_string)
        # Convert Hindi numerals to English numerals
        cleaned_string = self.convert_hindi_to_english_numerals(cleaned_string)
        # Replace sequences \nstr\n based on the given conditions
        cleaned_string = self.replace_specific_sequences(cleaned_string)
        # Remove characters after 'भवदीय' until '('
        cleaned_string = self.remove_characters_after_bhavdiya(cleaned_string)
        return cleaned_string


    def correct_text(self, text):
        api_key = os.environ.get("GEMINI_API_KEY")
        endpoint = "https://generativelanguage.googleapis.com/v1beta/openai/"
        model_name = "gemini-2.5-flash"
        
        client = OpenAI(base_url=endpoint,api_key=api_key)

        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": """You are a text corrector,
        I am going to provide you a text in Hindi and English. Clean up the text, by removing all random symbols, characters, etc which are clearly printing mistakes and do not make any sense.

        Finally, ONLY output the corrected text.

        DO NOT CHANGE anything else in the text.
        """,
                },
                {
                    "role": "user",
                    "content": f'''{text}''',
                }
            ],
            model=model_name,
        )

        return response.choices[0].message.content

    def convert(self):
        # self.preprocess()
        for year in years:
            circulars = os.listdir(jpg_path + '/' + year)
            for circular in tqdm.tqdm(circulars, desc=f"Extracting text from circulars of {year}"):
                
                total_text=""
                iteration_count = 0
                for page in os.listdir(jpg_path + '/' + year + '/' + circular):

                    image_path = (jpg_path + '/' + year + '/' + circular + '/' + page)
                    result = reader.readtext(image_path)
                    formatted_lines = []
                    for (bbox, text, prob) in result:
                        # Get bounding box coordinates
                        top_left, top_right, bottom_right, bottom_left = bbox
                        x_min = int(min(top_left[0], bottom_left[0]))
                        x_max = int(max(top_right[0], bottom_right[0]))
                        y_min = int(min(top_left[1], top_right[1]))
                        y_max = int(max(bottom_left[1], bottom_right[1]))
                        
                        # Add the text to the corresponding position in the formatted lines
                        formatted_lines.append((y_min, x_min, text))
                    
                    # Sort the lines based on y_min to maintain top-to-bottom order
                    formatted_lines.sort()
                    
                    # Group text by lines, inserting newlines for paragraph changes
                    output_lines = []
                    current_line = []
                    current_y = formatted_lines[0][0]
                    
                    # Threshold to detect paragraph changes, this might need adjustment based on document
                    paragraph_threshold = 30
                    
                    for y_min, x_min, text in formatted_lines:
                        if abs(y_min - current_y) <= paragraph_threshold:
                            current_line.append((x_min, text))
                        else:
                            # Sort the current line by x_min
                            current_line.sort()
                            line_text = ' '.join([txt for _, txt in current_line])
                            output_lines.append(line_text)
                            
                            # Insert a newline to indicate a paragraph change
                            output_lines.append("\n")
                            
                            current_line = [(x_min, text)]
                            current_y = y_min
                    
                    # Add the last line
                    if current_line:
                        current_line.sort()
                        line_text = ' '.join([txt for _, txt in current_line])
                        output_lines.append(line_text)
                    
                    # Remove unnecessary newlines
                    formatted_text = '\n'.join(line for line in output_lines if line.strip() != "\n") 
                    # Implement rate limiting to call correct_text exactly 8 times per minute
                    if iteration_count % 8 == 0 and iteration_count != 0:
                        time.sleep(60)  # Sleep for 60 seconds after every 8 calls
                    
                    formatted_text = self.correct_text(self.remove_special_characters(formatted_text))
                    iteration_count += 1
                    total_text += formatted_text
                    
                
                os.makedirs(txt_path + '/' + year , exist_ok=True)
                with open(txt_path + '/' + year + '/' + circular + '.txt', "w", encoding="utf-8") as f:
                    f.write(total_text)



if __name__ == '__main__':
    p = JPGtoTEXT()
    p.convert()
