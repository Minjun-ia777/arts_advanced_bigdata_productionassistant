import streamlit as st
import requests
import io
from PIL import Image
import json
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI Pre-Production Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- "SELF-HEALING" API FUNCTION ---
@st.cache_data(show_spinner=False)
def query_text_api_robust(payload, model_name):
    """
    Tries multiple URLs automatically to find where the model is hiding.
    """
    # The list of possible addresses where the model might live
    urls_to_try = [
        f"https://router.huggingface.co/hf-inference/models/{model_name}", # New Router
        f"https://api-inference.huggingface.co/models/{model_name}"       # Old Standard
    ]
    
    try:
        hf_token = st.secrets["HF_TOKEN"]
    except:
        return {"error": "⚠️ Token missing. Check .streamlit/secrets.toml"}
    
    headers = {"Authorization": f"Bearer {hf_token}"}
    
    last_error = ""
    
    # Loop through URLs until one works
    for url in urls_to_try:
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            # If successful (200 OK)
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"error": f"API Error (Not JSON): {response.text}"}
            
            # If model is loading (503), wait and return error so user knows to wait
            elif response.status_code == 503:
                return {"error": f"⏳ Model is loading... Please wait 30s and try again."}
            
            # If "Not Found" or "Not Supported", just continue to the next URL
            else:
                last_error = f"Error {response.status_code}: {response.text}"
                continue 
                
        except Exception as e:
            last_error = str(e)
            continue

    # If we tried all URLs and none worked:
    return {"error": f"Failed to connect to model ({model_name}). Details: {last_error}"}

def query_image_api(payload, model_name):
    # Image models usually stay on the standard URL, but we can force one if needed
    API_URL = f"https://api-inference.huggingface.co/models/{model_name}"
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
            with st.spinner("Analyzing..."):
                # 1. Summary (Using Facebook BART - The gold standard for summaries)
                summ_payload = {"inputs": script_input, "parameters": {"max_new_tokens": 150}}
                summ_response = query_text_api_robust(summ_payload, "facebook/bart-large-cnn")
                
                # 2. Logline (Using Microsoft Phi-3 - Very reliable on new Router)
                log_prompt = f"Read this and write a 1-sentence logline: {script_input}"
                log_payload = {"inputs": log_prompt, "parameters": {"max_new_tokens": 60}}
                log_response = query_text_api_robust(log_payload, "microsoft/Phi-3-mini-4k-instruct")

                # Handle Summary Response
                if isinstance(summ_response, list):
                    st.session_state.summary_result = summ_response[0].get('summary_text', 'Error')
                elif isinstance(summ_response, dict) and "error" in summ_response:
                    st.error(f"Summary Error: {summ_response['error']}")

                # Handle Logline Response
                if isinstance(log_response, list):
                    full_text = log_response[0].get('generated_text', '')
                    st.session_state.logline_result = full_text.replace(log_prompt, "").strip()
                elif isinstance(log_response, dict) and "error" in log_response:
                    st.error(f"Logline Error: {log_response['error']}")

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
            # Using Stable Diffusion v1.5
            image_bytes = query_image_api({"inputs": full_prompt}, "runwayml/stable-diffusion-v1-5")
            
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
            # Prompt engineered for Phi-3
            script_prompt = f"""<|user|>
            Write a movie scene in standard screenplay format about:
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
            
            # Using Microsoft Phi-3 (Reliable)
            response = query_text_api_robust(payload, "microsoft/Phi-3-mini-4k-instruct")
            
            if isinstance(response, list):
                generated = response[0].get('generated_text', '')
                st.session_state.generated_script = generated
                st.success("Done!")
            elif isinstance(response, dict) and "error" in response:
                st.error(response["error"])

    if st.session_state.generated_script:
        st.text_area("Script:", value=st.session_state.generated_script, height=600)
