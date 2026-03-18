import streamlit as st
import yt_dlp
import os
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv

load_dotenv()

# Setup API Key
API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
MODEL_ID = "gemini-3.1-flash-lite-preview"

st.set_page_config(page_title="Video AI Researcher", page_icon="🎥")
st.title("🎥 Video AI Researcher")

def get_video_content(url):
    # We removed 'impersonate': 'chrome' to avoid the dependency error
    ydl_opts = {
        'skip_download': True, 
        'quiet': True, 
        'noplaylist': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # ... rest of your existing logic to get title/desc ...
            return f"TITLE: {info.get('title')}\n\nDESC: {info.get('description')}"
    except Exception as e:
        return f"FETCH_ERROR: {str(e)}"

# --- UI ---
url_input = st.text_input("Enter Video Link:")

if st.button("Analyze Video"):
    if not url_input:
        st.warning("Please paste a URL.")
    elif not API_KEY:
        st.error("API Key is missing in Streamlit Secrets!")
    else:
        with st.spinner("Decoding video data..."):
            content = get_video_content(url_input)
            
            if "FETCH_ERROR" in content:
                st.error(f"Could not read video: {content}")
            else:
                try:
                    client = genai.Client(api_key=API_KEY)
                    
                    # 1. Summary
                    res = client.models.generate_content(
                        model=MODEL_ID, 
                        contents=f"Summarize this video in 3 bullets:\n\n{content}"
                    )
                    st.subheader("📋 Summary")
                    st.write(res.text)
                    
# 2. Keywords Extraction
                    # Using a multi-line f-string for better prompt clarity
                    key_prompt = f"""
                    Extract 5 keywords from the summary below. 
                    
                    Prioritize categorizing into these three areas:
                    1. Catholic Liturgical times: (e.g., Christmas, Easter, Lent, Advent, etc.)
                    2. Catholic Spiritual themes: (e.g., Martyrdom, God's love, priesthood, pro-life, sainthood, etc.)
                    3. Social/Family themes: (e.g., Marriage, Family, Abortion, Mental Health, depression, addiction, pornography, abuse, alcoholism, divorce, suffering, relationship, etc.)

                    Summary to analyze: 
                    {res.text}

                    Instructions: Output exactly 5 keywords, separated by commas. No extra text.
                    """

                    with st.spinner("Classifying themes..."):
                        key_res = client.models.generate_content(
                            model=MODEL_ID, 
                            contents=key_prompt
                        )
                        
                        # Clean the response in case the AI adds extra spaces or quotes
                        keywords_output = key_res.text.strip() if key_res.text else "No themes identified."

                    st.subheader("🏷️ Themes & Classifications")
                    
                    # Using st.success or st.info makes the keywords pop more than st.code
                    st.info(keywords_output)
                    
                except Exception as ae:
                    st.error(f"AI Error during analysis: {str(ae)}")