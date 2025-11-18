import streamlit as st
from huggingface_hub import InferenceClient
import io
from PIL import Image

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI Pre-Production Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- API SETUP ---
try:
    hf_token = st.secrets["HF_TOKEN"]
except:
    st.error("⚠️ HF_TOKEN not found in Secrets. The app will not work.")
    st.stop()

# --- API FUNCTIONS ---

@st.cache_data(show_spinner=False)
def get_llm_response(prompt, max_tokens=500):
    """
    Model: Qwen2.5-7B-Instruct
    """
    repo_id = "Qwen/Qwen2.5-7B-Instruct" 
    
    try:
        client = InferenceClient(token=hf_token)
        
        messages = [{"role": "user", "content": prompt}]
        
        response = client.chat_completion(
            model=repo_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error: {str(e)}"

def get_image_response(prompt):
    """
    Model: stabilityai/stable-diffusion-xl-base-1.0 (More robust image model)
    """
    # SWITCHING TO STABLE DIFFUSION XL (SDXL) for better results and stability
    repo_id = "stabilityai/stable-diffusion-xl-base-1.0"
    
    try:
        client = InferenceClient(token=hf_token)
        # Pass the model argument explicitly to text_to_image
        image = client.text_to_image(prompt, model=repo_id) 
        return image
    except Exception as e:
        # Catch specific errors for better feedback
        if "model is currently loading" in str(e).lower():
            return "loading_error"
        elif "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
            return "busy_error"
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2503/2503508.png", width=50)
    st.title("User Guide")
    st.markdown("""
    **Status:** 🟢 System Ready
    
    **1. 🔑 Setup**
    Ensure `HF_TOKEN` is in Secrets.
    
    **2. ⚠️ Loading Times**
    If a model is "cold," it might take 60s to load. 
    This is normal for the free tier.
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
                    # 1. Summary
                    summ_prompt = f"Summarize this movie scene in 2 sentences:\n\n{script_input}"
                    summ_response = get_llm_response(summ_prompt, max_tokens=150)
                    
                    # 2. Logline
                    log_prompt = f"Write a one-sentence logline/pitch for this scene:\n\n{script_input}"
                    log_response = get_llm_response(log_prompt, max_tokens=60)

                    # Save to session
                    st.session_state.summary_result = summ_response
                    st.session_state.logline_result = log_response

    with col_output:
        st.markdown("#### Report")
        if st.session_state.summary_result:
            if "Error" in st.session_state.summary_result:
                st.error(st.session_state.summary_result)
            else:
                st.success(f"**Summary:**\n{st.session_state.summary_result}")
                
        if st.session_state.logline_result:
            if "Error" not in st.session_state.logline_result:
                st.info(f"**Logline:**\n{st.session_state.logline_result}")

# ==========================================
# TAB 2: STORYBOARDER
# ==========================================
with tab2:
    st.markdown("### 🖌️ Visuals")
    
    # Use logline as default prompt
    default_prompt = st.session_state.logline_result if "Error" not in st.session_state.logline_result else ""
    
    sb_prompt = st.text_input("Shot Description:", value=default_prompt)
    sb_style = st.selectbox("Style:", ["Cinematic", "Anime", "Cyberpunk", "Oil Painting"])
    
    if st.button("🎨 Generate Image", type="primary"):
        if not sb_prompt:
            st.warning("Please describe the shot first.")
        else:
            with st.spinner("Rendering high-resolution frame... (This might take 30-60s the first time!)"):
                full_prompt = f"{sb_style} style, {sb_prompt}, 8k masterpiece, highly detailed, dramatic lighting"
                image = get_image_response(full_prompt)
                
                if image == "loading_error":
                    st.warning("⏳ Image model is loading. Please wait 30-60 seconds and try again.")
                elif image == "busy_error":
                    st.warning("⚠️ Image model is busy. Please try again in a moment.")
                elif image:
                    st.image(image, caption=sb_style, use_container_width=True)
                else:
                    st.error("Image generation failed for an unknown reason. Try simplifying your prompt.")

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
        if not character or not setting:
            st.warning("Please provide at least a Character and a Setting.")
        else:
            with st.spinner("Writing script..."):
                script_prompt = f"""
                You are a professional screenwriter. Write a movie scene in standard screenplay format.
                
                Details:
                Genre: {genre}
                Character: {character}
                Setting: {setting}
                Conflict: {conflict}
                
                Output ONLY the script.
                """
                
                response = get_llm_response(script_prompt, max_tokens=700)
                
                if "Error" in response:
                    st.error(response)
                else:
                    st.session_state.generated_script = response

    if st.session_state.generated_script:
        st.text_area("Script:", value=st.session_state.generated_script, height=600)
