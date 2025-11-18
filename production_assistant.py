import streamlit as st
import requests
import io
from PIL import Image

# --- Page Configuration ---
st.set_page_config(page_title="AI Pre-Production Assistant", page_icon="🎬", layout="centered")

# --- Function to Query Hugging Face API ---
def query_api(payload, model_name, api_type="text"):
    """
    Sends a request to the Hugging Face Inference API.
    """
    API_URL = f"https://api-inference.huggingface.co/models/{model_name}"
    
    # Get the token from Streamlit Secrets
    # If running locally, you can hardcode it temporarily, but for deployment use Secrets!
    try:
        hf_token = st.secrets["HF_TOKEN"]
    except:
        st.error("Error: HF_TOKEN not found in Secrets. Please set it in Streamlit Cloud settings.")
        return None

    headers = {"Authorization": f"Bearer {hf_token}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

    # Handle Model Loading (Common in free tier)
    if response.status_code == 503:
        st.warning(f"Model {model_name} is currently loading. Please wait 30 seconds and try again.")
        return None
        
    if response.status_code != 200:
        st.error(f"API Error {response.status_code}: {response.text}")
        return None

    # Return appropriate data type
    if api_type == "image":
        return response.content # Raw bytes for images
    else:
        return response.json()  # JSON for text

# --- Main App UI ---
st.title("🎬 AI Pre-Production Assistant")
st.markdown("### Your Co-Developer for Scripts & Storyboards")
st.info("This app uses free AI models to help you analyze scripts and visualize scenes.")

# Create Tabs
tab1, tab2 = st.tabs(["📝 AI Script Doctor", "🎨 AI Storyboarder"])

# --- TAB 1: SCRIPT DOCTOR ---
with tab1:
    st.header("Script Analysis")
    script_input = st.text_area("Paste a scene from your script here:", height=250, 
                               placeholder="INT. DINER - NIGHT\nA rainy night. JOHN sits alone...")

    if script_input:
        col1, col2 = st.columns(2)
        
        # 1. Summarization
        with col1:
            if st.button("Summarize Scene"):
                with st.spinner("Reading script..."):
                    payload = {"inputs": script_input}
                    # Model: Facebook BART (Great for summarization)
                    summary_data = query_api(payload, "facebook/bart-large-cnn", "text")
                    
                    if summary_data and isinstance(summary_data, list):
                        summary_text = summary_data[0].get('summary_text', 'Error parsing summary.')
                        st.success(f"**Summary:** {summary_text}")

        # 2. Emotion Analysis
        with col2:
            if st.button("Analyze Mood"):
                with st.spinner("Analyzing emotions..."):
                    payload = {"inputs": script_input}
                    # Model: Roberta Emotion (Great for emotion detection)
                    emotion_data = query_api(payload, "j-hartmann/emotion-english-distilroberta-base", "text")
                    
                    if emotion_data:
                        # The API returns a list of lists, we flatten it
                        emotions = emotion_data[0] 
                        # Find the highest scoring emotion
                        top_emotion = max(emotions, key=lambda x: x['score'])
                        st.success(f"**Dominant Mood:** {top_emotion['label'].upper()} ({int(top_emotion['score']*100)}%)")

# --- TAB 2: STORYBOARDER ---
with tab2:
    st.header("Storyboard Generator")
    st.markdown("Turn a description into a storyboard frame.")
    
    # User Inputs
    sb_prompt = st.text_input("Scene Description:", placeholder="A futuristic city with neon lights, cinematic lighting")
    sb_style = st.selectbox("Select Style:", ["Cinematic", "Anime", "Sketch", "Cyberpunk", "Oil Painting"])
    
    if st.button("Generate Image"):
        if not sb_prompt:
            st.warning("Please enter a description first.")
        else:
            with st.spinner("Drawing your storyboard... (This might take a minute)"):
                # Combine style and prompt for better results
                final_prompt = f"{sb_style} style, {sb_prompt}, high quality, detailed"
                
                payload = {"inputs": final_prompt}
                # Model: Stable Diffusion v1.5 (Best general purpose free model)
                image_bytes = query_api(payload, "runwayml/stable-diffusion-v1-5", "image")
                
                if image_bytes:
                    image = Image.open(io.BytesIO(image_bytes))
                    st.image(image, caption=f"Generated Storyboard: {sb_prompt}")
