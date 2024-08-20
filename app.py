# from dotenv import load_dotenv
import os
import streamlit as st
import json
import cohere
from pinecone import Pinecone
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
import random
from openai import OpenAI
# from fuzzywuzzy import process

# Set page config
st.set_page_config(
    page_title="HEOSays",  # Set your desired title here
    page_icon="🎓",  # You can use an emoji or a path to an image file
    layout="wide",  # Optional: Use "wide" or "centered" for your layout
    initial_sidebar_state="expanded",  # Optional: Use "expanded" or "collapsed"
)

st.markdown(
    """
    <meta property="og:title" content="HEOSays">
    <meta property="og:description" content="HEOSays">
    """,
    unsafe_allow_html=True,
)

# st.markdown(
#     """
#     <meta property="og:title" content="HEOSays">
#     <meta property="og:description" content="Your custom description here.">
#     <meta property="og:image" content="URL_to_your_image">
#     <meta property="og:url" content="https://heo-says-37d5f8bda04f.herokuapp.com/">
#     """,
#     unsafe_allow_html=True,
# )


# Load environment variables from .env file
# load_dotenv()

# Need to include the parameters here
context_length = 30


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

# # Function to perform fuzzy search and return fixed text if match is found
# def fuzzy_search(text, variants, threshold=80):
#     # Split the input text into individual words or phrases
#     words = text.split()
    
#     # Check each word against the variants list using fuzzy matching
#     for word in words:
#         # Use fuzzy matching to find the closest match and its score
#         match, score = process.extractOne(word, variants)
#         # If the score exceeds the threshold, return the fixed phrase
#         if score > threshold:
#             return "want deadlines"
#     # If no word exceeds the threshold, return an indication of no match
#     return "No relevant deadlines found."

uri = os.getenv('MONGO_DB')

# Load your API key securely
openai_api_key = os.getenv("OPENAI_KEY")

organization = os.getenv('OPENAI_ORGANISATION')
model = os.getenv("OPENAI_MODEL")

openai_client = OpenAI(
    api_key=openai_api_key,
    organization=organization
)

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

    PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
    pc = Pinecone(api_key=PINECONE_API_KEY)

    index_name = os.getenv('INDEX_NAME')
    namespace = os.getenv('NAMESPACE')
    
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

# OpenAI Completions code
def get_ai_response(query):
    try:
        completion = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": query}],
            stream=False  # Adjust based on your actual requirement
        )
        return completion.choices[0].message.content
    except Exception as e:
        st.error(f"Failed to obtain AI response: {str(e)}")


query = st.text_input("Enter your query here")
# num_results = st.slider("Number of results", 1, 5, 3, 1)
num_results = 10 # Get 10 results to rerank




if st.button("Search"):

    if query.strip() == "":  # Check if the query is empty after stripping
        st.error("Please enter a valid query before searching.")

    else:
        # Set threshold value (this is an abitrary value)
        threshold = 0.4
    
        query_results = search(query, num_results)
    
        # Check top score first. If below threshold, reject
        top_score = query_results['matches'][0]['score']
        print(top_score)
    
        if top_score >= threshold:
    
            ## To ensure that same pages are not repeated.
    
            # Create new empty object
            pages_list = []
            top_k = 3 # To only return the top k value
            current_number = 0 # Initial response
    
            ## Create the AI response first
    
            # Relevant text for the AI model
            relevant_text = []
    
            # Concatenate all responses
            for current_index, match in enumerate(query_results['matches']):
    
                if current_index < 5:
    
                    relevant_text.append(match['metadata']['text'])
    
                else:
                    break
    
    
            # Create prompt
    
            joined_text = " ".join(relevant_text)
            
            prompt = f"You are a higher education mentor answering student queries about higher education stuff. Please answer the question using only information from the text below. ### Question: {query} ### Text: {joined_text} ### Your output should just be your answer to the person. If you cannot find any relevant information, please say: 'I am unsure...'"
    
            st.subheader("AI Summary")
            st.markdown(
                f"<pre style='font-size:smaller; white-space: pre-wrap; word-wrap: break-word;'>"
                f"{get_ai_response(prompt)}<br>------<br>"
                f"</pre>", unsafe_allow_html=True
            )
    
            st.subheader("Documents found")
    
            for match in query_results['matches']:
    
                # Check if current number >= top_k. If greater than 3, break out of the loop
                if current_number > top_k:
                    break
    
                if top_score >= threshold:
               
                    page_number = match['metadata']['page_number']
    
                    # If the page number does not exist yet
                    if page_number not in pages_list:
                        # Append the page number to the list then run the code
                        pages_list.append(page_number)
                    
                        score = match['score']
                        text = match['metadata']['text']
                        words = text.replace('\n', ' ').strip().split()
                        truncated_text = ' '.join(words[:context_length]) + "..." if len(words) > context_length else ' '.join(words)
                
                        page_key = page_number.split(" page")[0].strip()
                        
                        link = links_data.get(page_key, "No link available")
                        
                        # st.write(f"Page: {page_number} (Score: {score * 100:.0f}%)\nContext: {truncated_text}\n------\n")
        
                        st.markdown(
                            f"<pre style='font-size:smaller; white-space: pre-wrap; word-wrap: break-word;'>"
                            f"Page: {page_number} (Score: {score * 100:.0f}%)<br>"
                            f"Context: {truncated_text}<br>------<br>"
                            f"</pre>", unsafe_allow_html=True
                        )
                        
                        st.markdown(f"[Click here to access the document]({link})")
    
                        current_number += 1
    
            # # Perform the fuzzy search to see if the person wants deadlines (append to end)
            # result = fuzzy_search(input_string, variants)
    
            # Just insert the deadlines anyway
            result = "want deadlines"
            
            if result == "want deadlines":
        
                st.subheader("You might also be interested in the application deadlines:")
                
                # Display the table
                st.table(deadlines)
    
        else:
            # Define a list of philosophical lines
            philosophical_lines = [
                "Amid the clutter of existence, I search for meaning, like a shadow chasing light, only to grasp at echoes of understanding that slip through my fingers like sand.",
                "In the labyrinth of life, I wander, seeking answers that often elude me, and in this journey, I find that not all that is sought can be found, nor all that is lost is missing.",
                "I pursue the intangible with a fervor, seeking the unseeable stars hidden behind the daylight, learning that the quest itself enriches more than the discovery.",
                "Each day, I delve into the depths of the mind's caverns, reaching for truths veiled in obscurity, only to realize the treasure lies in the search, not the spoils.",
                "As I chase the horizons of understanding, they retreat ever further into the mists of unknowing, teaching me that in the pursuit of knowledge, the path walked is the wisdom gained."
            ]
            
            # Streamlit interface handling for no relevant results
            if top_score < threshold:
                # Select a random philosophical line
                random_line = random.choice(philosophical_lines)
                print("No relevant sources found")
                st.markdown(
                    f"<pre style='font-size:smaller; white-space: pre-wrap; word-wrap: break-word;'>"
                    f"{random_line}"
                    f"</pre>", unsafe_allow_html=True
                )
    
    
                # Just insert the deadlines anyway
                result = "want deadlines"
                
                if result == "want deadlines":
            
                    st.subheader("You might also be interested in the application deadlines:")
                    
                    # Display the table
                    st.table(deadlines)
