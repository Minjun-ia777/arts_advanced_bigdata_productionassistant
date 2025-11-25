import streamlit as st
from huggingface_hub import InferenceClient
import io
from PIL import Image
from openai import OpenAI
from fpdf import FPDF
import time
import datetime
import uuid

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI Pre-Production Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- GLOBAL USAGE TRACKER (Server-Side Memory) ---
# This dictionary lives on the server and survives browser refreshes
@st.cache_resource
def get_global_usage_db():
    return {}

# --- USER IDENTIFICATION ---
# Check if user has an ID in the URL. If not, give them one.
if "user_id" not in st.query_params:
    new_id = str(uuid.uuid4())[:8] # Generate a short unique ID
    st.query_params["user_id"] = new_id

user_id = st.query_params["user_id"]

# --- CONFIGURATION & LIMITS ---
FREE_TIER_DAILY_LIMIT = 20

# --- API SETUP ---
try:
    hf_token = st.secrets["HF_TOKEN"]
except:
    st.error("⚠️ HF_TOKEN not found in Secrets. The app will not work.")
    st.stop()

# --- HELPER FUNCTIONS ---

def check_usage_limit():
    """
    Checks global server usage for this specific user_id.
    Resets if the day has changed.
    """
    # 1. Bypass for Premium
    if st.session_state.get('openai_api_key'):
        return True

    # 2. Get the Global Database
    db = get_global_usage_db()
    today_str = datetime.date.today().isoformat()

    # 3. Initialize User if new
    if user_id not in db:
        db[user_id] = {"count": 0, "date": today_str}
    
    user_data = db[user_id]

    # 4. Check for Day Reset
    if user_data["date"] != today_str:
        user_data["count"] = 0
        user_data["date"] = today_str
    
    # 5. Check Limits
    usage = user_data["count"]
    percent = usage / FREE_TIER_DAILY_LIMIT

    # We increment here tentatively (visual check), 
    # but the real increment happens inside the button logic usually.
    # To keep it simple, we just return status here.
    
    if usage >= FREE_TIER_DAILY_LIMIT:
        st.error(f"❌ Daily Limit Reached ({usage}/{FREE_TIER_DAILY_LIMIT}). Wait until tomorrow or use Premium.")
        return False
    elif percent >= 0.75:
        st.toast(f"⚠️ Warning: 75% of free quota used ({usage}/{FREE_TIER_DAILY_LIMIT}).", icon="⚠️")
    
    return True

def increment_usage():
    """Call this ONLY when an API call is actually successful"""
    if not st.session_state.get('openai_api_key'):
        db = get_global_usage_db()
        if user_id in db:
            db[user_id]["count"] += 1

def get_current_usage():
    """Helper to get count for UI display"""
    db = get_global_usage_db()
    if user_id in db:
        return db[user_id]["count"]
    return 0

