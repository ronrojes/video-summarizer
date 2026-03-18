import streamlit as st
import requests
import re
import os
from urllib.parse import urlparse, parse_qs
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi
import vimeo

# --- CONFIG & SECRETS ---
# Ensure these are added to your Streamlit Cloud "Secrets"
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
VIMEO_TOKEN = st.secrets.get("VIMEO_TOKEN") # Optional: For private Vimeo access
MODEL_ID = "gemini-1.5-flash" # Use the stable workhorse

st.set_page_config(page_title="Video AI Researcher Pro", page_icon="🎥", layout="wide")

# --- DATA FETCHING LOGIC ---
def get_vimeo_data(video_id):
    if not VIMEO_TOKEN:
        return "Vimeo Token missing in secrets."
    
    # Initialize the Vimeo Client with your new Token
    v = vimeo.VimeoClient(token=VIMEO_TOKEN)
    
    try:
        # 1. Fetch Metadata (Title/Description)
        video_res = v.get(f'/videos/{video_id}')
        if video_res.status_code != 200:
            return f"Vimeo Error: {video_res.status_code}. Check if ID {video_id} is correct."
        
        data = video_res.json()
        title = data.get('name', 'Vimeo Video')
        description = data.get('description', 'No description.')

        # 2. Fetch Transcript (Text Tracks)
        transcript = ""
        tracks_res = v.get(f'/videos/{video_id}/texttracks')
        tracks = tracks_res.json().get('data', [])
        
        if tracks:
            # Get the first track (usually English)
            link = tracks[0].get('link')
            if link:
                transcript_res = requests.get(link)
                transcript = transcript_res.text
        
        return f"TITLE: {title}\nDESC: {description}\nTRANSCRIPT: {transcript}"
    except Exception as e:
        return f"Vimeo API Exception: {str(e)}"

def get_video_content(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # --- 1. Vimeo Logic (API + Transformer) ---
    if "vimeo.com" in url:
        # Extract ID from player.vimeo.com/video/ID or vimeo.com/ID
        video_id = url.split("/")[-1].split("?")[0]
        return get_vimeo_data(video_id)

    # --- 2. YouTube Logic (Lightweight) ---
    if "youtube.com" in url or "youtu.be" in url:
        v_id = ""
        if "youtu.be" in url: v_id = url.split("/")[-1]
        else:
            query = urlparse(url).query
            v_id = parse_qs(query).get("v", [""])[0]

        transcript = ""
        try:
            t_list = YouTubeTranscriptApi.get_transcript(v_id)
            transcript = " ".join([i["text"] for i in t_list])
        except: pass

        try:
            res = requests.get(url, headers=headers, timeout=10)
            title = re.search(r'<title>(.*?)</title>', res.text).group(1).replace(" - YouTube", "")
            return f"TITLE: {title}\n\nTRANSCRIPT: {transcript if transcript else 'No transcript.'}"
        except:
            return "YouTube Meta Fetch Failed."

    return ""

# --- UI LAYOUT ---
st.title("🎥 Video AI Researcher Pro")
st.markdown("Generate summaries and Catholic/Social themes from links or manual text.")

col1, col2 = st.columns(2)

with col1:
    url_input = st.text_input("🔗 Video Link (YouTube/Vimeo/ShalomWorld):")

with col2:
    manual_desc = st.text_area("📝 Manual Description/Transcript:", placeholder="Paste text here if the link fails or is private...")

if st.button("🚀 Analyze & Generate"):
    if not url_input and not manual_desc:
        st.warning("Please provide either a video link or a description.")
    elif not GEMINI_API_KEY:
        st.error("Gemini API Key missing! Check Streamlit Secrets.")
    else:
        with st.spinner("Processing data..."):
            # 1. Get automated data
            auto_data = get_video_content(url_input) if url_input else ""
            
            # 2. Combine with manual data
            combined_context = f"{auto_data}\n\nMANUAL USER DATA: {manual_desc}"
            
            try:
                client = genai.Client(api_key=GEMINI_API_KEY)
                
                # --- SUMMARY CALL ---
                sum_res = client.models.generate_content(
                    model=MODEL_ID,
                    contents=f"Summarize the video in 3 concise bullet points:\n\n{combined_context}"
                )
                
                # --- THEMES CALL ---
                theme_prompt = f"""
                Extract 5 keywords from this summary. 
                Prioritize: 
                1. Catholic Liturgical times (Christmas, Lent, etc.)
                2. Catholic Spiritual themes (Eucharist, Martyrdom, etc.)
                3. Social/Family themes (Marriage, Addiction, Pro-life, Mental Health, depression, pornography, alcoholism, divorce, etc).
                
                Summary: {sum_res.text}
                Output only 5 keywords separated by commas.
                """
                theme_res = client.models.generate_content(model=MODEL_ID, contents=theme_prompt)
                
                # --- DISPLAY RESULTS ---
                st.divider()
                st.subheader("📋 Summary")
                st.write(sum_res.text)
                
                st.subheader("🏷️ Key Themes")
                st.info(theme_res.text)
                
            except Exception as e:
                st.error(f"AI Error: {str(e)}")