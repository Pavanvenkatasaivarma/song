import speech_recognition as sr
import os
import webbrowser
import streamlit as st
import threading
from selenium import webdriver
import time
from gtts import gTTS
from playsound import playsound
import langchain
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import SystemMessage
from langchain.memory import ConversationBufferMemory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from googleapiclient.discovery import build
from langchain_core.prompts import PromptTemplate

load_dotenv()
store = {}

llama_model = ChatGroq(
    groq_api_key=os.environ.get('GROQ_API_KEY'),
    model="llama-3.1-70b-versatile",
    temperature=0,
)

# Define the prompt template for the AI assistant to generate song links
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
    """),
    
    MessagesPlaceholder(variable_name="chat_history"),
    HumanMessagePromptTemplate.from_template("""
        The user wants a song link. Given the song name and platform in the input below, generate only the link.
        If the platform is not mentioned, use youtube by default to generate the link.

        input: {text}

        Provide the output strictly in the format:
        "<valid URL>"
    """)
])

api_key = os.environ.get("YOU_API_KEY")  # Replace with your API key
youtube = build("youtube", "v3", developerKey=api_key)
def play_song(song_name):
    prompt_extract = PromptTemplate.from_template(
            """
            ### USER TEXT :
            {data}
            ### INSTRUCTION:
            You are a music assistant. Your task is to understand user input and provide only the relevant movie song name.
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

# Initialize the WebDriver
driver = webdriver.Chrome()

def speak(text):
    """Speak the given text using gTTS."""
    try:
        tts = gTTS(text=text, lang='en')
        tts.save("speech.mp3")
        playsound("speech.mp3")
        os.remove("speech.mp3")
    except Exception as e:
        print(f"Error: {e}")

def listen():
    """Listen for user commands."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("Listening...")
        try:
            audio = recognizer.listen(source)
            command = recognizer.recognize_google(audio)
            st.write(f"You said: {command}")
            return command.lower()
        except sr.UnknownValueError:
            st.write("Error: Could not understand the audio.")
        except sr.RequestError:
            st.write("Error: Issue with the speech recognition service.")
        except Exception as e:
            st.write(f"Error: {str(e)}")
        return None

def play_music():
    """Function to open the music app or play a song."""
    music_folder = "C:/Users/YourUsername/Music"  # Change this path to your music folder
    songs = os.listdir(music_folder)
    if songs:
        os.startfile(os.path.join(music_folder, songs[0]))  # Play the first song
        speak("Playing your music.")
        st.write(f"Playing: {songs[0]}")
    else:
        speak("No songs found in your music folder.")
        st.write("No songs found in your music folder.")

def search_music(song_name):
    """Search for a song on YouTube."""
    speak(f"Searching for {song_name}")
    st.write(f"Searching for {song_name}")
    def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
        if session_id not in store:
            store[session_id] = InMemoryChatMessageHistory()
        return store[session_id]

    chain = prompt | llama_model
    chains = RunnableWithMessageHistory(chain, get_session_history, input_messages_key="text",
                                        history_messages_key="chat_history")
    response = chains.invoke(
        input={"text": song_name},
        config={"configurable": {"session_id": "abc123"}}
    )
    print(response.content)
    driver.get(f"{response.content}")

# Initialize the WebDriver
driver = webdriver.Chrome()

# Streamlit app
def main():
    """Main function for the AI assistant."""
    st.title("AI Music Assistant 🎵")
    st.write("Hello! I am your music assistant. How can I help you?")
    speak("Hello! I am your music assistant. How can I help you?")

    user_command = st.text_input("Enter your command (e.g., 'play music', 'search [song name] on YouTube'):")

    while True:
        command = listen()
        if command:
            if "song" in command or "songs" in command:
                if "play music" in command:
                    play_music()
                elif "search" in command:
                    song_name = command.strip()
                    search_music(song_name)
               elif "play" in command:
                    song_name = command.strip()
                    play_music(song_name) 
                elif "stop" in command:
                    driver.close()
                elif "exit" in command or "quit" in command:
                    speak("Goodbye! Have a nice day!")
                    driver.quit()
                    break
                else:
                    st.write("Sorry, I didn't understand that.")
            else:
                st.write("No valid command detected.")
        else:
            st.write("No command received. Listening again...")

if __name__ == "__main__":
    main()
