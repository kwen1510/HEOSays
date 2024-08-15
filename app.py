import streamlit as st
import json
import os
import cohere
from pinecone import Pinecone
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from fuzzywuzzy import process

# Load JSON Data
def load_json_file(file_path):
    with open(file_path) as f:
        data = json.load(f)
    return data

# Load all the links
links_data = load_json_file("links.json")
deadlines = load_json_file("deadlines.json")

# Define the variants of "deadlines"
variants = ["deadline", "final date", "due date", "cut-off date", "submission date", "time limit"]

# Input string
input_string = "The final date for submissions is approaching."

def fuzzy_search(text, variants, thresholds):
    results = []
    for variant in variants:
        token_set_score = fuzz.token_set_ratio(text, variant)
        token_sort_score = fuzz.token_sort_ratio(text, variant)
        partial_score = fuzz.partial_ratio(text, variant)

        results.append({
            'variant': variant,
            'token_set_score': token_set_score,
            'token_sort_score': token_sort_score,
            'partial_score': partial_score
        })

        # Check if any score exceeds its respective threshold
        if (token_set_score > thresholds['token_set'] or
            token_sort_score > thresholds['token_sort'] or
            partial_score > thresholds['partial']):
            return "want deadlines", results  # Return on first match exceeding thresholds

    return "No relevant deadlines found.", results

# Thresholds dictionary
fuzzy_thresholds = {
    'token_set': 85,
    'token_sort': 80,
    'partial': 75
}

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

    index_name = st.secrets["INDEX_NAME"]
    namespace = st.secrets["NAMESPACE"]
    
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
# num_results = st.slider("Number of results", 1, 5, 3, 1)
num_results = 5

if st.button("Search"):

    # Perform the fuzzy search to see if the person wants deadlines
    # result = fuzzy_search(input_string, variants)
    result, debug_info = fuzzy_search(input_string, variants, fuzzy_thresholds)

    st.text(result)
    
    if result == "want deadlines":

        st.subheader("Seems like you are interested in the application deadlines:")
        
        # Display the table
        st.table(deadlines)

    # Set threshold value
    threshold = 0.4

    query_results = search(query, num_results)

    # Check top score first. If below threshold, reject
    top_score = query_results['matches'][0]['score']
    print(top_score)

    if top_score >= threshold:

        for match in query_results['matches']:

            if top_score >= threshold:
           
                page_number = match['metadata']['page_number']
                score = match['score']
                text = match['metadata']['text']
                words = text.replace('\n', ' ').strip().split()
                truncated_text = ' '.join(words[:30]) + "..."
        
                page_key = page_number.split(" page")[0].strip()
                
                link = links_data.get(page_key, "No link available")
                
                st.text(f"Page: {page_number} (Score: {score * 100:.0f}%)\nContext: {truncated_text}\n------\n")
                
                st.markdown(f"[Click here to access the document]({link})")

        # # Perform the fuzzy search to see if the person wants deadlines (append to end)
        # result = fuzzy_search(input_string, variants)

        # if result == "want deadlines":
    
        #     st.subheader("You might also find these info useful:")
            
        #     # Display the table
        #     st.table(deadlines)

    else:
        print("No relevent sources found")
        st.text("I could not find anything relevant :(")
