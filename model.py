import os
import re
import json
from dotenv import load_dotenv
from typing import Annotated, Literal, Sequence, TypedDict
from langchain_community.document_loaders import TextLoader
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langgraph.graph.message import add_messages
from langgraph.prebuilt import tools_condition
from langgraph.graph import END, StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_voyageai import VoyageAIEmbeddings
import pprint

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
            model="llama3-70b-8192", #  llama3-70b-8192 or llama-3.3-70b-versatile
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
        )
        self.workflow = self.create_workflow()

    def create_workflow(self):
        class AgentState(TypedDict):
            messages: Annotated[Sequence[BaseMessage], add_messages]
        def retrieve(state: dict) -> dict:
            """Retrieves relevant documents based on the rewritten query."""
            # print("---CALL RETRIEVE---")
            messages = state["messages"]
            query = messages[-1].content  # Get the rewritten query from the last message

            # Perform similarity search
            d = docsearch.similarity_search(query, k=10)
            context = ""
            for i in d:
                i.metadata['source'] = i.metadata['source'].split('/')[-1]
                for key, value in drive_link_dictionary.items():
                    if i.metadata['source'][:-4] == key[:-4]:
                        i.metadata['source'] = value
                        break
                context += f"{i.metadata}" + "\n" + i.page_content + "\n\n"

            # Append the retrieved context to the state
            return {"messages": messages + [HumanMessage(content=context)]}

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
                If the question is a general question that can be answered without the document, grade it as irrelevant. \n
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
            return "generate" if score == "yes" else "generic_agent"
        
        def generic_agent(state):
            """Answers to the conversational questions based on general knowledge that doesnt require retrieval.
            
            Args:
                state (messages): The current state
            
            Returns:
                dict: The updated state with the agent response appended to messages
            """
            print("---CALL GENERIC AGENT---")
            messages = state["messages"]
            question = messages[1].content
            prompt = ChatPromptTemplate([
                ("system", '''You are an helpful assistant for generic questions.'''),
                ("human", '''{question}''')
            ])
            model = self.llm
            generic_chain = prompt | model | StrOutputParser()

            # Run
            response = generic_chain.invoke({"question": question})
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
        workflow.add_node("rewrite", rewrite)  # Rewriting the question
        workflow.add_node("retrieve", retrieve)  # Retrieval step
        workflow.add_node("generate", generate)  # Generating a response after we know the documents are relevant
        workflow.add_node("generic_agent", generic_agent)  # Generic agent

        # Define edges for transitions
        workflow.add_edge(START, "rewrite")  # Start to rewrite
        workflow.add_edge("rewrite", "retrieve")  # Rewrite to retrieve
        workflow.add_conditional_edges(
            "retrieve",
            grade_documents,
            {
                "generate": "generate",  # If relevant, generate response
                "generic_agent": "generic_agent",  # If not relevant, fallback to generic agent
            },
        )
        workflow.add_edge("generate", END)  # Generate ends workflow
        workflow.add_edge("generic_agent", END)  # Generic agent ends workflow
        graph = workflow.compile()
        return graph


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

        def clean_text_and_extract_links(text: str) -> (str, list): # type: ignore
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

        inputs = {"messages": [HumanMessage(content=query)]}
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
    query = "what are jurisdriction of UP Police"
    response = bot.chatbot(query)
    print(response)