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
# 1. Text Function
@st.cache_data(show_spinner=False)
def query_text_api(payload, model_name):
    # BACK TO STANDARD URL (Most stable)
    API_URL = f"https://api-inference.huggingface.co/models/{model_name}"
    
    try:
        hf_token = st.secrets["HF_TOKEN"]
    except:
        return {"error": "⚠️ Token missing. Please check your Streamlit Secrets."}
    
    headers = {"Authorization": f"Bearer {hf_token}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        
        # CHECK: Did we get a JSON response?
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"error": f"API Error: {response.text}"}
            
    except Exception as e:
        return {"error": f"Connection error: {str(e)}"}

# 2. Image Function
def query_image_api(payload, model_name):
    # BACK TO STANDARD URL
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

# --- SIDEBAR INSTRUCTIONS ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2503/2503508.png", width=50)
    st.title("User Guide")
    
    st.markdown("""
    **Welcome to your AI Co-Producer.**
    
    **1. 🔑 Setup**
    Ensure your Hugging Face Token is set in secrets.
    
    **2. 🛠 Select a Tool**
    * **Script Doctor:** Fix and analyze existing text.
    * **Storyboarder:** Create visuals.
    * **Story Generator:** Write new ideas from scratch.
    
    **3. ⚠️ Troubleshooting**
    If you see "Model Loading," wait 30 seconds and try again.
    """)
    
    st.divider()
    st.caption("Final Project 2025")

# --- MAIN HEADER ---
st.title("🎬 AI Pre-Production Assistant")
st.markdown("##### Transform your film ideas into scripts and storyboards instantly.")

# --- INITIALIZE SESSION STATE ---
if 'summary_result' not in st.session_state: st.session_state.summary_result = ""
if 'logline_result' not in st.session_state: st.session_state.logline_result = ""
if 'generated_script' not in st.session_state: st.session_state.generated_script = ""

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📝 Script Doctor", "🎨 Storyboarder", "✨ Story Generator"])

# ==========================================
# TAB 1: SCRIPT DOCTOR
# ==========================================
with tab1:
    st.markdown("### 🩺 Script Analysis & Repair")
    
    with st.expander("ℹ️ Instructions: How to use the Script Doctor"):
        st.markdown("Paste a scene text below. The AI will summarize it and generate a professional logline.")

    col_input, col_output = st.columns([1, 1])
    
    with col_input:
        script_input = st.text_area(
            "Input Scene Text", 
            height=300, 
            placeholder="INT. SPACE STATION - NIGHT\n\nCOMMANDER ZARA (40s) looks at the red flashing light...",
            help="Paste a scene here. Aim for 200-500 words."
        )
        
        if st.button("🚀 Analyze Script", type="primary"):
            if not script_input:
                st.warning("⚠️ Please paste a script scene first.")
            else:
                with st.spinner("Reading your script..."):
                    # 1. Summary (BART Model - Very Stable)
                    summ_payload = {"inputs": script_input, "parameters": {"max_new_tokens": 150}}
                    summ_response = query_text_api(summ_payload, "facebook/bart-large-cnn")
                    
                    # 2. Logline (SWITCHED MODEL to Zephyr-7b-beta)
                    log_prompt = f"Summarize this movie scene into a one-sentence logline:\n{script_input}"
                    log_payload = {"inputs": log_prompt, "parameters": {"max_new_tokens": 50}}
                    log_response = query_text_api(log_payload, "HuggingFaceH4/zephyr-7b-beta")

                    # Handle responses
                    if isinstance(summ_response, list):
                        st.session_state.summary_result = summ_response[0].get('summary_text', 'Error')
                    elif isinstance(summ_response, dict) and "error" in summ_response:
                        st.error(f"Summary Error: {summ_response['error']}")

                    if isinstance(log_response, list):
                        # Zephyr returns text differently, usually in 'generated_text'
                        full_text = log_response[0].get('generated_text', '')
                        # Clean up the prompt from the answer
                        clean_text = full_text.replace(log_prompt, "").strip()
                        st.session_state.logline_result = clean_text
                    elif isinstance(log_response, dict) and "error" in log_response:
                        st.error(f"Logline Error: {log_response['error']}")

    with col_output:
        st.markdown("#### Analysis Report")
        if st.session_state.summary_result:
            st.success(f"**📝 Executive Summary:**\n\n{st.session_state.summary_result}")
        else:
            st.info("Waiting for input...")
            
        if st.session_state.logline_result:
            st.warning(f"**🎬 Logline / Pitch:**\n\n{st.session_state.logline_result}")