@st.cache_data(show_spinner=False)
def get_llm_response(prompt, max_tokens=700, provider="Free (Hugging Face)"):
    # OPTION A: PAID (OpenAI)
    if provider == "Premium (OpenAI)" and st.session_state.get('openai_api_key'):
        try:
            client = OpenAI(api_key=st.session_state.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"OpenAI Error: {str(e)}"

    # OPTION B: FREE (Qwen 7B)
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
    repo_id = "stabilityai/stable-diffusion-xl-base-1.0"
    try:
        client = InferenceClient(token=hf_token)
        image = client.text_to_image(prompt, model=repo_id) 
        return image
    except Exception as e:
        if "model is currently loading" in str(e).lower(): return "loading_error"
        elif "rate limit" in str(e).lower(): return "busy_error"
        return None

# --- PROMPT MAGIC ---
def optimize_prompt_magic(user_prompt, provider):
    system_prompt = f"""
    Act as an expert Prompt Engineer for Stable Diffusion XL.
    Rewrite the following user description into a high-quality image generation prompt.
    User Description: "{user_prompt}"
    Rules:
    1. Keep the artistic style keywords.
    2. Add specific lighting and camera details.
    3. Return ONLY the raw prompt text.
    """
    return get_llm_response(system_prompt, 150, provider)

# --- STUDIOBINDER HOLLYWOOD PDF FORMAT ---
class ScreenplayPDF(FPDF):
    def header(self):
        self.set_font('Courier', '', 12)
        self.cell(0, 10, f'{self.page_no()}.', 0, 0, 'R')
        self.ln(10)

def create_hollywood_pdf(script_text, logline, image=None, shotlist=None):
    pdf = ScreenplayPDF(format='Letter')
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.set_left_margin(38)
    pdf.set_right_margin(25)
    
    # Logline Section
    pdf.set_font("Courier", 'B', 12)
    pdf.cell(0, 10, "LOGLINE:", ln=True)
    pdf.set_font("Courier", '', 12)
    pdf.multi_cell(0, 6, logline)
    pdf.ln(10)
    
    # Image Section
    if image:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            image.save(tmp_file.name)
            pdf.image(tmp_file.name, x=38, w=140) 
        pdf.ln(15)

    # Script Section
    pdf.set_font("Courier", 'B', 12)
    pdf.cell(0, 10, "SCENE SCRIPT:", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Courier", '', 12)
    lines = script_text.split('\n')
    is_dialogue_block = False
    
    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(5)
            is_dialogue_block = False
            continue
        # Scene Heading (INT./EXT.)
        if line.startswith("INT.") or line.startswith("EXT.") or line.startswith("I/E."):
            pdf.set_font("Courier", 'B', 12)
            pdf.set_x(38)
            pdf.cell(0, 5, line.upper(), ln=True)
            pdf.set_font("Courier", '', 12)
            is_dialogue_block = False
        # Character Name (Centered)
        elif line.isupper() and len(line) < 40 and not is_dialogue_block:
            pdf.set_x(94)
            pdf.cell(0, 5, line, ln=True)
            is_dialogue_block = True
        # Parenthetical
        elif line.startswith("(") and line.endswith(")"):
            pdf.set_x(79)
            pdf.cell(0, 5, line, ln=True)
        # Dialogue
        elif is_dialogue_block:
            pdf.set_x(63)
            pdf.multi_cell(90, 5, line)
        # Transition
        elif line.endswith("TO:") and line.isupper():
            pdf.set_x(152)
            pdf.cell(0, 5, line, ln=True)
        # Action
        else:
            pdf.set_x(38)
            pdf.multi_cell(0, 5, line)
            is_dialogue_block = False

    # Shot List Appendix
    if shotlist:
        pdf.add_page()
        pdf.set_font("Courier", 'B', 12)
        pdf.cell(0, 10, "APPENDIX: SHOT LIST", ln=True)
        pdf.set_font("Courier", '', 10)
        clean_shotlist = shotlist.replace("|", "  ").replace("---", "")
        pdf.multi_cell(0, 5, clean_shotlist)

    return pdf.output(dest="S").encode("latin-1")

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2503/2503508.png", width=50)
    st.title("Settings")
    
    # 1. API Choice
    st.subheader("⚙️ AI Engine")
    api_choice = st.radio("Choose Provider:", ["Free (Hugging Face)", "Premium (OpenAI)"])
    
    if api_choice == "Premium (OpenAI)":
        openai_key = st.text_input("Enter OpenAI Key:", type="password")
        if openai_key:
            st.session_state.openai_api_key = openai_key
            st.success("✅ Premium Active")
    else:
        st.session_state.openai_api_key = None
        st.info("ℹ️ Using Free Tier.")

    st.divider()

    # 2. Memory Settings
    st.subheader("🧠 Memory")
    use_auto_context = st.toggle("Enable Auto-Context", value=True)
    if use_auto_context:
        st.caption("✅ **On:** App remembers your script across tabs.")
    else:
        st.caption("🚫 **Off:** Tabs work independently.")

    st.divider()

    # 3. Usage Monitor
    if api_choice == "Free (Hugging Face)":
        st.subheader("📊 Daily Quota")
        # Get count from Global DB
        u_count = get_current_usage()
        st.progress(min(u_count / FREE_TIER_DAILY_LIMIT, 1.0))
        st.caption(f"{u_count}/{FREE_TIER_DAILY_LIMIT} requests used")

    st.divider()
    
    # 4. Credits
    st.markdown("### ℹ️ About")
    st.caption("Designed & Built for Final Project 2025")
    st.caption("**Powered by:**")
    st.markdown("- Hugging Face Inference")
    st.markdown("- Qwen 2.5 (LLM)")
    st.markdown("- Stable Diffusion XL")

# --- MAIN HEADER ---
st.title("🎬 AI Pre-Production Assistant")

# --- SESSION STATE ---
if 'summary_result' not in st.session_state: st.session_state.summary_result = ""
if 'logline_result' not in st.session_state: st.session_state.logline_result = ""
if 'generated_script' not in st.session_state: st.session_state.generated_script = ""
if 'generated_image' not in st.session_state: st.session_state.generated_image = None
if 'breakdown_result' not in st.session_state: st.session_state.breakdown_result = ""
if 'music_result' not in st.session_state: st.session_state.music_result = ""
if 'shotlist_result' not in st.session_state: st.session_state.shotlist_result = ""

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["✨ Story Generator", "📝 Script Doctor", "🎥 Shot List Maker", "🎨 Storyboarder"])

# ==========================================
# TAB 1: STORY GENERATOR
# ==========================================
with tab1:
    st.markdown("### 🧬 AI Screenwriter")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        genre = st.selectbox("Genre", ["Sci-Fi", "Horror", "Comedy", "Thriller", "Drama"])
        time_period = st.selectbox("Era", ["Modern", "Future", "1980s", "Medieval", "Western"])
    with c2:
        character = st.text_input("Protagonist", placeholder="e.g. A retired spy")
        setting = st.text_input("Setting", placeholder="e.g. A bunker")
    with c3:
        conflict = st.text_input("Conflict", placeholder="e.g. Bomb ticking")
        tone = st.selectbox("Tone", ["Serious", "Funny", "Dark", "Surreal"])

    if st.button("✨ Write Scene", type="primary", use_container_width=True):
        if not check_usage_limit(): st.stop()
        
        if not character or not setting:
            st.warning("Need Character & Setting.")
        else:
            with st.spinner("Writing script..."):
                script_prompt = f"""
                You are a professional Hollywood Screenwriter. Write a scene using standard format.
                STRICT FORMATTING RULES:
                1. Scene Headings must be ALL CAPS (e.g. INT. ROOM - NIGHT)
                2. Character Names must be ALL CAPS centered above dialogue.
                
                Parameters:
                Genre: {genre} | Era: {time_period} | Tone: {tone}
                Character: {character} | Setting: {setting} | Conflict: {conflict}
                Output ONLY the script content.
                """
                response = get_llm_response(script_prompt, 1000, api_choice)
                if not "Error" in response:
                    increment_usage() # Increment only on success
                st.session_state.generated_script = response

    if st.session_state.generated_script:
        st.divider()
        st.subheader("📜 Generated Script")
        st.code(st.session_state.generated_script, language="plaintext")

# ==========================================
# TAB 2: SCRIPT DOCTOR
# ==========================================
with tab2:
    st.markdown("### 🩺 Analyze & Fix Scripts")
    
    default_text = ""
    if use_auto_context and st.session_state.generated_script:
        default_text = st.session_state.generated_script
        
    script_input = st.text_area("Scene Text", value=default_text, height=300, placeholder="Paste script here...")
    
    c1, c2 = st.columns(2)
    with c1:
        analysis_tone = st.selectbox("Logline Tone", ["Professional", "Mysterious", "Dramatic"])
    with c2:
        tasks = st.multiselect("Analysis Tasks", 
                               ["Summarize", "Generate Logline", "Scene Breakdown", "Music Suggestions"],
                               default=["Summarize", "Generate Logline"])
        
    if st.button("🚀 Analyze Script", type="primary"):
        if not check_usage_limit(): st.stop()
        
        if not script_input:
            st.warning("Paste text first.")
        else:
            with st.spinner("Analyzing..."):
                success = False
                if "Summarize" in tasks:
                    summ_prompt = f"Summarize this scene in 2 bullet points:\n{script_input}"
                    st.session_state.summary_result = get_llm_response(summ_prompt, 200, api_choice)
                    success = True
                
                if "Generate Logline" in tasks:
                    log_prompt = f"Write a {analysis_tone} logline for this:\n{script_input}"
                    st.session_state.logline_result = get_llm_response(log_prompt, 100, api_choice)
                    success = True
                
                if "Scene Breakdown" in tasks:
                    bd_prompt = f"List Characters, Props, and Sounds for this script:\n{script_input}"
                    st.session_state.breakdown_result = get_llm_response(bd_prompt, 300, api_choice)
                    success = True
                    
                if "Music Suggestions" in tasks:
                    music_prompt = f"Suggest a musical score (Genre, Instruments, Tempo, Reference Track) for:\n{script_input}"
                    st.session_state.music_result = get_llm_response(music_prompt, 300, api_choice)
                    success = True
                
                if success:
                    increment_usage()

    # OUTPUTS
    if st.session_state.summary_result:
        st.success(f"**Summary:** {st.session_state.summary_result}")
    if st.session_state.logline_result:
        st.info(f"**Logline:** {st.session_state.logline_result}")
        
    c_out1, c_out2 = st.columns(2)
    with c_out1:
        if st.session_state.breakdown_result:
            with st.expander("📂 Scene Breakdown", expanded=True):
                st.markdown(st.session_state.breakdown_result)
    with c_out2:
        if st.session_state.music_result:
            with st.expander("🎵 Music Score Suggestions", expanded=True):
                st.markdown(st.session_state.music_result)

# ==========================================
# TAB 3: SHOT LIST MAKER
# ==========================================
with tab3:
    st.markdown("### 🎥 AI Cinematographer")
    
    shot_default = ""
    if use_auto_context and script_input: 
        shot_default = script_input
    elif use_auto_context and st.session_state.generated_script:
        shot_default = st.session_state.generated_script
        
    shot_input = st.text_area("Script Context", value=shot_default, height=150, help="The script to visualize")
    shot_style = st.selectbox("Directing Style", ["Standard Coverage", "Wes Anderson", "Michael Bay", "Handheld Documentary", "Film Noir"])
    
    if st.button("🎬 Generate Shot List", type="primary"):
        if not check_usage_limit(): st.stop()
        
        if not shot_input:
            st.warning("No script found.")
        else:
            with st.spinner("Planning shots..."):
                sl_prompt = f"""
                Act as a Director of Photography. Create a numbered Shot List for this scene.
                Style: {shot_style}
                Format as a Markdown Table with columns: | Shot # | Size | Angle | Movement | Description |
                Script: {shot_input}
                """
                response = get_llm_response(sl_prompt, 800, api_choice)
                if not "Error" in response:
                    increment_usage()
                st.session_state.shotlist_result = response

    if st.session_state.shotlist_result:
        st.markdown(st.session_state.shotlist_result)

# ==========================================
# TAB 4: STORYBOARDER
# ==========================================
with tab4:
    st.markdown("### 🖌️ Visual Development")
    
    sb_default = ""
    if use_auto_context and st.session_state.logline_result:
        sb_default = st.session_state.logline_result
    
    # RESTORED: Advanced Camera Controls
    c1, c2 = st.columns([3, 1])
    with c1:
        sb_prompt = st.text_input("Shot Description", value=sb_default)
    with c2:
        sb_style = st.selectbox("Art Style", ["Cinematic", "Anime", "Cyberpunk", "Oil Painting", "Noir"])
    
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        lighting = st.selectbox("Lighting", ["Natural", "Neon", "Golden Hour", "Dark/Moody"])
    with cc2:
        angle = st.selectbox("Camera Angle", ["Wide Shot", "Close Up", "Low Angle", "Overhead"])
    with cc3:
        lens = st.selectbox("Lens", ["35mm", "85mm Portrait", "Fisheye", "Anamorphic"])

    use_magic = st.toggle("✨ Use Prompt Magic", value=True)

    if st.button("🎨 Generate Image", type="primary"):
        if not check_usage_limit(): st.stop()
        
        if not sb_prompt:
            st.warning("Describe the shot.")
        else:
            with st.spinner("Dreaming..."):
                base_prompt = f"{sb_style} style, {angle}, {sb_prompt}, {lighting} lighting, shot on {lens}"
                
                final_prompt = base_prompt
                if use_magic:
                    with st.status("✨ Optimizing prompt..."):
                        final_prompt = optimize_prompt_magic(base_prompt, api_choice)
                
                image = get_image_response(final_prompt)
                
                if image and not isinstance(image, str):
                    increment_usage()
                    st.session_state.generated_image = image
                    st.image(image, caption=f"Storyboard: {sb_style}", use_container_width=True)
                elif image == "loading_error":
                    st.warning("⏳ Model loading. Wait 30s.")
                else:
                    st.error("Generation failed.")

# --- EXPORT SECTION ---
st.divider()
c_ex1, c_ex2 = st.columns([3, 1])
with c_ex1:
    st.markdown("#### 📦 Export Production Package")
    st.caption("Download your Script, Logline, Storyboard, and Shot List in one PDF.")
with c_ex2:
    if st.session_state.generated_script:
        pdf_bytes = create_hollywood_pdf(
            st.session_state.generated_script, 
            st.session_state.logline_result or "Generated Script",
            st.session_state.generated_image,
            st.session_state.shotlist_result 
        )
        st.download_button(
            "🎬 Download Full PDF",
            pdf_bytes,
            "production_report.pdf",
            mime="application/pdf",
            type="primary"
        )
