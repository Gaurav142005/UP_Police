### UTTAR PRADESH POLICE AGENTIC RAG SYSTEM
---
This directory contains the code for our UP Police RAG application, utilizing the React framework alongside Flask for rendering and parsing. Further, it also contains our backend and the model which we have built.
How to run the program:

```
npm i
npm run dev
```

Then run the app.py file using
```
python backend/app.py
```

Following is the tree structure of the UI:
```
├── Data_Ingestion
├── backend
│   ├── app.py
│   ├── model.py
│   ├── utility.py

├── src
│   ├── assets
│   ├── components
        ├── main
        ├── sidebar
        ├── graphbar
        ├── file
        ├── dropdown
│   ├── context
```

1. **``assets``**:  This folder contains the all the images used throughout the website.
2. **``components``**: 
    - This folder contains all the individual components of our web app.
    - Main - The main component of our website where the chat interface is present. It contains a search box to interact with the bot as well as upload files to our RAG, from the computer and to Google Drive.  It also contains options for the user to select the language of the response they wish to get. Currently, it supports English and Hindi but can be expanded to 22 regional languages.
    - Sidebar - The sidebar component stores the previous chats with the user and even allows the user to create new chats. It also contains the file system viewer to have a look at the files uploaded till now.
    - File - Helper component to view the file history of the uploaded files.
    - Dropdown - Helper component to make a dropdown and allow users to choose their desired language to get the response.

3. **``Context``**:
    - This serves as a centralized store for managing shared state across components, providing a single source of truth for variables and state data used throughout the application. It enhances code maintainability, simplifying state updates, and promoting scalability by allowing easy integration of new features. It is particularly useful for managing global data.

3. **``app.py``**:
    - This serves as our main flask backend. We communicate with the frontend through this, and send the responses to the queries as well from here. Further it allows us to upload files to Google drive, and store download pdfs of the responses. 

4. **``model.py``**:
    - This is the model which we have made. It is an Agentic framework made using Langgraph containing agents like rewrite, retrieve and generate.

5. **``utility.py``**:
    - Contains some utility functions for our backend file. 

#### Downloading Circulars Pipeline

To download the circulars from the UP Police website, and convert them to translated text files, run the following command and specify the year for which the files will be downloaded.
```
cd Data_Ingestion
python download.py
```

This script first scrapes and downloads all circulars of that year from `Scraper.py`, then converts the pdfs to jpg in `pdf_to_jpg.py`, then goes to `jpg_to_text.py` and finally translates the text through `translate.py` to get the required text files for our RAG.
