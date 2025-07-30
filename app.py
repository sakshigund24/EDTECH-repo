# app.py

import os
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from googleapiclient.discovery import build
import fitz  # PyMuPDF
import docx

# ==== CONFIG ====
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]

# ==== LangChain Model ====
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GEMINI_API_KEY)

def run_chain(task, text):
    prompt = ChatPromptTemplate.from_template("{task}\n\n{text}")
    chain = prompt | llm
    return chain.invoke({"task": task, "text": text}).content


# ==== File Reader ====
def extract_text(file):
    if file.name.endswith(".pdf"):
        doc = fitz.open(stream=file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    elif file.name.endswith(".docx"):
        doc = docx.Document(file)
        return "\n".join([para.text for para in doc.paragraphs])
    elif file.name.endswith(".txt"):
        return file.read().decode()
    else:
        return "Unsupported file type."

# ==== YouTube Search ====
def get_youtube_videos(query):
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    req = youtube.search().list(q=query, part="snippet", maxResults=3)
    res = req.execute()
    videos = []
    for item in res['items']:
        title = item['snippet']['title']
        video_id = item['id'].get('videoId')
        url = f"https://www.youtube.com/watch?v={video_id}"
        videos.append((title, url))
    return videos

# ==== Streamlit UI ====
st.set_page_config(page_title="📘 Educational Content Generator", layout="centered")
st.title("📘 Educational Content Generator Agent")

uploaded_file = st.file_uploader("Upload Document (PDF, Word, TXT)", type=["pdf", "docx", "txt"])
custom_text = st.text_area("Enter your topic/query (e.g. 'Summarize chapter 2'): ")

col1, col2, col3, col4 = st.columns(4)
with col1:
    do_summary = st.checkbox("Summarize")
with col2:
    do_flashcards = st.checkbox("Flashcards")
with col3:
    do_quiz = st.checkbox("Quiz")
with col4:
    do_youtube = st.checkbox("Suggest Videos")

if st.button("Generate"):
    extracted_text = ""
    if uploaded_file:
        extracted_text = extract_text(uploaded_file)

    if not extracted_text and not custom_text:
        st.warning("Please upload a file or enter a topic/query.")
    else:
        if uploaded_file and custom_text:
            input_text = f"{custom_text}\n\nHere is the content to refer:\n{extracted_text}"
        else:
            input_text = extracted_text if uploaded_file else custom_text

        if do_summary:
            st.subheader("📄 Summary")
            st.write(run_chain("Summarize the following text:", input_text))

        if do_flashcards:
            st.subheader("🧠 Flashcards")
            flashcard_text = run_chain("Create flashcards (term and definition) from the following text:", input_text)
            flashcards = flashcard_text.strip().split("\n")
            for card in flashcards:
                if ":" in card:
                    term, definition = card.split(":", 1)
                    with st.expander(f"🃏 {term.strip()}"):
                        st.markdown(f"**Answer:** {definition.strip()}")
                else:
                    st.write(card)

        if do_quiz:
            st.subheader("❓ Multiple Choice Quiz")
            quiz_text = run_chain("Generate 5 multiple choice questions (with options A, B, C, D and correct answer marked) from the following text:", input_text)
            st.markdown(quiz_text)

        if do_youtube:
            st.subheader("📺 YouTube Suggestions")
            topic = custom_text if custom_text else input_text[:100]
            results = get_youtube_videos(topic)
            for title, link in results:
                st.markdown(f"- [{title}]({link})")

        if not any([do_summary, do_flashcards, do_quiz, do_youtube]):
            st.subheader("📘 Educational Response")
            st.write(run_chain("Respond to the following educational query:", input_text))
