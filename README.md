# 🎬 AI Pre-Production Assistant

## Project Description
The **AI Pre-Production Assistant** is a web application designed to help film students and screenwriters streamline their creative process. By leveraging the power of Artificial Intelligence, this tool acts as a co-developer during the pre-production phase, assisting with both script analysis and visual development.

## Features
This app is divided into two main modules:

### 1. 📝 AI Script Doctor (Text Analysis)
* **Scene Summarization:** Uses AI (BART model) to read complex scenes and generate concise summaries.
* **Emotion Analysis:** Analyzes the text to determine the dominant mood or emotion of the scene (e.g., "Joy", "Fear", "Sadness") using the Roberta model.

### 2. 🎨 AI Storyboarder (Visual Generation)
* **Concept Art Generation:** Transforms text descriptions into visual storyboard frames.
* **Style Selection:** Users can choose from various artistic styles (Cinematic, Anime, Cyberpunk, etc.) to match their film's aesthetic.
* **Powered by Stable Diffusion:** Uses state-of-the-art image generation to visualize scenes instantly.

## Technologies Used
* **Python:** Core programming language.
* **Streamlit:** For building the interactive web interface.
* **Hugging Face Inference API:** To access the AI models without heavy local processing.
    * `facebook/bart-large-cnn` (Summarization)
    * `j-hartmann/emotion-english-distilroberta-base` (Emotion Analysis)
    * `runwayml/stable-diffusion-v1-5` (Image Generation)

## How to Run Locally
1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the app:
    ```bash
    streamlit run app.py
    ```

## Live Demo: 
https://artsadvancedbigdataappuctionassistant-aazqzscjsnakqe5zdwxqhn.streamlit.app
