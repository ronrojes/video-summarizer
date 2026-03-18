import streamlit as st
import requests
import re
import os
from urllib.parse import urlparse, parse_qs
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG & API SETUP ---
API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
MODEL_ID = "gemini-2.0-flash-lite-preview-02-05" # Updated to latest stable flash

st.set_page_config(page_title="Video AI Researcher", page_icon="🎥")
st.title("🎥 Video AI Researcher")

# --- DATA FETCHING LOGIC ---
def get_video_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }

    # 1. Transform Vimeo Player links to standard links
    if "player.vimeo.com/video/" in url:
        v_id = url.split("/")[-1].split("?")[0]
        url = f"https://vimeo.com/{v_id}"

    # 2. YouTube Logic (Lightweight)
    if "youtube.com" in url or "youtu.be" in url:
        v_id = ""
        if "youtu.be" in url:
            v_id = url.split("/")[-1]
        else:
            query = urlparse(url).query
            v_id = parse_qs(query).get("v", [""])[0]

        transcript = ""
        try:
            t_list = YouTubeTranscriptApi.get_transcript(v_id)
            transcript = " ".join([i["text"] for i in t_list])
        except:
            pass

        try:
            res = requests.get(url, headers=headers, timeout=15)
            title = re.search(r'<title>(.*?)</title>', res.text).group(1).replace(" - YouTube", "")
            return f"TITLE: {title}\n\nTRANSCRIPT: {transcript if transcript else 'No transcript available.'}"
        except:
            return "FETCH_ERROR: YouTube connection failed."

    # 3. Vimeo Logic (HTML Scrape)
    if "vimeo.com" in url:
        try:
            res = requests.get(url, headers=headers, timeout=15)
            title_m = re.search(r'<title>(.*?)</title>', res.text)
            desc_m = re.search(r'<meta name="description" content="(.*?)">', res.text)
            title = title_m.group(1).replace("on Vimeo", "").strip() if title_m else "Vimeo Video"
            description = desc_m.group(1) if desc_m else "No description."
            return f"TITLE: {title}\n\nDESCRIPTION: {description}"
        except:
            return "FETCH_ERROR: Vimeo connection failed."

    return "FETCH_ERROR: Unsupported URL."

# --- USER INTERFACE ---
url_input = st.text_input("Paste YouTube or Vimeo URL here:")

if st.button("Generate Summary"):
    if not url_input:
        st.warning("Please provide a link first.")
    elif not API_KEY:
        st.error("API Key missing! Check Streamlit Secrets.")
    else:
        with st.spinner("Analyzing video data..."):
            raw_data = get_video_content(url_input)
            
            if "FETCH_ERROR" in raw_data:
                st.error(raw_data)
            else:
                try:
                    client = genai.Client(api_key=API_KEY)
                    
                    # 1. Generate Summary
                    sum_res = client.models.generate_content(
                        model=MODEL_ID,
                        contents=f"Summarize this video in 3 concise bullet points:\n\n{raw_data}"
                    )
                    st.subheader("📋 Summary")
                    st.write(sum_res.text)

                    # 2. Generate Themes (Your custom logic)
                    theme_prompt = f"""
                    Extract 5 keywords from this summary. 
                    Prioritize: 
                    1. Catholic Liturgical times (Christmas, Easter, Lent, etc.)
                    2. Catholic Spiritual themes (Martyrdom, priesthood, pro-life, etc.)
                    3. Social/Family themes (Marriage, Mental Health, addiction, etc.)

                    Summary: {sum_res.text}
                    
                    Output only 5 keywords separated by commas.
                    """
                    
                    theme_res = client.models.generate_content(model=MODEL_ID, contents=theme_prompt)
                    st.subheader("🏷️ Themes")
                    st.info(theme_res.text)

                except Exception as e:
                    st.error(f"AI Error: {str(e)}")