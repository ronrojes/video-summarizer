import streamlit as st
import requests
import re
import vimeo
from urllib.parse import urlparse, parse_qs
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi

# --- Setup & Config ---
API_KEY = st.secrets.get("GEMINI_API_KEY")
VIMEO_TOKEN = st.secrets.get("VIMEO_TOKEN")
MODEL_ID = "gemini-3.1-flash-lite-preview"

st.set_page_config(page_title="Video Summarizer Pro", page_icon="🎥", layout="wide")

# --- Custom Styling ---
st.markdown("""
    <style>
    .stTextArea textarea { height: 180px; }
    .stTextInput input { height: 45px; }
    .stButton>button { width: 100%; height: 50px; font-weight: bold; border-radius: 8px;}
    </style>
    """, unsafe_allow_html=True)

# --- Logic Functions ---
def clean_youtube_url(url):
    """
    Cleans YouTube URLs to handle playlists. 
    It extracts the Video ID and rebuilds a clean link.
    """
    if "youtube.com/watch" in url or "youtu.be" in url:
        # Extract ID from standard or shortened links
        if "v=" in url:
            v_id = url.split("v=")[1].split("&")[0]
        else:
            v_id = url.split("/")[-1].split("?")[0]
        return f"https://www.youtube.com/watch?v={v_id}"
    return url

def get_video_content(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    clean_url = clean_youtube_url(url)
    
    # YouTube Logic
    if "youtube.com" in clean_url or "youtu.be" in clean_url:
        v_id = clean_url.split("v=")[1]
        transcript = ""
        try:
            t_list = YouTubeTranscriptApi.get_transcript(v_id)
            transcript = " ".join([i["text"] for i in t_list])
        except Exception:
            pass
        try:
            res = requests.get(clean_url, headers=headers, timeout=10)
            title = re.search(r'<title>(.*?)</title>', res.text).group(1).replace(" - YouTube", "")
            return f"TITLE: {title}\n\nCONTENT: {transcript}"
        except Exception:
            return "YouTube Meta Fetch Error."
    
    # Vimeo Logic
    if "vimeo.com" in url:
        v_id = url.split("/")[-1].split("?")[0]
        if VIMEO_TOKEN:
            try:
                v_client = vimeo.VimeoClient(token=VIMEO_TOKEN)
                v_data = v_client.get(f'/videos/{v_id}').json()
                return f"TITLE: {v_data.get('name')}\nDESC: {v_data.get('description')}"
            except Exception:
                pass
        return "Vimeo Fetch Error (Token may be missing)."
    return ""

# --- Session State Management ---
if 'summary' not in st.session_state: st.session_state.summary = ""
if 'keywords' not in st.session_state: st.session_state.keywords = ""

def reset_all():
    st.session_state.summary = ""
    st.session_state.keywords = ""
    st.session_state.url_box = ""
    st.session_state.manual_box = ""

# --- UI Layout ---
st.title("🎥 Video Summarizer Pro")
st.markdown("---")

col1, col2 = st.columns(2, gap="large")

with col1:
    st.subheader("🔗 Video Source")
    url_input = st.text_input("Enter Video Link):", key="url_box")

with col2:
    st.subheader("📝 Additional Context")
    manual_input = st.text_area("Enter Transcript or Description:", key="manual_box")

btn_col1, btn_col2 = st.columns([2, 1])
with btn_col1:
    analyze = st.button("🚀 Analyze Now", type="primary")
with btn_col2:
    st.button("🔄 Reset Fields", on_click=reset_all)

# --- Analysis Logic ---
if analyze:
    if not url_input and not manual_input:
        st.warning("Please provide a video link or manual text to begin.")
    else:
        with st.spinner("🔍 Fetching data and generating insights..."):
            fetched_data = get_video_content(url_input) if url_input else ""
            final_context = f"{fetched_data}\n\nMANUAL_INFO: {manual_input}"
            
            try:
                client = genai.Client(api_key=API_KEY)
                
                # Summary Generation
                summary_prompt = f"Summarize the video in 3 distinct and concise bullet points:\n\n{final_context}"
                st.session_state.summary = client.models.generate_content(model=MODEL_ID, contents=summary_prompt).text
                
                # Theme Generation
                theme_prompt = f"""
                Extract exactly 5 keywords from the summary. 
                Prioritize: 
                - Catholic Liturgical times (Christmas, Lent, Advent, etc.)
                - Catholic Spiritual themes (Eucharist, Martyrdom, Suffering, God's love, etc.)
                - Social/Family themes (Pro-life, Addiction, Mental Health, Abuse, etc.)
                
                Summary: {st.session_state.summary}
                
                Output ONLY 5 keywords separated by commas.
                """
                st.session_state.keywords = client.models.generate_content(model=MODEL_ID, contents=theme_prompt).text
                
            except Exception as e:
                st.error(f"⚠️ AI Engine Error: {str(e)}")

# --- Results Display (Rearranged) ---
if st.session_state.summary:
    st.divider()
    
    # Summary Section (Full Width)
    st.subheader("📋 Executive Summary")
    st.write(st.session_state.summary)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Keywords Section (Below Summary)
    st.subheader("🏷️ Tagging & Themes")
    st.code(st.session_state.keywords, language="text")
    st.caption("Click the icon in the top-right of the box above to copy these tags.")
    
    st.success("Analysis complete!")