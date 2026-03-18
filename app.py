import streamlit as st
import yt_dlp
import os
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
import requests
import re

load_dotenv()

# Setup API Key
API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
MODEL_ID = "gemini-3.1-flash-lite-preview"

st.set_page_config(page_title="Video AI Researcher", page_icon="🎥")
st.title("🎥 Video AI Researcher")

def get_video_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }

    # Step 1: Try yt-dlp first (it's best for YouTube transcripts)
    try:
        ydl_opts = {'skip_download': True, 'quiet': True, 'noplaylist': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', '')
            description = info.get('description', '')
            
            transcript = ""
            if "youtube" in url or "youtu.be" in url:
                try:
                    video_id = info.get('id')
                    t_list = YouTubeTranscriptApi.get_transcript(video_id)
                    transcript = " ".join([i["text"] for i in t_list])
                except: pass
            
            # If we got a title, we are successful
            if title:
                return f"TITLE: {title}\n\nDESC: {description}\n\nTRANSCRIPT: {transcript}"
    except Exception as e:
        print(f"yt-dlp failed, switching to manual scrape: {e}")

    # Step 2: MANUAL FALLBACK (The 'Vimeo Fix')
    # If yt-dlp fails (XML error), we fetch the HTML page directly
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # Use Regex to find Title and Description in the HTML Meta Tags
        title_match = re.search(r'<title>(.*?)</title>', response.text)
        desc_match = re.search(r'<meta name="description" content="(.*?)">', response.text)
        
        title = title_match.group(1) if title_match else "Unknown Video"
        description = desc_match.group(1) if desc_match else "No description available."
        
        return f"TITLE: {title}\n\nDESC: {description}\n\nNote: Data fetched via manual scrape."
    except Exception as e:
        return f"FETCH_ERROR: Both yt-dlp and manual scrape failed. {str(e)}"

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