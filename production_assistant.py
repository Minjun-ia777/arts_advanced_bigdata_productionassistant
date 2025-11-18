import streamlit as st
import requests
import io
from PIL import Image

st.set_page_config(page_title="AI Pre-Production Assistant", page_icon="🎬", layout="wide")

# --- LESSON 2: CACHING ---
# We use @st.cache_data so we don't call the API unnecessarily if the input hasn't changed.
# We DO NOT cache the image generation because we might want different results for the same prompt.
@st.cache_data(show_spinner=False)
def query_text_api(payload, model_name):
    """Dedicated function for Text models with caching"""
    API_URL = f"https://api-inference.huggingface.co/models/{model_name}"
    try:
        hf_token = st.secrets["HF_TOKEN"]
    except:
        return {"error": "Token not found"}
        
    headers = {"Authorization": f"Bearer {hf_token}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def query_image_api(payload, model_name):
    """Dedicated function for Image models (No caching to allow variations)"""
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

# --- MAIN APP ---
st.title("🎬 AI Pre-Production Assistant")
st.markdown("### Professional Film Development Tool")

# --- LESSON 3: SESSION STATE ---
# Initialize session state to store results so they don't disappear
if 'summary_result' not in st.session_state:
    st.session_state.summary_result = ""
if 'logline_result' not in st.session_state:
    st.session_state.logline_result = ""

tab1, tab2 = st.tabs(["📝 AI Script Doctor", "🎨 AI Storyboarder"])

# --- TAB 1 ---
with tab1:
    col_input, col_output = st.columns([1, 1])
    
    with col_input:
        st.subheader("Script Input")
        script_input = st.text_area("Paste Scene:", height=300, placeholder="INT. ROOM - DAY...")
        
        if st.button("Analyze Script"):
            if script_input:
                with st.spinner("Analyzing..."):
                    # --- LESSON 1: TOKEN PARAMETERS ---
                    # 1. Summarization
                    summ_payload = {
                        "inputs": script_input,
                        "parameters": {"max_new_tokens": 150, "min_length": 30}
                    }
                    summ_response = query_text_api(summ_payload, "facebook/bart-large-cnn")
                    
                    # 2. Logline Generation (Using Mistral)
                    log_prompt = f"Write a one-sentence logline for this movie scene:\n\n{script_input}"
                    log_payload = {
                        "inputs": log_prompt,
                        "parameters": {"max_new_tokens": 50, "temperature": 0.8}
                    }
                    log_response = query_text_api(log_payload, "mistralai/Mistral-7B-Instruct-v0.2")

                    # Save to session state
                    if isinstance(summ_response, list):
                        st.session_state.summary_result = summ_response[0].get('summary_text', 'Error')
                    
                    if isinstance(log_response, list):
                         # Cleaning up Mistral output
                        full_text = log_response[0].get('generated_text', '')
                        st.session_state.logline_result = full_text.replace(log_prompt, "").strip()

    with col_output:
        st.subheader("Analysis Results")
        # Display results from Session State (Memory)
        if st.session_state.summary_result:
            st.info(f"**Summary:** {st.session_state.summary_result}")
        
        if st.session_state.logline_result:
            st.success(f"**Logline:** {st.session_state.logline_result}")

# --- TAB 2 ---
with tab2:
    st.subheader("Visual Development")
    sb_prompt = st.text_input("Scene Description:", value=st.session_state.logline_result)
    sb_style = st.selectbox("Style:", ["Cinematic", "Anime", "Cyberpunk", "Watercolor"])
    
    if st.button("Generate Storyboard"):
        with st.spinner("Rendering..."):
            full_prompt = f"{sb_style} style, {sb_prompt}, detailed, 8k"
            image_bytes = query_image_api({"inputs": full_prompt}, "runwayml/stable-diffusion-v1-5")
            
            if image_bytes:
                image = Image.open(io.BytesIO(image_bytes))
                st.image(image, caption=full_prompt, use_container_width=True)
