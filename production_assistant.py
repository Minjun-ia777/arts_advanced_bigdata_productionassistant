import streamlit as st
from huggingface_hub import InferenceClient
import io
from PIL import Image
from openai import OpenAI
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI Pre-Production Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONFIGURATION & LIMITS ---
FREE_TIER_DAILY_LIMIT = 20  # Simulate a limit for free users
if 'usage_count' not in st.session_state:
    st.session_state.usage_count = 0

# --- API SETUP ---
# 1. Load Hugging Face Token (Essential for Free Tier)
try:
    hf_token = st.secrets["HF_TOKEN"]
except:
    st.error("⚠️ HF_TOKEN not found in Secrets. The app will not work.")
    st.stop()

# --- HELPER FUNCTIONS ---

def check_usage_limit():
    """Tracks usage and displays warnings based on the % used."""
    # Only limit usage if NOT using OpenAI (Paid users shouldn't have app limits)
    if not st.session_state.get('openai_api_key'):
        st.session_state.usage_count += 1
        usage = st.session_state.usage_count
        percent = usage / FREE_TIER_DAILY_LIMIT
        
        if percent >= 1.0:
            st.error(f"❌ Daily Limit Reached ({usage}/{FREE_TIER_DAILY_LIMIT}). Please wait 24 hours or add an OpenAI Key.")
            return False
        elif percent >= 0.75:
            st.warning(f"⚠️ Warning: You have used 75% of your free daily quota ({usage}/{FREE_TIER_DAILY_LIMIT}).")
        elif percent >= 0.50:
            st.info(f"ℹ️ Notice: You have used 50% of your free daily quota ({usage}/{FREE_TIER_DAILY_LIMIT}).")
            
    return True

