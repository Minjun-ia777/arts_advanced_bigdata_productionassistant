Markdown
# 🎬 AI Pre-Production Assistant

### A Generative AI Tool for Filmmakers & Storytellers

**Final Project 2025** **Course:** Art & Advanced Big Data  
**Built with:** Python, Streamlit, Hugging Face, Stable Diffusion

---

## 📖 Project Overview
The **AI Pre-Production Assistant** is a comprehensive web application designed to accelerate the early stages of film production. By leveraging Large Language Models (LLMs) and Latent Diffusion Models (LDMs), this tool acts as an "always-on" creative partner.

It solves the "Blank Page Problem" by helping creators write scripts, analyze narrative structure, plan shot lists, and visualize storyboards—all within a single, cohesive interface.

## ✨ Key Features

### 1. 🧬 AI Screenwriter (Text Generation)
* **Generates Scripts:** Creates properly formatted screenplays based on user inputs (Genre, Tone, Character, Conflict).
* **Smart Formatting:** Outputs standard screenplay format (Courier font, Scene Headings, Dialogue).
* **Dual Modes:** Toggle between "Short" (1-minute) or "Detailed" (Dialogue-heavy) scenes.

### 2. 🩺 Script Doctor (Analysis & Logic)
* **Narrative Analysis:** Automatically summarizes scenes and generates professional Loglines.
* **Scene Breakdown:** Extracts Characters, Props, and VFX notes.
* **Music & Color:** Suggests musical scores (with reference tracks) and generates a downloadable **Color Grading Palette (.csv)** based on the script's mood.

### 3. 🎥 AI Cinematographer (Planning)
* **Shot List Generator:** Converts the script into a structured Shot List (Shot Size, Angle, Movement).
* **Director Styles:** Emulates specific directing styles (e.g., Wes Anderson, Michael Bay) to suggest camera coverage.

### 4. 🎨 Visual Storyboarder (Image Generation)
* **Text-to-Image:** Uses **Stable Diffusion XL** to visualize scenes.
* **Prompt Magic:** A "Chain-of-Thought" optimization feature where the LLM rewrites simple user descriptions into professional photography prompts (adding lighting, lens type, and texture details) before generation.

### 5. 📦 Professional Export
* **Hollywood PDF:** Compiles the Script, Logline, Storyboard, and Shot List into a single **StudioBinder-standard PDF**.
* **Smart Layout:** Handles margins, bold sluglines, and centered character names automatically.

---

## 🛠️ Technical Architecture

This app is built on a **Serverless Architecture** using the **Hugging Face Inference API**.

* **Frontend:** Streamlit (Python)
* **LLM Engine (Logic/Text):** `Qwen/Qwen2.5-7B-Instruct` (Selected for its high adherence to complex formatting instructions).
* **Image Engine (Vision):** `stabilityai/stable-diffusion-xl-base-1.0` (Selected for photorealism).
* **Dual-Engine Logic:** The app supports a "Premium" toggle. If a user provides an OpenAI API Key, it seamlessly switches the text engine to `GPT-4o` for enhanced performance.
* **Usage Limiting:** Includes a server-side IP tracker to simulate a "Daily Free Tier" limit (20 requests/day).

---

## 🚀 Installation & Setup

Follow these steps to run the project locally.

### 1. Clone the Repository
```bash
git clone [https://github.com/minjun-ia777/ai-pre-production-assistant.git](https://github.com/YOUR_USERNAME/ai-pre-production-assistant.git)
cd ai-pre-production-assistant
2. Install Dependencies

Bash
pip install -r requirements.txt
3. Set up Secrets

Create a folder named .streamlit in the root directory. Inside, create a file named secrets.toml. Add your Hugging Face Token (Free) inside:

Ini, TOML
HF_TOKEN = "hf_YOUR_HUGGINGFACE_TOKEN_HERE"
(Note: If deploying to Streamlit Cloud, add this to the "Secrets" setting in the dashboard instead).

4. Run the App

Bash
streamlit run app.py
📂 Dependencies (requirements.txt)
streamlit: Web framework.

huggingface_hub: API connection client.

openai: Optional integration for premium users.

fpdf: PDF generation engine.

Pillow: Image processing.

🔮 Future Improvements
Audio Table Read: Implementing Text-to-Speech to have AI actors read the script aloud.

Character Consistency: Using LoRA adapters to keep the main character looking the same in every storyboard frame.

Cloud Saving: Integrating a database (Supabase/Firebase) to save projects permanently.

Created by Ezequiel Gavilan | 2025

## Live Demo: 
https://artsadvancedbigdataappuctionassistant-aazqzscjsnakqe5zdwxqhn.streamlit.app
