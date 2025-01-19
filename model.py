import os
import re
import json
from dotenv import load_dotenv
from typing import Annotated, Literal, Sequence, TypedDict
from langchain_community.document_loaders import TextLoader
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langgraph.graph.message import add_messages
from langgraph.prebuilt import tools_condition
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_voyageai import VoyageAIEmbeddings

load_dotenv()

pinecone_api_key = os.environ.get("PINECONE_API_KEY")
pc = Pinecone(api_key=pinecone_api_key)
index_name = "bcs-up-police"
index = pc.Index(index_name)
embeddings = VoyageAIEmbeddings(
    voyage_api_key=os.environ.get('VOYAGE_API_KEY'), model="voyage-3-large"
)
docsearch = PineconeVectorStore(index=index, embedding=embeddings)

with open('drive_link_dictionary.json') as f:
    drive_link_dictionary = json.load(f)

class Chatbot:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
        )
        self.tools = [self.retriever_tool]
        self.workflow = self.create_workflow()


    @tool
    def retriever_tool(query: str) -> str:
        """Search and return information about the user query from the circulars by UP Police."""
        d = docsearch.similarity_search(query, k=10)
        context = ""
        for i in d:
            i.metadata['source'] = i.metadata['source'].split('/')[-1]
            for key, value in drive_link_dictionary.items():
                if i.metadata['source'][:-4] == key[:-4]:
                    i.metadata['source'] = value
                    break
            context += f"{i.metadata}" + "\n" + i.page_content + "\n\n"
        return context

    def create_workflow(self):
        class AgentState(TypedDict):
            messages: Annotated[Sequence[BaseMessage], add_messages]

        def grade_documents(state) -> Literal["generate", "rewrite"]:
            class Grade(BaseModel):
                binary_score: str = Field(description="Relevance score 'yes' or 'no'")

            model = self.llm
            llm_with_tool = model.with_structured_output(Grade)
            prompt = PromptTemplate(
                template="""You are a grader assessing relevance of a retrieved document to a user question. \n 
                Here is the retrieved document: \n\n {context} \n\n
                Here is the user question: {question} \n
                If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n
                Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question.""",
                input_variables=["context", "question"],
            )
            chain = prompt | llm_with_tool
            messages = state["messages"]
            last_message = messages[-1]
            question = messages[0].content
            docs = last_message.content
            scored_result = chain.invoke({"question": question, "context": docs})
            score = scored_result.binary_score
            return "generate" if score == "yes" else "rewrite"

        def agent(state):
            messages = state["messages"]
            model = self.llm.bind_tools(self.tools)
            response = model.invoke(messages)
            return {"messages": [response]}

        def rewrite(state):
            messages = state["messages"]
            question = messages[0].content
            msg = [
                HumanMessage(
                    content=f""" \n 
                    Look at the input and try to reason about the underlying semantic intent / meaning. \n 
                    Here is the initial question:
                    \n ------- \n
                    {question} 
                    \n ------- \n
                    Formulate an improved question and output the formulated question only: """,
                )
            ]
            model = self.llm
            response = model.invoke(msg)
            return {"messages": [response]}

        def generate(state):
            messages = state["messages"]
            question = messages[0].content
            last_message = messages[-1]
            docs = last_message.content
            prompt = ChatPromptTemplate([
                ("system", '''You are an assistant for question-answering tasks related to the circulars released by UP Police.
                Use the following pieces of retrieved circulars to answer the question. 
                If you don't know the answer, just say that you don't know. 
                After answering the question, provide the source of the information mentioned before each retrieved context in the format:
                    Source 1: 
                    Source 2:
                    Source 3:
                    ...
                    Source n:
                Only mention the sources that you have actually used to answer.
                Question: {question} 
                Context: {context}  
                Answer:''')
            ])
            model = self.llm
            rag_chain = prompt | model | StrOutputParser()
            response = rag_chain.invoke({"context": docs, "question": question})
            return {"messages": [response]}

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", agent)
        retrieve = ToolNode([self.retriever_tool])
        workflow.add_node("retrieve", retrieve)
        workflow.add_node("rewrite", rewrite)
        workflow.add_node("generate", generate)
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", tools_condition, {"tools": "retrieve", END: END})
        workflow.add_conditional_edges("retrieve", grade_documents)
        workflow.add_edge("generate", END)
        workflow.add_edge("rewrite", "agent")
        return workflow.compile()

    def chatbot(self, query: str) -> str:
        def make_serializable(obj):
            if isinstance(obj, (AIMessage, HumanMessage)):
                return obj.content
            elif isinstance(obj, dict):
                return {key: make_serializable(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(item) for item in obj]
            elif hasattr(obj, '_dict_'):  # Handle custom objects like ToolMessage
                return {key: make_serializable(value) for key, value in obj._dict_.items()}
            return str(obj)  # Fallback for other non-serializable objects

        def clean_text_and_extract_links(text: str) -> (str, list):
            """Cleans text, removes placeholders like 'Source 1' and extracts unique drive links."""
            # Extract drive links
            drive_links = re.findall(r"https://drive\.google\.com/file/d/[a-zA-Z0-9_-]+/view", text)
            unique_links = list(set(drive_links))  # Remove duplicates

            # Remove placeholders like 'Source 1:', 'Source 2:' etc., and drive links from text
            cleaned_text = re.sub(r"Source \d+:.*\n?", "", text)
            
            # Remove links from text body
            cleaned_text = re.sub(r"https://drive\.google\.com/file/d/[a-zA-Z0-9_-]+/view", "", cleaned_text)
            
            # Replace multiple newlines with a single newline
            cleaned_text = re.sub(r'\n+', '\n', cleaned_text)
            
            # Strip leading and trailing whitespace
            cleaned_text = cleaned_text.strip()

            return cleaned_text, unique_links

        inputs = {"messages": [("user", query)]}
        results = {}
        for output in self.workflow.stream(inputs):
            for key, value in output.items():
                results[key] = value

        serializable_results = make_serializable(results)
        # Convert to JSON object
        parsed_json = json.loads(json.dumps(serializable_results, indent=2))

        # Extract the final response from the "generate" node
        final_response = ""
        if "generate" in parsed_json and "messages" in parsed_json["generate"]:
            final_response = parsed_json["generate"]["messages"][0]

        # Clean the text and extract unique drive links
        final_response, unique_links = clean_text_and_extract_links(final_response)

        # Append unique links at the end of the response as relevant sources
        if unique_links:
            final_response += "\n\nRelevant Sources:\n" + "\n".join(unique_links)

        return final_response
    
if __name__ == "__main__":
    bot = Chatbot()
    query = "What is the procedure to file an FIR?"
    response = bot.chatbot(query)
    print(response)