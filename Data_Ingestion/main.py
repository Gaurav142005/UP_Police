from download import data_fetch
from langchain_voyageai import VoyageAIEmbeddings
import os
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_core.documents import Document
import json
import re
from tqdm import tqdm
import unicodedata
from uuid import uuid4

load_dotenv()
def to_ascii_safe(text):
    # Normalize and remove non-ASCII characters
    normalized = unicodedata.normalize("NFKD", text)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', ascii_str)  # Replace unsafe characters with '_'


class Update_circular_index:
    def __init__(self):
        self.years = self.get_years()
        self.embeddings = VoyageAIEmbeddings(
                            voyage_api_key=os.environ.get('VOYAGE_API_KEY'), model="voyage-3-large"
                        )
        self.text_splitter = SemanticChunker(self.embeddings,min_chunk_size=512,breakpoint_threshold_amount=95)
        self.recursive_text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1800,  # chunk size (characters)
            chunk_overlap=200,  # chunk overlap (characters)
        )
        self.documents=[]
        self.txt_path = './downloads/translated_data'
        self.links_path = './downloads/pdf_links.json'
        self.pdf_links = json.load(open(self.links_path, 'r', encoding='utf-8'))
        with open('./already_indexed.json','w', encoding='utf-8') as f:
            json.dump(self.pdf_links, f, ensure_ascii=False, indent=4)
        self.already_indexed = list(self.pdf_links.keys())
        pinecone_api_key = os.environ.get("PINECONE_API_KEY")
        pc = Pinecone(api_key=pinecone_api_key)
        index_name = "up-police-circulars"
        self.index = pc.Index(index_name)
        self.data_fetcher = data_fetch(self.years)
        self.MAX_REQUEST_SIZE = 2_000_000 
    
    def get_years(self):
        years = input("Enter years separated by commas: ").split(',')
        return [year.strip() for year in years if year.strip().isdigit()]
    
    def clean_circular_text(self,raw_text: str) -> str:
        # Step 1: Remove redundant newlines within paragraphs
        cleaned = re.sub(r'\n(?=\w)', ' ', raw_text)  # Merge lines that start with a word
        cleaned = re.sub(r'(?<=[a-zA-Z])\s{2,}(?=[a-zA-Z])', ' ', cleaned)  # Fix multiple spaces
        cleaned = re.sub(r'\n{2,}', '\n', cleaned)  # Remove multiple newlines

        # Step 2: Fix linebreaks that interrupt sentences
        cleaned = re.sub(r'(?<!\n)\n(?![\n0-9\-â€¢])', ' ', cleaned)  # Join broken sentences
        cleaned = re.sub(r' +', ' ', cleaned)  # Remove multiple spaces

        # Step 3: Preserve headings, numbered points and sections
        cleaned = re.sub(r'(?<=\n)([0-9]+[\-\.])', r'\n\1', cleaned)  # Ensure points start on a new line
        cleaned = re.sub(r'(Subject:)', r'\n\1', cleaned)
        cleaned = re.sub(r'(Date:)', r'\n\1', cleaned)
        cleaned = re.sub(r'(Dear Sir / Madam,)', r'\n\1', cleaned)

        # Step 4: Remove duplicate | or trailing lines
        cleaned = re.sub(r'[|Â¦]', '', cleaned)
        cleaned = re.sub(r'_{5,}', '', cleaned)  # Horizontal line artifacts
        cleaned = re.sub(r'^\s*$', '', cleaned, flags=re.MULTILINE)  # Remove blank lines

        # Step 5: Fix common OCR artifacts
        cleaned = re.sub(r'\bDrified\b', 'Dated', cleaned)
        cleaned = re.sub(r'\bopproprite\b', 'appropriate', cleaned)
        cleaned = re.sub(r'\bopplicable\b', 'applicable', cleaned)
        cleaned = re.sub(r'\bextramely\b', 'extremely', cleaned)
        cleaned = re.sub(r'\bpladuing\b', 'plaguing', cleaned)
        cleaned = re.sub(r'\bhelp\b', 'held', cleaned)  # "meeting is help" â†’ "held"
        cleaned = re.sub(r'\bblessed\b', 'pleased', cleaned)  # OCR: "blem" or "bless" â†’ "pleased"

        # Step 6: Ensure final clean-up
        cleaned = cleaned.strip()

        return cleaned

    def load_text_documents(self):
        for year in os.listdir(self.txt_path):
            if(year in self.years):
                year_path = os.path.join(self.txt_path, year)
                for file in os.listdir(year_path):
                    if file.endswith('.txt'):
                        file_path = os.path.join(year_path, file)
                        if file[:-4]+'.pdf' not in self.already_indexed:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                content = self.clean_circular_text(content)
                                file_name = file[:-4] + '.pdf'
                                source = self.pdf_links[file_name]
                                self.documents.append(Document(page_content=content, metadata={"source": source, "file_name": file_name}))
        if len(self.documents) == 0:
            print("No new documents found for the specified years.")
            exit(0)
                
    
    def chunking(self):
        chunks = self.text_splitter.split_documents(self.documents)
        return chunks

    def chunk_long_chunks(self):
        long_chunks = []
        for chunk in self.chunks:
            if len(chunk.page_content) > 2500:
                # 1) split really-long chunks
                split_chunks = self.recursive_text_splitter.split_documents([chunk])
                final_chunks = []
                
                i = 0
                while i < len(split_chunks):
                    current = split_chunks[i]
                    curr_name = current.metadata.get("file_name")
                    
                    # 2) small chunk â†’ merge
                    if len(current.page_content) < 200:
                        
                        # case A: merge into previous
                        if final_chunks:
                            prev = final_chunks[-1]
                            prev_name = prev.metadata.get("file_name")
                            
                            if curr_name == prev_name:
                                # merge text
                                prev.page_content += " " + current.page_content
                            else:
                                print(f"[WARNING] Cannot merge chunk #{i} (file: {curr_name!r}) into previous chunk (file: {prev_name!r}); keeping separate.")
                                final_chunks.append(current)
                        
                        # case B: no previous â†’ merge into next
                        elif i + 1 < len(split_chunks):
                            nxt = split_chunks[i + 1]
                            next_name = nxt.metadata.get("file_name")
                            
                            if curr_name == next_name:
                                nxt.page_content = current.page_content + " " + nxt.page_content
                            else:
                                print(f"[WARNING] Cannot merge chunk #{i} (file: {curr_name!r}) into next chunk (file: {next_name!r}); keeping separate.")
                                final_chunks.append(current)
                        
                        # only one chunk in split list
                        else:
                            final_chunks.append(current)
                    
                    else:
                        # normal-sized chunk: keep it
                        final_chunks.append(current)
                    
                    i += 1
                
                long_chunks.extend(final_chunks)
            
            else:
                # chunk is already small enough
                long_chunks.append(chunk)
        
        return long_chunks
    

    # def embed_and_index_chunks(self):
    #     vectors = []
    #     for chunk in tqdm(self.new_chunks, desc="Embedding and Indexing Chunks"):
    #         chunk_embedding = self.embeddings.embed_documents([chunk.page_content])
    #         original_name = chunk.metadata["file_name"]
    #         safe_file_name = to_ascii_safe(original_name)
    #         vector_id = f"{safe_file_name}_{uuid4()}"

    #         vectors.append({
    #             "id": vector_id,
    #             "values": chunk_embedding[0],
    #             "metadata": {
    #                 "source": chunk.metadata["source"],
    #                 "file_name": original_name,
    #                 "text": chunk.page_content
    #             }}
    #         )
    #     self.index.upsert(vectors=vectors)

    def get_vector_size(self,vector):
        return len(json.dumps(vector).encode('utf-8'))

    def batch_upsert(self,index, vectors, max_size):
        batch = []
        batch_size = 0

        for vector in vectors:
            vector_size = self.get_vector_size(vector)
            if batch_size + vector_size > max_size:
                index.upsert(vectors=batch)
                batch = [vector]
                batch_size = vector_size
            else:
                batch.append(vector)
                batch_size += vector_size

        if batch:
            index.upsert(vectors=batch)

    # Modified method
    def embed_and_index_chunks(self):
        vectors = []
        for chunk in tqdm(self.new_chunks, desc="Embedding and Indexing Chunks"):
            chunk_embedding = self.embeddings.embed_documents([chunk.page_content])
            original_name = chunk.metadata["file_name"]
            safe_file_name = to_ascii_safe(original_name)
            vector_id = f"{safe_file_name}_{uuid4()}"

            vector = {
                "id": vector_id,
                "values": chunk_embedding[0],
                "metadata": {
                    "source": chunk.metadata["source"],
                    "file_name": original_name,
                    "text": chunk.page_content
                }
            }
            vectors.append(vector)

        self.batch_upsert(self.index, vectors,self.MAX_REQUEST_SIZE)

    def update(self):
        print("Starting the update process for circular index...")
        
        print("Step 0: Fetching new data...")
        self.data_fetcher.fetch(self.already_indexed)
        self.pdf_links = json.load(open(self.links_path, 'r', encoding='utf-8'))

        print("Step 1: Loading text documents...")
        self.load_text_documents()
        print(f"Loaded {len(self.documents)} documents for the years: {self.years}")
        
        print("Step 2: Chunking documents into smaller semantic chunks...")
        self.chunks = self.chunking()
        print(f"Generated {len(self.chunks)} chunks from the documents.")
        
        print("Step 3: Further splitting long chunks into manageable sizes...")
        self.new_chunks = self.chunk_long_chunks()
        print(f"Processed long chunks. Total chunks after splitting: {len(self.new_chunks)}")
        
        print("Step 4: Embedding and indexing chunks...")
        self.embed_and_index_chunks()
        print("Embedding and indexing completed successfully.")
        
        print("Update process completed.")

if __name__ == "__main__":
    updater = Update_circular_index()
    updater.update()
        