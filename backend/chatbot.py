from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import create_retrieval_chain, create_history_aware_retriever
from langchain.chains.combine_documents.stuff import create_stuff_documents_chain
import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()


# Get API keys from environment variables
groq_api_key = os.getenv("GROQ_API_KEY")
pinecone_api_key = os.getenv("PINECONE_API_KEY")

# Initialize Pinecone client with API key

pc = Pinecone(api_key=pinecone_api_key)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    


# Define index name and dimension for Pinecone vector store
index_name = "wellmate-chatbot"
dimension = 384

# Check if index exists, if not create it
try:
    if index_name not in pc.list_indexes().names():
        print(f"Creating new index: {index_name}")  # Debug
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric='cosine',
            spec=ServerlessSpec(cloud='aws', region='us-west-2')
        )
except Exception as e:
    print("Error creating Pinecone index:", str(e))  # Debug
    raise

# Connect to existing Pinecone index and create vector store
docsearch = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embeddings)
retriever = docsearch.as_retriever(search_kwargs={"k": 1})


# Initialize Groq LLM

llm = ChatGroq(
        groq_api_key=groq_api_key,
        model_name="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0.2,
        max_tokens=500
)

# Define system prompt for contextualizing questions
contextualize_q_system_prompt = (
    "Given a chat history and the latest user question "
    "which might reference context in the chat history, "
    "formulate a standalone question that can be understood "
    "without the chat history. Do NOT answer it, just reformulate if needed."
)

# Create prompt template for contextualizing questions
contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [("system", contextualize_q_system_prompt), MessagesPlaceholder("chat_history"), ("human", "{input}")]
)

# Create history-aware retriever
history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)


# Function to enforce constraints on chatbot responses
def enforce_constraints(response, chat_history, user_input):
    print("Enforcing constraints on response:", response)  # Debug
    bot_response = response['answer']
    
    sentences = [s.strip() for s in bot_response.split('.') if s.strip()]
    if len(sentences) > 4:
        bot_response = '. '.join(sentences[:4]) + '.'
    
    if "prescribe" in bot_response.lower() and len(chat_history.messages) < 4:
        bot_response = "I need more details about your condition before prescribing anything. What symptoms are you experiencing?"
    
    banned_phrases = ["Sorry to hear", "I cannot help", "I am not a doctor", "I'm glad you reached out"]
    if any(phrase in bot_response.lower() for phrase in banned_phrases):
        bot_response = "Let me assist you. What can I help you with today? 😊"
     

    return bot_response

# Main function to generate chatbot responses
def generate_response(system_prompt, chat_history, user_input, max_history=10):
    print("Generating response for input:", user_input)  # Debug
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), MessagesPlaceholder("chat_history"), ("human", "{input}")]
    )
    
    try:
        question_answer_chain = create_stuff_documents_chain(
            llm=llm,
            prompt=prompt,
            document_variable_name="context"
        )
        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
        response = rag_chain.invoke({"input": user_input, "chat_history": chat_history.messages})
        print("Raw RAG response:", response)  # Debug
        bot_response = enforce_constraints(response, chat_history, user_input)
        
        chat_history.add_user_message(user_input)
        chat_history.add_ai_message(bot_response)
        
        if len(chat_history.messages) > max_history:
            chat_history.messages = chat_history.messages[-max_history:]
        
        return bot_response
    except Exception as e:
        print("Error in generate_response:", str(e))  # Debug
        raise