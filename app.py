import streamlit as st
import requests
import re
import vimeo
from urllib.parse import urlparse, parse_qs
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi

# --- SETUP & CONFIGURATION ---
# These must be set in your Streamlit Cloud "Secrets"
API_KEY = st.secrets.get("GEMINI_API_KEY")
VIMEO_TOKEN = st.secrets.get("VIMEO_TOKEN")
MODEL_ID = "gemini-3.1-flash-lite-preview"

st.set_page_config(page_title="Video Summarizer Pro", page_icon="🎥", layout="wide")

# Custom CSS for alignment and modern look
st.markdown("""
    <style>
    .stTextArea textarea { height: 180px; }
    .stTextInput input { height: 45px; }
    .stButton>button { width: 100%; height: 50px; font-weight: bold; border-radius: 8px; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIC FUNCTIONS ---
def clean_youtube_url(url):
    """Removes playlist and radio parameters from YouTube URLs."""
    if "youtube.com/watch" in url:
        v_id = re.search(r"v=([a-zA-Z0-9_-]+)", url)
        return f"https://www.youtube.com/watch?v={v_id.group(1)}" if v_id else url
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
            return f"TITLE: {title}\n\nCONTENT: {transcript}"
        except: return None

    # Vimeo Logic (Using Authenticated API)
    if "vimeo.com" in url:
        v_id = url.split("/")[-1].split("?")[0]
        if VIMEO_TOKEN:
            try:
                v_client = vimeo.VimeoClient(token=VIMEO_TOKEN)
                v_data = v_client.get(f'/videos/{v_id}').json()
                title = v_data.get('name', 'Vimeo Video')
                desc = v_data.get('description', '')
                # Attempt to get transcript via texttracks API
                transcript = ""
                tracks_res = v_client.get(f'/videos/{v_id}/texttracks').json()
                if tracks_res.get('data'):
                    link = tracks_res['data'][0].get('link')
                    if link: transcript = requests.get(link).text
                return f"TITLE: {title}\nDESC: {desc}\nTRANSCRIPT: {transcript}"
            except: pass
        return "Vimeo Fetch Error or Token Missing."
    
    return ""

# --- SESSION STATE MANAGEMENT ---
# Prevents data from disappearing when interacting with the UI
if 'summary' not in st.session_state: st.session_state.summary = ""
if 'keywords' not in st.session_state: st.session_state.keywords = ""

def reset_all():
    st.session_state.summary = ""
    st.session_state.keywords = ""
    # Clearing the text boxes manually
    st.session_state.url_box = ""
    st.session_state.manual_box = ""

# --- UI LAYOUT ---
st.title("🎥 Video Summarizer Pro")

col1, col2 = st.columns(2, gap="large")
with col1:
    url_input = st.text_input("🔗 Video Link:", key="url_box", value=st.session_state.get('url_box', ""))
with col2:
    manual_input = st.text_area("📝 Manual Content (Description or Transcript):", key="manual_box", value=st.session_state.get('manual_box', ""))

btn_col1, btn_col2 = st.columns([2, 1])
with btn_col1:
    analyze = st.button("🚀 Analyze Now", type="primary")
with btn_col2:
    st.button("🔄 Reset Fields", on_click=reset_all)

# --- ANALYSIS LOGIC ---
if analyze:
    if not url_input and not manual_input:
        st.warning("Please provide a link or text.")
    else:
        with st.spinner("🔍 AI is thinking..."):
            fetched_data = get_video_content(url_input) if url_input else ""
            final_context = f"{fetched_data}\n\nMANUAL: {manual_input}"
            
            try:
                client = genai.Client(api_key=API_KEY)
                
                # Generate Summary
                summary_prompt = f"Summarize the video in 3 concise bullets:\n\n{final_context}"
                st.session_state.summary = client.models.generate_content(model=MODEL_ID, contents=summary_prompt).text
                
                # Generate Themed Keywords
                theme_prompt = f"""
                Extract 5 keywords from the following summary. 
                Prioritize: Catholic Liturgical times (Christmas, Lent, Advent, etc.),"
                Catholic Spiritual themes (Martyrdom, Suffering, God's love, Eucharist, etc.), and Social/Family themes "
                (Family life, Divorce, Addiction, Abortion, Pro-life, Alchohol Addiction, Porn Addiction, Sexual Addiction, "
                "Pornography, Abuse, Mental Health, etc.).\n\n"
                Summary: {st.session_state.summary}
                Output ONLY 5 keywords separated by commas.
                """
                st.session_state.keywords = client.models.generate_content(model=MODEL_ID, contents=theme_prompt).text
                
            except Exception as e:
                st.error(f"AI Error: {str(e)}")

# --- RESULTS DISPLAY ---
if st.session_state.summary:
    st.divider()
    res_col1, res_col2 = st.columns([2, 1], gap="medium")
    
    with res_col1:
        st.subheader("📋 Summary")
        st.write(st.session_state.summary)
    
    with res_col2:
        st.subheader("🏷️ Keywords")
        # st.code provides a native copy button and only shows keywords once
        st.code(st.session_state.keywords, language="text")
        st.caption("Click the icon in the top-right of the box above to copy.")
    
    st.success("Analysis complete!")