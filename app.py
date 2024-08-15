import streamlit as st
import json
import os
import cohere
from pinecone import Pinecone
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime

# Load JSON Data
def load_json_file(file_path):
    with open(file_path) as f:
        data = json.load(f)
    return data

# Load all the links
links_data = load_json_file("links.json")

uri = st.secrets["MONGO_DB"]

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
db = client.HEO
collection = db.HEO_queries

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# Initialize Cohere client
co = cohere.Client(os.getenv('COHERE_API_KEY'))

# Search function
def search(query, num_results=1):

    # Save question to MongoDB
    current_time = datetime.now()  # Get current date and time
    collection.insert_one({"question": query, "timestamp": current_time})

    # Get embeddings from Cohere
    response = co.embed(
        texts=[query], model="embed-english-v3.0", input_type="search_query"
    )

    embeddings = response.embeddings[0]

    # Can filter by scores to say if the result is relevant

    PINECONE_API_KEY = st.secrets["PINECONE_API_KEY"]
    pc = Pinecone(api_key=PINECONE_API_KEY)

    index_name = "heo-say-2023"
    namespace="HEOSAYS2023"
    
    index = pc.Index(index_name)
    
    query_results = index.query(
        namespace=namespace,
        vector=embeddings,
        top_k=3,
        include_values=False,
        include_metadata=True
    )

    return query_results

# Streamlit interface
st.title("HEOSays")

query = st.text_input("Enter your query here")
num_results = st.slider("Number of results", 1, 5, 3, 1)

if st.button("Search"):
            
    query_results = search(query, num_results)

    for match in query_results['matches']:
        page_number = match['metadata']['page_number']
        score = match['score']
        text = match['metadata']['text']
        words = text.replace('\n', ' ').strip().split()
        truncated_text = ' '.join(words[:30]) + "..."

        page_key = result['page_number'].split(" page")[0].strip()
        
        link = links_data.get(page_key, "No link available")
        
        st.text("Page: " + result['page_number'] + " (Score: " + score + ")" + "\nContext: " + truncated_text + "\n------\n")
        st.markdown(f"[Click here to access the document]({link})")

    # for result in search_results:
    #     words = result['text'].replace('\n', ' ').strip().split()
    #     truncated_text = ' '.join(words[:30]) + "..."
        
    #     page_key = result['page_number'].split(" page")[0].strip()
        
    #     link = links_data.get(page_key, "No link available")
        
    #     st.text("Page: " + result['page_number'] + "\nContext: " + truncated_text + "\n------\n")
    #     st.markdown(f"[Click here to access the document]({link})")
