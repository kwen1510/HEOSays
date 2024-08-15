import streamlit as st
import json
import os
import cohere
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime

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
def search(query, index, metadata, num_results=1):

    # Save question to MongoDB
    current_time = datetime.now()  # Get current date and time
    collection.insert_one({"question": query, "timestamp": current_time})

    # Generate query embedding with Cohere
    response = co.embed(texts=[query], model='large')
    query_embedding = response.embeddings[0]
    
    # nearest_neighbors = index.get_nns_by_vector(query_embedding, num_results)
    # return [metadata[i] for i in nearest_neighbors]

# Streamlit interface
st.title("HEOSays")

query = st.text_input("Enter your query here")
num_results = st.slider("Number of results", 1, 5, 3, 1)

if st.button("Search"):
    # Preparing metadata array; adjust according to your structure if needed
    metadata_array = []
    # for key, values in loaded_data.items():
    #     for value in values:
    #         metadata_array.append({"page_number": key, "text": value})
            
    # search_results = search(query, ann_index, metadata_array, num_results)

    # for result in search_results:
    #     words = result['text'].replace('\n', ' ').strip().split()
    #     truncated_text = ' '.join(words[:30]) + "..."
        
    #     page_key = result['page_number'].split(" page")[0].strip()
        
    #     link = links_data.get(page_key, "No link available")
        
    #     st.text("Page: " + result['page_number'] + "\nContext: " + truncated_text + "\n------\n")
    #     st.markdown(f"[Click here to access the document]({link})")
