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
def query_text_api(payload, model_name):
    # Standard HF Inference URL
    API_URL = f"https://api-inference.huggingface.co/models/{model_name}"
    
    try:
        hf_token = st.secrets["HF_TOKEN"]
    except:
        return {"error": "⚠️ Token missing. Check .streamlit/secrets.toml"}
    
    headers = {"Authorization": f"Bearer {hf_token}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        
        # DEBUG: Check if response is JSON
        try:
            return response.json()
        except json.JSONDecodeError:
            # If not JSON, return the raw text so we can see the error
            return {"error": f"API Error: {response.text}"}
            
    except Exception as e:
        return {"error": f"Connection error: {str(e)}"}

def query_image_api(payload, model_name):
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
    
    **Troubleshooting:**
    If you see "Model Loading", wait 30s and try again. 
    Free models sometimes sleep!
    """)
    st.divider()
    st.caption("Final Project 2025")

# --- HEADER ---
st.title("🎬 AI Pre-Production Assistant")

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
    st.subheader("Script Analysis")
    col_input, col_output = st.columns([1, 1])
    
    with col_input:
        script_input = st.text_area("Paste Scene:", height=300, placeholder="INT. ROOM - NIGHT...")
        
        if st.button("Analyze Script", type="primary"):
            with st.spinner("Analyzing..."):
                # 1. Summary (BART is very stable)
                summ_payload = {"inputs": script_input, "parameters": {"max_new_tokens": 100}}
                summ_response = query_text_api(summ_payload, "facebook/bart-large-cnn")
                
                # 2. Logline (Using Zephyr instead of Mistral)
                log_prompt = f"Summarize this movie scene into a one-sentence logline:\n{script_input}"
                log_payload = {"inputs": log_prompt, "parameters": {"max_new_tokens": 50}}
                log_response = query_text_api(log_payload, "HuggingFaceH4/zephyr-7b-beta")

                if isinstance(summ_response, list):
                    st.session_state.summary_result = summ_response[0].get('summary_text', 'Error')
                elif "error" in summ_response:
                    st.error(summ_response["error"])

                if isinstance(log_response, list):
                    st.session_state.logline_result = log_response[0].get('generated_text', '').replace(log_prompt, "").strip()

    with col_output:
        if st.session_state.summary_result:
            st.success(f"**Summary:** {st.session_state.summary_result}")
        if st.session_state.logline_result:
            st.info(f"**Logline:** {st.session_state.logline_result}")

# ==========================================
# TAB 2: STORYBOARDER
# ==========================================
with tab2:
    st.subheader("Visual Development")
    sb_prompt = st.text_input("Shot Description:", value=st.session_state.logline_result)
    sb_style = st.selectbox("Style:", ["Cinematic", "Anime", "Cyberpunk", "Oil Painting"])
    
    if st.button("Generate Image", type="primary"):
        with st.spinner("Generating..."):
            full_prompt = f"{sb_style} style, {sb_prompt}, 8k masterpiece"
            image_bytes = query_image_api({"inputs": full_prompt}, "runwayml/stable-diffusion-v1-5")
            
            if image_bytes:
                try:
                    image = Image.open(io.BytesIO(image_bytes))
                    st.image(image, caption=sb_style, use_container_width=True)
                except:
                    st.error("Model is loading. Try again in 30 seconds.")
            else:
                st.error("Image generation failed.")

# ==========================================
# TAB 3: STORY GENERATOR (Fixed Model)
# ==========================================
with tab3:
    st.subheader("AI Screenwriter")
    c1, c2 = st.columns(2)
    with c1:
        genre = st.selectbox("Genre", ["Sci-Fi", "Horror", "Comedy", "Western"])
        character = st.text_input("Protagonist", placeholder="e.g. A robot")
    with c2:
        setting = st.text_input("Setting", placeholder="e.g. Mars")
        conflict = st.text_input("Conflict", placeholder="e.g. Out of oxygen")

    if st.button("Write Scene", type="primary"):
        with st.spinner("Writing script..."):
            # Prompt
            script_prompt = f"""<|system|>
            You are a screenwriter. Write a scene script.
            <|user|>
            Write a scene about a {character} in {setting}. 
            Genre: {genre}. Conflict: {conflict}.
            Format: Standard Screenplay.
            <|assistant|>"""
            
            payload = {
                "inputs": script_prompt,
                "parameters": {
                    "max_new_tokens": 500,
                    "temperature": 0.8,
                    "return_full_text": False
                }
            }
            
            # SWITCHED MODEL: Zephyr-7b-beta (More reliable than Mistral v0.2 on free tier)
            response = query_text_api(payload, "HuggingFaceH4/zephyr-7b-beta")
            
            if isinstance(response, list):
                st.session_state.generated_script = response[0].get('generated_text', '')
                st.success("Done!")
            elif "error" in response:
                st.error(response["error"])

    if st.session_state.generated_script:
        st.text_area("Script:", value=st.session_state.generated_script, height=400)
