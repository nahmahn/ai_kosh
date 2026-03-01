import streamlit as st
import requests
import json
import uuid
import base64
import time
import os
import tempfile

st.set_page_config(page_title="MSME-Graph Voice Tester", page_icon="🎙️", layout="wide")

API_URL_PROCESS = "http://localhost:8000/voice/process"
API_URL_FOLLOWUP = "http://localhost:8000/voice/followup"

# Initialize session state variables if they don't exist
if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "backend_state" not in st.session_state:
    st.session_state.backend_state = {}

def reset_session():
    st.session_state.session_id = uuid.uuid4().hex
    st.session_state.chat_history = []
    st.session_state.backend_state = {}
    st.rerun()

st.title("🎙️ MSME-Graph Voice Pipeline Tester")
st.markdown("Speak into the microphone to test STT, NER extraction, and TTS follow-ups.")

# Sidebar controls
with st.sidebar:
    st.header("Settings")
    lang_hint = st.selectbox("Language Hint", ["hi", "en", "ta", "te", "mr"])
    st.text_input("Session ID", value=st.session_state.session_id, disabled=True)
    if st.button("Start New Session", type="primary", use_container_width=True):
        reset_session()
        
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Chat Interface")
    
    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("audio"):
                st.audio(msg["audio"], format="audio/wav")
    
    # Process audio if new recording is detected
    audio_upload = st.audio_input("Record your answer", key=f"audio_input_{len(st.session_state.chat_history)}")
    if audio_upload is not None:
        audio_bytes = audio_upload.getvalue()
        # Check if we already processed this exact audio clip to avoid double loops
        audio_hash = hash(audio_bytes)
        if "last_audio_hash" not in st.session_state or st.session_state.last_audio_hash != audio_hash:
            st.session_state.last_audio_hash = audio_hash
            
            with st.spinner("Processing audio with IndicConformer & NLP..."):
                # Save bytes to temporary file for upload
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
                    temp_wav.write(audio_bytes)
                    temp_wav_path = temp_wav.name
                
                try:
                    is_first_turn = len(st.session_state.chat_history) == 0
                    endpoint = API_URL_PROCESS if is_first_turn else API_URL_FOLLOWUP
                    
                    with open(temp_wav_path, "rb") as f:
                        files = {"audio": f}
                        data = {
                            "session_id": st.session_state.session_id,
                            "language_hint": lang_hint
                        }
                        
                        res = requests.post(endpoint, data=data, files=files)
                        res.raise_for_status()
                        result = res.json()
                    
                    st.session_state.backend_state = result
                    
                    transcript_data = result.get("transcript", {})
                    user_text = transcript_data.get("cleaned_transcript") or transcript_data.get("raw_transcript", "[Unintelligible]")
                    st.session_state.chat_history.append({"role": "user", "content": user_text})
                    
                    ai_text = "Analysis complete. All core fields captured!"
                    ai_audio_bytes = None
                    
                    if result.get("followup_questions_audio") and len(result["followup_questions_audio"]) > 0:
                        f_info = result["followup_questions_audio"][0]
                        ai_text = f_info.get("question", "")
                        b64audio = f_info.get("audio_base64", "")
                        if b64audio:
                            ai_audio_bytes = base64.b64decode(b64audio)
                    
                    st.session_state.chat_history.append({
                        "role": "assistant", 
                        "content": ai_text,
                        "audio": ai_audio_bytes
                    })
                    
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to FastAPI backend. Is 'python main.py' running?")
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    os.unlink(temp_wav_path)
                    st.rerun()

with col2:
    st.subheader("Live Backend State (JSON)")
    if st.session_state.backend_state:
        st.json(st.session_state.backend_state, expanded=True)
    else:
        st.info("Record audio to see the extracted entities appear here.")
