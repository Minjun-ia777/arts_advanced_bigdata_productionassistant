import streamlit as st
from huggingface_hub import InferenceClient
import io
from PIL import Image
from openai import OpenAI
from fpdf import FPDF
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI Pre-Production Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONFIGURATION & LIMITS ---
FREE_TIER_DAILY_LIMIT = 20
if 'usage_count' not in st.session_state: st.session_state.usage_count = 0

# --- API SETUP ---
try:
    hf_token = st.secrets["HF_TOKEN"]
except:
    st.error("⚠️ HF_TOKEN not found in Secrets. The app will not work.")
    st.stop()

# --- HELPER FUNCTIONS ---

def check_usage_limit():
    if not st.session_state.get('openai_api_key'):
        st.session_state.usage_count += 1
        usage = st.session_state.usage_count
        percent = usage / FREE_TIER_DAILY_LIMIT
        
        if percent >= 1.0:
            st.error(f"❌ Daily Limit Reached ({usage}/{FREE_TIER_DAILY_LIMIT}). Wait 24h or use Premium.")
            return False
        elif percent >= 0.75:
            st.warning(f"⚠️ 75% of free quota used.")
    return True

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

# --- NEW: PROMPT MAGIC (CHAIN OF THOUGHT) ---
def optimize_prompt_magic(user_prompt, provider):
    system_prompt = f"""
    Act as an expert Prompt Engineer for Stable Diffusion XL.
    Rewrite the following user description into a high-quality image generation prompt.
    
    User Description: "{user_prompt}"
    
    Rules:
    1. Add keywords for lighting (e.g., volumetric, cinematic).
    2. Add keywords for style (e.g., 8k, masterpiece, photorealistic).
    3. Add camera details (e.g., 35mm, wide angle).
    4. Return ONLY the raw prompt text. No intros.
    """
    return get_llm_response(system_prompt, 100, provider)

# --- UPGRADED: STUDIOBINDER HOLLYWOOD PDF FORMAT ---
class ScreenplayPDF(FPDF):
    def header(self):
        self.set_font('Courier', '', 12)
        # Page number top right
        self.cell(0, 10, f'{self.page_no()}.', 0, 0, 'R')
        self.ln(10)

def create_hollywood_pdf(script_text, logline, image=None):
    # Standard Letter size
    pdf = ScreenplayPDF(format='Letter')
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=25)
    
    # 1. MARGINS (StudioBinder Standard)
    # Left: 1.5 inch (38mm), Right: 1.0 inch (25mm)
    pdf.set_left_margin(38)
    pdf.set_right_margin(25)
    
    # 2. LOGLINE PAGE
    pdf.set_font("Courier", 'B', 12)
    pdf.cell(0, 10, "LOGLINE:", ln=True)
    pdf.set_font("Courier", '', 12)
    pdf.multi_cell(0, 6, logline)
    pdf.ln(10)
    
    # 3. STORYBOARD (If exists)
    if image:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            image.save(tmp_file.name)
            # Image centered, 6 inches wide (approx 152mm)
            pdf.image(tmp_file.name, x=38, w=140) 
        pdf.ln(15)

    pdf.set_font("Courier", 'B', 12)
    pdf.cell(0, 10, "SCENE SCRIPT:", ln=True)
    pdf.ln(5)
    
    # 4. SCRIPT PARSING LOGIC
    pdf.set_font("Courier", '', 12)
    
    lines = script_text.split('\n')
    is_dialogue_block = False
    
    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(5) # Blank line space
            is_dialogue_block = False
            continue
            
        # SCENE HEADING (INT./EXT.) -> ALL CAPS, BOLD, LEFT ALIGNED
        if line.startswith("INT.") or line.startswith("EXT.") or line.startswith("I/E."):
            pdf.set_font("Courier", 'B', 12)
            pdf.set_x(38) # Reset to left margin
            pdf.cell(0, 5, line.upper(), ln=True)
            pdf.set_font("Courier", '', 12)
            is_dialogue_block = False
            
        # CHARACTER NAME -> ALL CAPS, CENTERED (3.7 inches / ~94mm from left edge)
        # Heuristic: Upper case, short, not a slugline
        elif line.isupper() and len(line) < 40 and not is_dialogue_block:
            pdf.set_x(94) # Character indent
            pdf.cell(0, 5, line, ln=True)
            is_dialogue_block = True # Next line is likely dialogue
            
        # PARENTHETICAL -> (wryly), Indented (3.1 inches / ~79mm)
        elif line.startswith("(") and line.endswith(")"):
            pdf.set_x(79)
            pdf.cell(0, 5, line, ln=True)
            
        # DIALOGUE -> Indented (2.5 inches / ~63mm)
        elif is_dialogue_block:
            pdf.set_x(63) # Dialogue indent
            # Limit width of dialogue box to approx 3.5 inches (90mm)
            pdf.multi_cell(90, 5, line)
            
        # TRANSITIONS (CUT TO:) -> Right aligned (approx 6 inches / 152mm)
        elif line.endswith("TO:") and line.isupper():
            pdf.set_x(152)
            pdf.cell(0, 5, line, ln=True)
            
        # ACTION -> Standard Left Margin, Full Width
        else:
            pdf.set_x(38)
            pdf.multi_cell(0, 5, line)
            is_dialogue_block = False

    return pdf.output(dest="S").encode("latin-1")

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2503/2503508.png", width=50)
    st.title("Settings")
    
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

    # Usage Monitor
    if api_choice == "Free (Hugging Face)":
        st.divider()
        st.subheader("📊 Daily Quota")
        u_count = st.session_state.usage_count
        st.progress(min(u_count / FREE_TIER_DAILY_LIMIT, 1.0))
        st.caption(f"{u_count}/{FREE_TIER_DAILY_LIMIT} requests used")

    st.divider()
    st.caption("Final Project 2025")

