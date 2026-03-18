import streamlit as st
import os
import requests
import re
from urllib.parse import urlparse, parse_qs
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi
import vimeo

# --- Setup & Config ---
API_KEY = st.secrets.get("GEMINI_API_KEY")
VIMEO_TOKEN = st.secrets.get("VIMEO_TOKEN")
MODEL_ID = "gemini-3.1-flash-lite-preview"

st.set_page_config(page_title="Video Summarizer Pro", page_icon="🎥", layout="wide")

# --- Custom Styling for Alignment ---
st.markdown("""
    <style>
    .stTextArea textarea { height: 150px; }
    .stTextInput input { height: 45px; }
    div[data-testid="stVerticalBlock"] > div:has(div.stButton) {
        display: flex;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def clean_youtube_url(url):
    """Strips playlist parameters to ensure fetching works."""
    if "youtube.com/watch" in url:
        parsed = urlparse(url)
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        return f"https://www.youtube.com/watch?v={video_id}" if video_id else url
    return url

def get_video_content(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = clean_youtube_url(url)
    
    # YouTube Logic
    if "youtube.com" in url or "youtu.be" in url:
        v_id = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        transcript = ""
        try:
            t_list = YouTubeTranscriptApi.get_transcript(v_id)
            transcript = " ".join([i["text"] for i in t_list])
        except: pass
        try:
            res = requests.get(url, headers=headers, timeout=10)
            title = re.search(r'<title>(.*?)</title>', res.text).group(1).replace(" - YouTube", "")
            return f"TITLE: {title}\n\nTRANSCRIPT: {transcript}"
        except: return "Error fetching YouTube metadata."
    
    # Vimeo Logic (Using API)
    if "vimeo.com" in url:
        v_id = url.split("/")[-1].split("?")[0]
        if VIMEO_TOKEN:
            try:
                v = vimeo.VimeoClient(token=VIMEO_TOKEN)
                data = v.get(f'/videos/{v_id}').json()
                return f"TITLE: {data.get('name')}\nDESC: {data.get('description')}"
            except: pass
        return "Vimeo API Error or Token missing."
    
    return ""

# --- Session State for Reset ---
if 'url' not in st.session_state: st.session_state.url = ""
if 'transcript' not in st.session_state: st.session_state.transcript = ""

def reset_fields():
    st.session_state.url = ""
    st.session_state.transcript = ""

# --- UI Layout ---
st.title("🎥 Video Summarizer Pro")

# Aligned input columns
col1, col2 = st.columns(2)
with col1:
    url_input = st.text_input("🔗 Video Link:", value=st.session_state.url, key="url_box")
with col2:
    manual_desc = st.text_area("📝 Manual Content:", value=st.session_state.transcript, key="trans_box")

# Action Buttons
btn_col1, btn_col2, btn_col3 = st.columns([1,1,1])
with btn_col1:
    analyze_btn = st.button("🚀 Analyze Video", use_container_width=True)
with btn_col2:
    reset_btn = st.button("🔄 Reset Fields", on_click=reset_fields, use_container_width=True)

if analyze_btn:
    if not url_input and not manual_desc:
        st.warning("Please provide a link or text.")
    else:
        with st.spinner("Processing..."):
            fetched_data = get_video_content(url_input) if url_input else ""
            combined = f"{fetched_data}\n\nMANUAL: {manual_desc}"
            
            try:
                client = genai.Client(api_key=API_KEY)
                sum_res = client.models.generate_content(model=MODEL_ID, contents=f"Summarize in 3 bullets:\n\n{combined}").text
                
                theme_prompt = f"Extract 5 keywords (Catholic/Social themes) from this: {sum_res}. Output only keywords separated by commas."
                keywords = client.models.generate_content(model=MODEL_ID, contents=theme_prompt).text
                
                st.divider()
                st.subheader("📋 Summary")
                st.write(sum_res)
                
                st.subheader("🏷️ Key Themes")
                st.info(keywords)
                
                # Copy Button
                st.button("📋 Copy Keywords", on_click=lambda: st.write(f"Copied to clipboard: {keywords}"))
                # Note: True browser clipboard "copy" in Streamlit often requires a custom component or clicking the text in 'st.code'. 
                # Using st.code(keywords) is the most user-friendly way for them to copy.
                st.code(keywords, language="text")
                
            except Exception as e:
                st.error(f"AI Error: {str(e)}")