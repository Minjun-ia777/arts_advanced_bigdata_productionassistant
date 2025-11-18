import streamlit as st
import requests
import io
from PIL import Image
import json

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI Pre-Production Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- API FUNCTIONS ---

@st.cache_data(show_spinner=False)
def query_text_api(payload):
    """
    Uses the Zephyr model for all text generation.
    This is the most stable configuration for the Free Tier.
    """
    # URL: New Router (Required)
    # MODEL: Zephyr-7b-beta (Reliable)
    API_URL = "https://router.huggingface.co/hf-inference/models/HuggingFaceH4/zephyr-7b-beta"
    
    try:
        hf_token = st.secrets["HF_TOKEN"]
    except:
        return {"error": "⚠️ Token missing. Check .streamlit/secrets.toml"}
    
    headers = {"Authorization": f"Bearer {hf_token}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        
        # If successful
        if response.status_code == 200:
            return response.json()
        
        # If loading
        elif "loading" in response.text.lower():
             return {"error": "⏳ Model is loading... (Wait 30s and try again)"}
        
        # Other errors
        else:
            return {"error": f"API Error {response.status_code}: {response.text}"}
            
    except Exception as e:
        return {"error": f"Connection error: {str(e)}"}

def query_image_api(payload):
    # URL: New Router
    # MODEL: Stable Diffusion v1.5
    API_URL = "https://router.huggingface.co/hf-inference/models/runwayml/stable-diffusion-v1-5"
    
    try:
        hf_token = st.secrets["HF_TOKEN"]
    except:
        return None
        
    headers = {"Authorization": f"Bearer {hf_token}"}
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        return response.content
    except:
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2503/2503508.png", width=50)
    st.title("User Guide")
    st.markdown("""
    **Status:** 🟢 System Ready
    
    **1. 🔑 Setup**
    Ensure Token is in Secrets.
    
    **2. ⚠️ Troubleshooting**
    If you see "Model is loading," wait 30 seconds and click again. This is normal for free accounts!
    """)
    st.divider()
    st.caption("Final Project 2025")

# --- HEADER ---
st.title("🎬 AI Pre-Production Assistant")
st.markdown("##### Transform your film ideas into scripts and storyboards instantly.")

# --- SESSION STATE ---
if 'summary_result' not in st.session_state: st.session_state.summary_result = ""
if 'logline_result' not in st.session_state: st.session_state.logline_result = ""
if 'generated_script' not in st.session_state: st.session_state.generated_script = ""

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📝 Script Doctor", "🎨 Storyboarder", "✨ Story Generator"])

# ==========================================
# TAB 1: SCRIPT DOCTOR
# ==========================================
with tab1:
    st.markdown("### 🩺 Script Analysis")
    with st.expander("ℹ️ Instructions"):
        st.markdown("Paste a scene. The AI will summarize it and give you a logline.")

    col_input, col_output = st.columns([1, 1])
    
    with col_input:
        script_input = st.text_area("Input Scene Text", height=300, placeholder="INT. ROOM - NIGHT...")
        
        if st.button("🚀 Analyze Script", type="primary"):
            if not script_input:
                st.warning("Please paste text first.")
            else:
                with st.spinner("Analyzing..."):
                    # 1. Summary (Using Zephyr to summarize)
                    summ_prompt = f"<|user|>Summarize this movie scene in 2 sentences:\n{script_input}<|assistant|>"
                    summ_payload = {"inputs": summ_prompt, "parameters": {"max_new_tokens": 150, "return_full_text": False}}
                    summ_response = query_text_api(summ_payload)
                    
                    # 2. Logline (Using Zephyr to write logline)
                    log_prompt = f"<|user|>Write a one-sentence logline for this scene:\n{script_input}<|assistant|>"
                    log_payload = {"inputs": log_prompt, "parameters": {"max_new_tokens": 60, "return_full_text": False}}
                    log_response = query_text_api(log_payload)

                    # Handle Summary
                    if isinstance(summ_response, list):
                        st.session_state.summary_result = summ_response[0].get('generated_text', '')
                    elif "error" in summ_response:
                        st.error(summ_response['error'])

                    # Handle Logline
                    if isinstance(log_response, list):
                        st.session_state.logline_result = log_response[0].get('generated_text', '')
                    elif "error" in log_response:
                        st.error(log_response['error'])

    with col_output:
        st.markdown("#### Report")
        if st.session_state.summary_result:
            st.success(f"**Summary:**\n{st.session_state.summary_result}")
        if st.session_state.logline_result:
            st.info(f"**Logline:**\n{st.session_state.logline_result}")

# ==========================================
# TAB 2: STORYBOARDER
# ==========================================
with tab2:
    st.markdown("### 🖌️ Visuals")
    
    sb_prompt = st.text_input("Shot Description:", value=st.session_state.logline_result)
    sb_style = st.selectbox("Style:", ["Cinematic", "Anime", "Cyberpunk", "Oil Painting"])
    
    if st.button("🎨 Generate Image", type="primary"):
        with st.spinner("Rendering..."):
            full_prompt = f"{sb_style} style, {sb_prompt}, 8k masterpiece, detailed"
            image_bytes = query_image_api({"inputs": full_prompt})
            
            if image_bytes:
                try:
                    image = Image.open(io.BytesIO(image_bytes))
                    st.image(image, caption=sb_style, use_container_width=True)
                except:
                    st.error("Model is loading. Try again in 30 seconds.")
            else:
                st.error("Image generation failed. Check Token.")

# ==========================================
# TAB 3: STORY GENERATOR
# ==========================================
with tab3:
    st.markdown("### 🧬 AI Screenwriter")
    
    c1, c2 = st.columns(2)
    with c1:
        genre = st.selectbox("Genre", ["Sci-Fi", "Horror", "Comedy", "Western"])
        character = st.text_input("Protagonist", placeholder="e.g. A robot")
    with c2:
        setting = st.text_input("Setting", placeholder="e.g. Mars")
        conflict = st.text_input("Conflict", placeholder="e.g. No oxygen")

    if st.button("✨ Write Scene", type="primary"):
        with st.spinner("Writing script..."):
            # Prompt engineered for Zephyr
            script_prompt = f"""<|system|>
You are a professional screenwriter. Write a movie scene in standard screenplay format.
<|user|>
Write a scene with the following details:
Genre: {genre}
Character: {character}
Setting: {setting}
Conflict: {conflict}
<|assistant|>"""
            
            payload = {
                "inputs": script_prompt,
                "parameters": {
                    "max_new_tokens": 600,
                    "return_full_text": False
                }
            }
            
            response = query_text_api(payload)
            
            if isinstance(response, list):
                generated = response[0].get('generated_text', '')
                st.session_state.generated_script = generated
                st.success("Done!")
            elif "error" in response:
                st.error(response["error"])

    if st.session_state.generated_script:
        st.text_area("Script:", value=st.session_state.generated_script, height=600)
