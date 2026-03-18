import streamlit as st
import video_describer as vd

st.title("🎥 AI Video Summarizer")

url = st.text_input("Paste Link (YouTube or Vimeo):")

if st.button("Analyze"):
    if url:
        with st.spinner("Processing..."):
            # 1. Get Metadata
            data = vd.get_video_data(url)
            
            if "error" in data:
                st.error(f"Error: {data['error']}")
            else:
                # 2. Get Transcript (if YouTube)
                transcript = ""
                if "vimeo" not in url.lower():
                    transcript = vd.get_transcript(data['id'])
                
                # 3. Generate AI Content
                summary, keywords = vd.generate_ai_content(data, transcript)
                
                st.subheader("📋 Summary")
                st.write(summary)
                
                st.subheader("🏷️ Keywords")
                st.code(keywords, language=None)