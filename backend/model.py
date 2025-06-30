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
from langchain_google_genai import ChatGoogleGenerativeAI
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
from deep_translator import GoogleTranslator
import pprint

load_dotenv()


def set_google_credentials(filename: str):
    full_path = os.path.join(os.path.dirname(__file__), filename)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = full_path

# Set the Google Application Credentials
set_google_credentials("apikey.json")



pinecone_api_key = os.environ.get("PINECONE_API_KEY")
pc = Pinecone(api_key=pinecone_api_key)
index_name = "bcs-up-police"
index = pc.Index(index_name)
embeddings = VoyageAIEmbeddings(
    voyage_api_key=os.environ.get('VOYAGE_API_KEY'), model="voyage-3-large"
)
docsearch = PineconeVectorStore(index=index, embedding=embeddings)

with open('./drive_link_dictionary.json') as f:
    drive_link_dictionary = json.load(f)

class Conversation():
    def __init__(self):
        self.conv = {"conversation": []}
        self.summary = ""
    def add_message(self, message):
        self.conv["conversation"].append(message)
    def get_summary(self):
        return self.summary

history = Conversation()
class Chatbot:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash-lite-preview-06-17",
                temperature=0,
                max_tokens=None,
                timeout=None,
                max_retries=2,
            )
        self.workflow = self.create_workflow()
        self.relevant_sources = set()  # Initialize set for relevant sources
        self.source_scores = {}  # Store similarity scores for sorting

    def create_workflow(self):
        class AgentState(TypedDict):
            messages: Annotated[Sequence[BaseMessage], add_messages]

        def summarize_conversation(state):
            # First, we summarize the conversation
            summary = history.get_summary()
            messages = state["messages"]
            history.add_message(messages[-1].content) # add the response to the history

            conversation = "User: " + messages[-3].content + "\n" + "Assistant: " + messages[-1].content + "\n"

            # print("summarize node per aa gye with query :" + conversation)
            
            if summary:
                summary_message = (
                    f"This is summary of the conversation to date: {summary}\n\n"
                    "Extend the summary by taking into account the new messages below:"
                )
            else:
                summary_message = "Create a summary of the conversation below:"

            prompt = PromptTemplate(
                template="""Your job is to summarize the conversation so far.\n
                {summary_message}\n\n
                {conversation}""",
                input_variables=["summary_message", "conversation"],
            )
            chain = prompt | self.llm
            response = chain.invoke(
                {"summary_message": summary_message, "conversation": conversation}
            )
            history.summary = response.content
            return {"messages": response.content}        
            
        def retrieve(state: dict) -> dict:
            """Retrieves relevant documents based on the rewritten query."""
            
            messages = state["messages"]
            query = messages[-1].content 
            # print("retrieve node per aa gye with query :" + query)

           
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
        
        def retrieve_again(state: dict) -> dict:
            """Retrieves relevant documents based on the rewritten query with similarity scoring."""
            
            messages = state["messages"]
            query = messages[-1].content 
            # print("retrieve again node per aa gye with query :" + query)

            # Use similarity_search_with_score to get cosine similarity scores
            d = docsearch.similarity_search_with_score(query, k=10)
            context = ""
            
            for doc, score in d:
                # doc.metadata['source'] = doc.metadata['source'].split('/')[-1]
                # for key, value in drive_link_dictionary.items():
                #     if doc.metadata['source'][:-4] == key[:-4]:
                #         doc.metadata['source'] = value
                #         break
                
                # Add sources with similarity >= 0.75 to the set
                if score >= 0.5:
                    self.relevant_sources.add(doc.metadata['source'])
                    self.source_scores[doc.metadata['source']] = score
                    # print(f"\nAdding source: {doc.metadata['source']} with score: {score}\n\n")
                context += f"{doc.metadata}" + "\n" + doc.page_content + "\n\n"

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
            return "rewrite" if score == "yes" else "generic_agent"
        
        def generic_agent(state):
            """Answers to the conversational questions based on general knowledge that doesnt require retrieval.
            
            Args:
                state (messages): The current state
            
            Returns:
                dict: The updated state with the agent response appended to messages
            """
            
            summary = history.get_summary()
            if summary:
                system_message = f"Summary of conversation earlier: {summary}"
            else:
                system_message =  f"Summary of conversation earlier: No conversation till now"
            messages = state["messages"]
            question = messages[0].content
            # print("generic agent per aa gye with query :" + question)
            history.add_message(question) # add the question to the history
            prompt = ChatPromptTemplate([
                ("system", '''You are an helpful assistant made for answering questions related to the circulars released by UP Police.
                You will be provided with the summary of past conversation. Refer to it if needed.'''),
                ("user",''' Summary: {system_message}
                Question: {question}
                Answer:
                '''),
            ])
            model = self.llm
            generic_chain = prompt | model | StrOutputParser()

            # Run
            response = generic_chain.invoke({"question": question, "system_message": system_message})
            return {"messages": [response]}



        def rewrite(state):
            """
            Transform the query to produce a better question.
            """
            
            class QueryRewrite(BaseModel):
                rewritten_query: str = Field(description="The rewritten query or original query if no rewriting needed")
            
            messages = state["messages"]
            question = messages[0].content
            # print("rewrite node per aa gye with query :" + question)

            model = self.llm
            llm_with_tool = model.with_structured_output(QueryRewrite)
            
            prompt = PromptTemplate(
                template="""Look at the input and try to reason about the underlying semantic intent/meaning. 
                The user may ask a question or just try to chat.
                Rewrite the query only if it pertains to topics related to UP Police, law, or orders. 
                Do not rewrite casual or unrelated queries like "Hi, how are you?".
                
                Here is the user query: {question}
                
                If the query is related to UP Police, law, or orders, provide an improved version.
                Otherwise, return the original query unchanged.""",
                input_variables=["question"]
            )
            
            chain = prompt | llm_with_tool
            response = chain.invoke({"question": question})
            
            # Extract only the rewritten query from the structured output
            rewritten_query = response.rewritten_query
            
            return {"messages": [HumanMessage(content=rewritten_query)]}



        def generate(state):
            """
            Generate answer

            Args:
                state (messages): The current state

            Returns:
                dict: The updated state with re-phrased question
            """

            summary = history.get_summary()
            if summary:
                system_message = f"Summary of conversation earlier: {summary}"
            else:
                system_message =  f"Summary of conversation earlier: No conversation till now"
            messages = state["messages"]
            question = messages[-2].content
            last_message = messages[-1]

            # print("generate node per aa gye with query :" + question)
            # print("generate node per aa gye with context :" + last_message.content)

            history.add_message(question) # add the question to the history

            docs = last_message.content
            
            # Modified prompt - removed source formatting instructions
            prompt = ChatPromptTemplate([
                ("system", '''You are an assistant that helps people understand UP Police circulars and procedures in simple, everyday language.

                When answering questions:
                - Use plain, conversational language that anyone can understand
                - Explain technical terms and legal jargon in simple words
                - Structure your answer like you're talking to a friend or family member
                - Start with the most important information first
                - Use bullet points or numbered lists when helpful
                - Give practical examples when possible
                - If mentioning laws or sections, briefly explain what they mean in simple terms

                For example, instead of saying "non-cognizable cases," say "minor cases that police don't actively investigate."

                Make your response feel helpful and reassuring, not like reading a government document. Focus on what the person actually needs to know and do.

                If the answer spans multiple paragraphs, insert a <br> tag between each paragraph.
                If the answer is not available in the provided circulars, clearly state: "I don't have this information in the UP Police circulars I can access."
                Refer to the past conversation summary if relevant.
                '''),

               ("user", '''Summary: {system_message}
        
                 Question: {question}
                 Context: {context}
                 Answer:''')
            ])

            # LLM
            model = self.llm

            # Chain
            rag_chain = prompt | model | StrOutputParser()

            # Run
            response = rag_chain.invoke({"context": docs, "question": question, "system_message": system_message})

            return {"messages": [response]}


        workflow = StateGraph(AgentState)
        workflow.add_node("rewrite", rewrite)  # Rewriting the question
        workflow.add_node("retrieve", retrieve)  # Retrieval step
        workflow.add_node("generate", generate)  # Generating a response after we know the documents are relevant
        workflow.add_node("generic_agent", generic_agent)  # Generic agent
        workflow.add_node("summarize_conversation", summarize_conversation)
        workflow.add_node("retrieve_again", retrieve_again)
        
        workflow.add_edge(START, "retrieve")  # Start to retrieve
        workflow.add_conditional_edges(
            "retrieve",
            grade_documents,
            {
                "rewrite": "rewrite",  # If relevant, go to rewrite
                "generic_agent": "generic_agent",  # If not relevant, fallback to generic agent
            },
        )
        workflow.add_edge("rewrite", "retrieve_again")  # Rewrite to retrieve_again
        workflow.add_edge("retrieve_again", "generate")  # Retrieve_again to generate
        workflow.add_edge("generate", "summarize_conversation")
        workflow.add_edge("generic_agent", "summarize_conversation")
        workflow.add_edge("summarize_conversation", END)

        from langgraph.checkpoint.memory import MemorySaver
        memory = MemorySaver()
        graph = workflow.compile()
        return graph


    def chatbot(self, query: str, language: str) -> str:
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

        # Initialize relevant sources set for each query
        self.relevant_sources = set()
        self.source_scores = {}

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
        elif "generic_agent" in parsed_json and "messages" in parsed_json["generic_agent"]:
            final_response = parsed_json["generic_agent"]["messages"][0]
        
        if language == 'hindi':
            final_response = GoogleTranslator(source='en', target='hi').translate(final_response)


        # Format sources in descending order of similarity score
        if self.relevant_sources:
            # Sort sources by similarity score in descending order
            sorted_sources = sorted(
            self.relevant_sources, 
            key=lambda x: self.source_scores.get(x, 0), 
            reverse=True
            )
            
            # Limit to at most 3 relevant sources
            sorted_sources = sorted_sources[:3]
            
            final_response += "<br><br><h3>Relevant Sources:</h3>"
            for source in sorted_sources:
                final_response += f"<a href='{source}' target='_blank'>{source}</a><br>"

        return final_response
