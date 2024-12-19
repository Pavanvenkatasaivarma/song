from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import speech_recognition as sr
import os
from selenium import webdriver
import threading
from langchain_groq import ChatGroq
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import SystemMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from dotenv import load_dotenv
from googleapiclient.discovery import build
from langchain_core.prompts import PromptTemplate

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "abcd"

store = {}

# Initialize language model
llama_model = ChatGroq(
    groq_api_key=os.environ.get('GROQ_API_KEY'),
    model="llama3-groq-70b-8192-tool-use-preview",
    temperature=0,
)

# Define the prompt template for generating song links
prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="""Scenario: You are an AI assistant designed to help users find music and song links.
        You have access to platforms like YouTube and JioSaavn. Your task is to generate accurate and relevant song links based on user input. If the platform is not mentioned, default to JioSaavn and generate the URL for it.

        Example output for a song search:
        "https://www.youtube.com/results?search_query=ninu+kori+songs"

        Do's:
            - Generate song links using only the platforms mentioned (YouTube).
            - If no platform is specified, assume youtube by default.
            - Validate the user's input to ensure it matches the song name and platform. If not provided or incorrect, return "Invalid input."
            - Always provide the link in the exact format specified in the output example.
            - Ensure generated links are valid, clickable, and formatted correctly (e.g., valid URLs).
            - If the song is unavailable on the specified platform, return "Song not available on the requested platform."
            - Cross-check the song details with the requested platform to ensure relevance.
            - Maintain 100% accuracy in generating song links without any errors.

        Don'ts:
            - Do not generate links for platforms other than YouTube and JioSaavn.
            - Do not include any extra text or commentary in the output other than the song link.
            - Do not generate a response if the user's input does not specify a valid song name.
            - Do not generate invalid or unrelated URLs (e.g., https://www.youtube.com/feed/playlists).
            - Do not assume the song exists without verifying its availability.

        Example additional detail:
        Your are highly intelligent, knows all song links in the world, and always generates accurate and relevant links for any given input with 100% precision. It never fails to provide valid, formatted links that meet user requirements."""),
            
    # Placeholder for storing the conversation history
    MessagesPlaceholder(variable_name="chat_history"),
    
    # Template for human message prompt asking for song link generation
    HumanMessagePromptTemplate.from_template("""
        The user wants a song link. Given the song name and platform in the input below, generate only the link.
        If the platform is not mentioned, use youtube by default to generate the link.

        input: {text}

        Provide the output strictly in the format:
        "<valid URL>"
        
        Example:
        -"https://www.youtube.com/results?search_query=ninu+kori+songs"
        -"https://www.jiosaavn.com/song/pushpa-pushpa-telugu/GS8HdCF2RFQ"
    """)
])


# Set up YouTube Data API client
api_key = os.environ.get("YOU_API_KEY") # Replace with your API key
youtube = build("youtube", "v3", developerKey=api_key)

def play_song(song_name):
    prompt_extract = PromptTemplate.from_template(
            """
            ### USER TEXT :
            {data}
            ### INSTRUCTION:
            You are a music assistant. Your task is to understand user input and provide only the relevant song name.
            """
        )
    chain = prompt_extract | llama_model
    response = chain.invoke(input={"data": song_name})
    name=response.content
    # Search for the song on YouTube
    request = youtube.search().list(
        part="snippet",
        q=name,
        type="video",
        maxResults=1
    )
    response = request.execute()

    # Get the video URL
    video_id = response["items"][0]["id"]["videoId"]
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    return video_url

# Example usage:



def play_music():
    """Function to open the music app or play a song."""
    music_folder = "C:/Users/YourUsername/Music"  # Change this path to your music folder
    songs = os.listdir(music_folder)
    if songs:
        os.startfile(os.path.join(music_folder, songs[0]))  # Play the first song
    else:
        print("no songs available")
def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
        if session_id not in store:
            store[session_id] = InMemoryChatMessageHistory()
        return store[session_id]
def search_music(song_name):
    """Search for a song on YouTube."""

    chain = prompt | llama_model

    chains = RunnableWithMessageHistory(chain, get_session_history,input_messages_key="text",
            history_messages_key="chat_history")
    
    response = chains.invoke(
            input={
                "text":song_name
            },
            config={
                "configurable": {"session_id": "abc123"}
            }
        )
    print(response.content)
    return response.content

# Flask routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    song_name = request.form.get('song_name')
    if not song_name:
        return render_template('index.html', error="Please provide a song name.")
    elif "search" in song_name:
        link = search_music(song_name)
        return render_template('index.html', result=link)
    elif "play" in song_name:
        link = play_song(song_name)
        print(f"Watch '{song_name}' on YouTube: {link}")
        return render_template('index.html', result=link)
    else:
        return render_template('index.html', error="Please provide clear information")

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