@st.cache_data(show_spinner=False)
def get_llm_response(prompt, max_tokens=700, provider="Free (Hugging Face)"):
    
    # OPTION A: PAID (OpenAI)
    if provider == "Premium (OpenAI)" and st.session_state.get('openai_api_key'):
        try:
            client = OpenAI(api_key=st.session_state.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini", # Cost effective and smart
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"OpenAI Error: {str(e)}"

    # OPTION B: FREE (Your Existing Qwen Logic)
    else:
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
            return f"Hugging Face Error: {str(e)}"

def get_image_response(prompt):
    """
    Keeps your working SDXL logic.
    """
    repo_id = "stabilityai/stable-diffusion-xl-base-1.0"
    try:
        client = InferenceClient(token=hf_token)
        image = client.text_to_image(prompt, model=repo_id) 
        return image
    except Exception as e:
        if "model is currently loading" in str(e).lower():
            return "loading_error"
        elif "rate limit" in str(e).lower():
            return "busy_error"
        return None

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2503/2503508.png", width=50)
    st.title("Settings")
    
    # 1. API Selection
    st.subheader("⚙️ AI Engine")
    api_choice = st.radio("Choose Provider:", ["Free (Hugging Face)", "Premium (OpenAI)"])
    
    if api_choice == "Premium (OpenAI)":
        openai_key = st.text_input("Enter OpenAI API Key:", type="password", help="Sk-...")
        if openai_key:
            st.session_state.openai_api_key = openai_key
            st.success("✅ OpenAI Key Saved")
        else:
            st.warning("⚠️ Enter key to unlock Premium")
    else:
        st.session_state.openai_api_key = None
        st.info("ℹ️ Using Free Tier. Speed and daily usage are limited.")

    # 2. Usage Monitor (Visual)
    if api_choice == "Free (Hugging Face)":
        st.divider()
        st.subheader("📊 Free Quota")
        u_count = st.session_state.usage_count
        st.progress(min(u_count / FREE_TIER_DAILY_LIMIT, 1.0))
        st.caption(f"Used: {u_count} / {FREE_TIER_DAILY_LIMIT} requests")

    st.divider()
    st.markdown("[View Source Code](https://github.com/your-repo) | Final Project 2025")

# --- MAIN HEADER ---
st.title("🎬 AI Pre-Production Assistant")
st.markdown("##### The professional co-pilot for filmmakers.")

# --- SESSION STATE INITIALIZATION ---
if 'summary_result' not in st.session_state: st.session_state.summary_result = ""
if 'logline_result' not in st.session_state: st.session_state.logline_result = ""
if 'generated_script' not in st.session_state: st.session_state.generated_script = ""

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📝 Script Doctor", "🎨 Storyboarder", "✨ Story Generator"])

# ==========================================
# TAB 1: SCRIPT DOCTOR
# ==========================================
with tab1:
    st.markdown("### 🩺 Analyze & Fix Scripts")
    st.caption("Paste a rough scene to get a professional logline and summary.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        script_input = st.text_area(
            "Paste Scene Text", 
            height=300, 
            placeholder="INT. COFFEE SHOP - DAY\n\nJOHN (30s) sits nervously...",
            help="Copy and paste your script scene here."
        )
    with col2:
        st.markdown("**Analysis Options**")
        analysis_tone = st.selectbox("Desired Logline Tone", ["Professional", "Mysterious", "Comedic", "Dramatic"], help="How should the logline sound?")
        
        if st.button("🚀 Analyze Script", type="primary", use_container_width=True):
            if not check_usage_limit(): st.stop() # Check Limit
            
            if not script_input:
                st.warning("Please paste text first.")
            else:
                with st.spinner(f"Analyzing with {api_choice}..."):
                    # 1. Summary
                    summ_prompt = f"Summarize this movie scene in 2 bullet points:\n\n{script_input}"
                    summ_response = get_llm_response(summ_prompt, 200, api_choice)
                    
                    # 2. Logline
                    log_prompt = f"Write a {analysis_tone} one-sentence logline/pitch for this scene:\n\n{script_input}"
                    log_response = get_llm_response(log_prompt, 100, api_choice)

                    st.session_state.summary_result = summ_response
                    st.session_state.logline_result = log_response

    # OUTPUT AREA
    if st.session_state.summary_result:
        st.divider()
        c_out1, c_out2 = st.columns(2)
        with c_out1:
            st.subheader("📝 Summary")
            st.success(st.session_state.summary_result)
        with c_out2:
            st.subheader("🎬 Logline")
            st.info(st.session_state.logline_result)

# ==========================================
# TAB 2: STORYBOARDER
# ==========================================
with tab2:
    st.markdown("### 🖌️ Visual Development")
    st.caption("Turn text into concept art using Stable Diffusion.")
    
    # Use logline as default prompt
    default_prompt = st.session_state.logline_result if "Error" not in st.session_state.logline_result else ""
    
    c1, c2 = st.columns([3, 1])
    with c1:
        sb_prompt = st.text_input("Shot Description", value=default_prompt, placeholder="A wide shot of...", help="Describe the image details.")
    with c2:
        sb_style = st.selectbox("Art Style", ["Cinematic", "Anime", "Cyberpunk", "Oil Painting", "Noir", "Watercolor"], help="Visual aesthetic.")
    
    # New Tools for better prompting
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        lighting = st.selectbox("Lighting", ["Natural", "Neon", "Golden Hour", "Dark/Moody"], help="Lighting condition.")
    with cc2:
        angle = st.selectbox("Camera Angle", ["Wide Shot", "Close Up", "Low Angle", "Overhead"], help="Camera placement.")
    with cc3:
        lens = st.selectbox("Lens Type", ["35mm", "85mm Portrait", "Fisheye", "Anamorphic"], help="Lens distortion.")

    if st.button("🎨 Generate Image", type="primary"):
        if not check_usage_limit(): st.stop() # Check Limit
        
        if not sb_prompt:
            st.warning("Please describe the shot first.")
        else:
            with st.spinner("Rendering... (Free tier may take 30-60s)"):
                # Construct a professional prompt using all tools
                full_prompt = f"{sb_style} style, {angle}, {sb_prompt}, {lighting} lighting, shot on {lens}, 8k masterpiece, detailed"
                
                image = get_image_response(full_prompt)
                
                if image == "loading_error":
                    st.warning("⏳ Image model is loading. Please wait 30-60 seconds and try again.")
                elif image == "busy_error":
                    st.warning("⚠️ Image model is busy. Please try again in a moment.")
                elif image:
                    st.image(image, caption=f"{sb_style} | {angle}", use_container_width=True)
                else:
                    st.error("Image generation failed. Try simplifying your prompt.")

# ==========================================
# TAB 3: STORY GENERATOR
# ==========================================
with tab3:
    st.markdown("### 🧬 AI Screenwriter")
    st.caption("Create a formatted script from scratch.")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        genre = st.selectbox("Genre", ["Sci-Fi", "Horror", "Comedy", "Western", "Thriller"], help="Movie genre")
        time_period = st.selectbox("Time Period", ["Modern Day", "Future 2099", "Medieval", "1980s", "Victorian Era"], help="When does it take place?")
    with c2:
        character = st.text_input("Protagonist", placeholder="e.g. A retired spy", help="Main character description")
        setting = st.text_input("Setting", placeholder="e.g. An abandoned bunker", help="Location")
    with c3:
        conflict = st.text_input("Conflict", placeholder="e.g. The bomb is ticking", help="What is the problem?")
        tone = st.selectbox("Script Tone", ["Serious", "Funny", "Dark", "Fast-paced"], help="Mood of the writing")

    if st.button("✨ Write Scene", type="primary", use_container_width=True):
        if not check_usage_limit(): st.stop() # Check Limit
        
        if not character or not setting:
            st.warning("Please provide at least a Character and a Setting.")
        else:
            with st.spinner(f"Writing script with {api_choice}..."):
                script_prompt = f"""
                You are a professional screenwriter. Write a movie scene in standard screenplay format (Courier font style).
                
                Parameters:
                - Genre: {genre}
                - Time Period: {time_period}
                - Tone: {tone}
                - Character: {character}
                - Setting: {setting}
                - Conflict: {conflict}
                
                Ensure proper formatting with Scene Headings (INT/EXT), Action Lines, and Dialogue. 
                Output ONLY the script content.
                """
                
                response = get_llm_response(script_prompt, 1000, api_choice)
                st.session_state.generated_script = response

    # OUTPUT AREA - Styled to look like a script
    if st.session_state.generated_script:
        st.divider()
        st.subheader("📜 Final Script")
        
        # Display as a code block for clear formatting
        st.code(st.session_state.generated_script, language="plaintext")
        
        # Add a download button
        st.download_button(
            label="Download Script (.txt)",
            data=st.session_state.generated_script,
            file_name="generated_script.txt",
            mime="text/plain"
        )
