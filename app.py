import streamlit as st
import os
import yt_dlp
from google import genai

# --- Setup & Config ---
# Streamlit Cloud uses st.secrets. Locally, it will look for .streamlit/secrets.toml
API_KEY = st.secrets.get("GEMINI_API_KEY")
MODEL_ID = "gemini-3.1-flash-lite-preview"

# Page Configuration
st.set_page_config(page_title="Video Summarizer Pro", page_icon="🎥")
st.title("🎥 Video Summarizer")
st.markdown("Enter a video link to get a 3-bullet summary and key themes.")

# --- Logic Functions ---
def get_video_content(url):
    ydl_opts = {
        'skip_download': True, 
        'quiet': True, 
        'noplaylist': True,
        'extractor_args': {'vimeo': {'player_client': ['web']}},
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown Title')
            description = info.get('description', 'No description available.')
            return f"TITLE: {title}\n\nDESCRIPTION: {description}"
    except Exception as e:
        st.error(f"Fetcher Error: {str(e)}")
        return None

def process_ai(content):
    client = genai.Client(api_key=API_KEY)
    
    # 1. Summary Call
    sum_prompt = f"Summarize the video in 3 distinct bullet points based on this information:\n\n{content}"
    sum_res = client.models.generate_content(model=MODEL_ID, contents=sum_prompt)
    summary_text = sum_res.text
    
    # 2. Keyword Call
    key_prompt = (
        "Extract 5 keywords from this video summary. Prioritize: Catholic Liturgical times (Christmas, Lent, Advent, etc.), "
        "Catholic Spiritual themes (Martyrdom, Suffering, God's love, Eucharist, etc.), and Social/Family themes "
        "(Family life, Divorce, Addiction, Abortion, Pro-life, Alchohol Addiction, Porn Addiction, Sexual Addiction, "
        "Pornography, Abuse, Mental Health, etc.).\n\n"
        f"Summary: {summary_text}\n\nOutput only 5 keywords separated by commas."
    )
    key_res = client.models.generate_content(model=MODEL_ID, contents=key_prompt)
    keywords_text = key_res.text
    
    return summary_text, keywords_text

# --- UI Layout ---
message_place = st.empty()

url_input = st.text_input("Paste Video Link here:", placeholder="https://youtube.com/watch?v=...")

if st.button("Analyze Video"):
    message_place.empty()
    
    if not url_input:
        message_place.warning("Please enter a URL first.")
    elif not API_KEY:
        message_place.error("API Key missing! Please add GEMINI_API_KEY to your Streamlit Secrets.")
    else:
        with st.spinner("Fetching video data and thinking..."):
            video_text = get_video_content(url_input)
            
            if video_text:
                try:
                    summary, keywords = process_ai(video_text)
                    
                    st.subheader("📋 Summary")
                    st.write(summary)
                    
                    st.subheader("🏷️ Key Themes")
                    # Using st.info makes the keywords look like tags
                    st.info(keywords)
                    
                    st.success("Analysis complete!")
                except Exception as ai_err:
                    st.error(f"AI Error: {str(ai_err)}")