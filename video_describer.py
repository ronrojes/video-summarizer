import os
import re
import yt_dlp
import streamlit as st
from dotenv import load_dotenv
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()

# 1. Standardize the API Key and Model
API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
MODEL_ID = "gemini-3.1-flash-lite-preview" # The 2026 Lite model

client = genai.Client(api_key=API_KEY)

def get_video_data(url):
    """Fetches title and description using yt-dlp (works for both YT and Vimeo)"""
    ydl_opts = {
        'skip_download': True, 'quiet': True, 'noplaylist': True,
        'extractor_args': {'vimeo': {'player_client': ['web']}}, # Vimeo 2026 Fix
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Referer': 'https://vimeo.com/',
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get('title', 'Unknown'),
                "desc": info.get('description', ''),
                "id": info.get('id')
            }
    except Exception as e:
        return {"error": str(e)}

def get_transcript(video_id):
    """Attempts to get YouTube transcript; returns empty string if fails"""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([item["text"] for item in transcript_list])
    except:
        return ""

def generate_ai_content(metadata, transcript=""):
    """One function to handle Summary + Keywords using Gemini 3.1"""
    # Combine all available text
    full_text = f"TITLE: {metadata['title']}\nDESC: {metadata['desc']}\nTRANSCRIPT: {transcript}"
    
    # Summary Prompt
    sum_prompt = f"Summarize this video in 3 distinct bullet points:\n\n{full_text}"
    summary = client.models.generate_content(model=MODEL_ID, contents=sum_prompt).text

    # Keyword Prompt (Your specific themes)
    key_prompt = (
        "Extract  keywords from this summary. Prioritize: Catholic Liturgical times (Christmas, Easter, Lent, Advent etc), "
        "Catholic Spiritual themes (Martyrdom, God's love, priesthood, pro-life, sainthood, etc), and Social/Family themes (Marriage, Family, Abortion, Mental Health, depression, addiction, pornography, abuse, alchoholism, divorce, suffering, relationship, etc).\n\n"
        f"Summary: {summary}\n\nOutput only 5 keywords separated by commas."
    )
    keywords = client.models.generate_content(model=MODEL_ID, contents=key_prompt).text
    
    return summary, keywords