# ==========================================
# TAB 2: STORYBOARDER
# ==========================================
with tab2:
    st.markdown("### 🖌️ Visual Development")
    
    with st.expander("ℹ️ Instructions: How to get the best images"):
        st.markdown("Describe the shot using lighting (e.g., 'neon', 'sunset') and style keywords.")
    
    # Use logline from Tab 1 if available
    default_val = st.session_state.logline_result if st.session_state.logline_result else ""
    
    sb_prompt = st.text_input(
        "Describe the shot:", 
        value=default_val, 
        placeholder="A wide shot of a futuristic city at sunset...",
        help="Type a visual description of the scene you want to see."
    )
    
    sb_style = st.selectbox(
        "Cinematography Style:", 
        ["Cinematic Film", "Anime", "Cyberpunk", "Oil Painting", "Black & White Noir", "3D Render"]
    )
    
    if st.button("🎨 Generate Storyboard", type="primary"):
        if not sb_prompt:
            st.warning("⚠️ Please describe the scene first.")
        else:
            with st.spinner("Rendering high-resolution frame..."):
                full_prompt = f"{sb_style} style, {sb_prompt}, 8k, highly detailed, dramatic lighting, masterpiece"
                image_bytes = query_image_api({"inputs": full_prompt}, "runwayml/stable-diffusion-v1-5")
                
                if image_bytes:
                    try:
                        image = Image.open(io.BytesIO(image_bytes))
                        st.image(image, caption=f"Generated in {sb_style} style", use_container_width=True)
                    except:
                        st.error("Error: The model is loading or the image failed to decode. Try again in 30 seconds.")
                else:
                    st.error("Error generating image. Check your Token.")

# ==========================================
# TAB 3: STORY GENERATOR
# ==========================================
with tab3:
    st.markdown("### 🧬 AI Screenwriter")
    
    with st.expander("ℹ️ Instructions: Create a scene from scratch"):
        st.markdown("Define the ingredients below. The AI will write a script format scene for you.")
        
    c1, c2 = st.columns(2)
    with c1:
        genre = st.selectbox("Genre", ["Sci-Fi", "Horror", "Romance", "Thriller", "Comedy", "Western"])
        character = st.text_input("Protagonist", placeholder="e.g. A retired spy", help="Who is the main character?")
    with c2:
        setting = st.text_input("Setting", placeholder="e.g. An underground bunker", help="Where does this scene happen?")
        conflict = st.text_input("The Conflict", placeholder="e.g. The door won't open", help="What is the problem to solve?")

    if st.button("✨ Write Scene", type="primary"):
        if not character or not setting:
            st.warning("⚠️ Please provide at least a Character and a Setting.")
        else:
            with st.spinner("Writing screenplay... (This may take 60 seconds)"):
                # NEW: Prompt specifically for Zephyr
                script_prompt = f"""<|system|>
                You are a professional screenwriter. Write a movie scene in standard screenplay format.
                <|user|>
                Write a scene with the following details:
                Genre: {genre}
                Characters: {character}
                Setting: {setting}
                Plot Conflict: {conflict}
                
                Include Scene Heading, Action Lines, and Dialogue.
                <|assistant|>"""
                
                payload = {
                    "inputs": script_prompt,
                    "parameters": {
                        "max_new_tokens": 500,
                        "temperature": 0.8,
                        "return_full_text": False
                    }
                }
                
                # SWITCHED MODEL: Zephyr-7b-beta (Free and supported)
                response = query_text_api(payload, "HuggingFaceH4/zephyr-7b-beta")
                
                # Robust Error Handling
                if isinstance(response, list):
                    generated_text = response[0].get('generated_text', '')
                    st.session_state.generated_script = generated_text
                    st.success("Script generated successfully!")
                elif isinstance(response, dict) and "error" in response:
                    st.error(f"AI Error: {response['error']}")
                    if "loading" in response['error'].lower():
                        st.warning("⏳ Model is loading. Please wait 1 minute and try again.")
                else:
                    st.error("Unknown error occurred.")
    
    st.divider()
    
    if st.session_state.generated_script:
        st.markdown("#### 📜 Final Script")
        st.text_area("Copy your script:", value=st.session_state.generated_script, height=600)