# --- MAIN HEADER ---
st.title("🎬 AI Pre-Production Assistant")

# --- SESSION STATE ---
if 'summary_result' not in st.session_state: st.session_state.summary_result = ""
if 'logline_result' not in st.session_state: st.session_state.logline_result = ""
if 'generated_script' not in st.session_state: st.session_state.generated_script = ""
if 'generated_image' not in st.session_state: st.session_state.generated_image = None
if 'breakdown_result' not in st.session_state: st.session_state.breakdown_result = ""

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📝 Script Doctor", "🎨 Storyboarder", "✨ Story Generator"])

# ==========================================
# TAB 1: SCRIPT DOCTOR
# ==========================================
with tab1:
    st.markdown("### 🩺 Analyze & Fix Scripts")
    
    c1, c2 = st.columns([2, 1])
    with c1:
        script_input = st.text_area("Paste Scene Text", height=300, placeholder="INT. COFFEE SHOP - DAY...")
    with c2:
        st.markdown("**Tools**")
        analysis_tone = st.selectbox("Logline Tone", ["Professional", "Mysterious", "Dramatic"])
        do_breakdown = st.checkbox("Generate Scene Breakdown", help="Extracts props and characters")
        
        if st.button("🚀 Analyze", type="primary", use_container_width=True):
            if not check_usage_limit(): st.stop()
            
            if not script_input:
                st.warning("Paste text first.")
            else:
                with st.spinner("Analyzing..."):
                    summ_prompt = f"Summarize this scene in 2 bullet points:\n{script_input}"
                    summ_response = get_llm_response(summ_prompt, 200, api_choice)
                    
                    log_prompt = f"Write a {analysis_tone} logline for this:\n{script_input}"
                    log_response = get_llm_response(log_prompt, 100, api_choice)
                    
                    st.session_state.summary_result = summ_response
                    st.session_state.logline_result = log_response
                    
                    if do_breakdown:
                        bd_prompt = f"""
                        Analyze this script scene and list:
                        1. Characters (Names)
                        2. Props (Objects mentioned)
                        3. Sound/VFX Notes
                        
                        Script: {script_input}
                        """
                        st.session_state.breakdown_result = get_llm_response(bd_prompt, 300, api_choice)

    # OUTPUTS
    if st.session_state.summary_result:
        st.divider()
        col_A, col_B = st.columns(2)
        with col_A:
            st.subheader("Summary")
            st.success(st.session_state.summary_result)
        with col_B:
            st.subheader("Logline")
            st.info(st.session_state.logline_result)
            
        if st.session_state.breakdown_result:
            with st.expander("📂 Scene Breakdown (Props & Characters)"):
                st.markdown(st.session_state.breakdown_result)

# ==========================================
# TAB 2: STORYBOARDER
# ==========================================
with tab2:
    st.markdown("### 🖌️ Visual Development")
    
    default_prompt = st.session_state.logline_result if "Error" not in st.session_state.logline_result else ""
    
    c1, c2 = st.columns([3, 1])
    with c1:
        sb_prompt = st.text_input("Shot Description", value=default_prompt)
    with c2:
        sb_style = st.selectbox("Style", ["Cinematic", "Anime", "Cyberpunk", "Oil Painting", "Noir"])
    
    use_magic = st.toggle("✨ Use Prompt Magic (Chain of Thought)", value=True, help="AI will rewrite your prompt to be more professional before generating.")

    if st.button("🎨 Generate Image", type="primary"):
        if not check_usage_limit(): st.stop()
        
        if not sb_prompt:
            st.warning("Describe the shot first.")
        else:
            with st.spinner("Dreaming..."):
                final_prompt = f"{sb_style} style, {sb_prompt}"
                
                if use_magic:
                    with st.status("✨ Optimizing prompt with AI..."):
                        optimized = optimize_prompt_magic(final_prompt, api_choice)
                        st.write(f"**Original:** {final_prompt}")
                        st.write(f"**Optimized:** {optimized}")
                        final_prompt = optimized 
                
                image = get_image_response(final_prompt)
                
                if image and not isinstance(image, str):
                    st.session_state.generated_image = image
                    st.image(image, caption="Generated Storyboard", use_container_width=True)
                elif image == "loading_error":
                    st.warning("⏳ Image model is loading. Wait 30s.")
                else:
                    st.error("Image generation failed.")

# ==========================================
# TAB 3: STORY GENERATOR
# ==========================================
with tab3:
    st.markdown("### 🧬 AI Screenwriter")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        genre = st.selectbox("Genre", ["Sci-Fi", "Horror", "Comedy", "Thriller"])
        time_period = st.selectbox("Era", ["Modern", "Future", "1980s", "Medieval"])
    with c2:
        character = st.text_input("Protagonist", placeholder="e.g. A retired spy")
        setting = st.text_input("Setting", placeholder="e.g. A bunker")
    with c3:
        conflict = st.text_input("Conflict", placeholder="e.g. Bomb ticking")
        tone = st.selectbox("Tone", ["Serious", "Funny", "Dark"])

    if st.button("✨ Write Scene", type="primary", use_container_width=True):
        if not check_usage_limit(): st.stop()
        
        if not character or not setting:
            st.warning("Need Character & Setting.")
        else:
            with st.spinner("Writing script..."):
                # UPDATED PROMPT to ensure AI outputs clean Hollywood format for the PDF to catch
                script_prompt = f"""
                You are a professional Hollywood Screenwriter. Write a scene using standard format.
                
                STRICT FORMATTING RULES:
                1. Scene Headings must be ALL CAPS (e.g. INT. ROOM - NIGHT)
                2. Character Names must be ALL CAPS centered above dialogue.
                3. Do not use bold or markdown in the output, just plain text.
                4. Write dialogue clearly.
                
                Parameters:
                Genre: {genre} | Era: {time_period} | Tone: {tone}
                Character: {character} | Setting: {setting} | Conflict: {conflict}
                
                Output ONLY the script content. No intros.
                """
                response = get_llm_response(script_prompt, 1000, api_choice)
                st.session_state.generated_script = response

    if st.session_state.generated_script:
        st.divider()
        st.subheader("📜 Final Script")
        st.code(st.session_state.generated_script, language="plaintext")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button(
                "📥 Download .txt",
                st.session_state.generated_script,
                "script.txt"
            )
        with col_d2:
            # Generate the Professional PDF
            pdf_bytes = create_hollywood_pdf(
                st.session_state.generated_script, 
                st.session_state.logline_result or "Generated Script",
                st.session_state.generated_image 
            )
            st.download_button(
                "🎬 Export StudioBinder PDF",
                pdf_bytes,
                "hollywood_script.pdf",
                mime="application/pdf",
                help="Exports in Standard Industry Format (Courier, margins, sluglines)."
            )
