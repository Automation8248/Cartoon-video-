import os
import random
import requests
import google.generativeai as genai
from gradio_client import Client
from duckduckgo_search import DDGS
from pathlib import Path

# --- CONFIGURATION ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# --- PROMPTS ---
# Note: I added "VERTICAL IMAGE" forcefully here to fix the aspect ratio issue
USER_GEMINI_PROMPT = "Recreate this character in a full body standing pose, looking happy. The image MUST be VERTICAL (9:16 ratio). High quality, 3D render style, clean background."

USER_VIDEO_PROMPT = "Gentle movement, blinking eyes, breathing motion, high quality animation."

# --- CARTOON LIST ---
CARTOON_LIST = [
    "Doraemon full body cartoon",
    "Shinchan cartoon full body",
    "Pikachu cute full body",
    "Tom and Jerry cartoon character",
    "SpongeBob SquarePants full body",
    "Motu Patlu cartoon",
    "Chhota Bheem full body",
    "Oggy and the cockroaches"
]

genai.configure(api_key=GEMINI_KEY)

# --- STEP 1: SEARCH ---
def search_random_character():
    query = random.choice(CARTOON_LIST)
    print(f"🔍 Searching for: {query}...")
    with DDGS() as ddgs:
        results = list(ddgs.images(query, max_results=1))
    
    if results:
        image_url = results[0]['image']
        print(f"✅ Found Image URL: {image_url}")
        return image_url
    else:
        raise Exception("Could not find any image on search.")

def download_image(url, filename="input.jpg"):
    print(f"⬇️ Downloading Image...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        return filename
    raise Exception("Failed to download image.")

# --- STEP 2: GEMINI (FIXED) ---
def gemini_process(input_path):
    print("🤖 Gemini: Analyzing & Regenerating...")
    imagen_model = genai.GenerativeModel("imagen-3.0-generate-001")
    
    myfile = genai.upload_file(input_path)
    full_prompt = f"Based on the character in this image {myfile.uri}, {USER_GEMINI_PROMPT}"
    
    # --- ERROR FIX IS HERE ---
    # We removed 'aspect_ratio' from GenerationConfig because it caused the crash.
    # We rely on the text prompt now.
    result = imagen_model.generate_content(
        full_prompt,
        generation_config=genai.types.GenerationConfig(
            number_of_images=1
        )
    )
    
    output_file = "gemini_output.png"
    result.parts[0].save(output_file)
    print(f"✅ Generated Image: {output_file}")
    return output_file

# --- STEP 3: VIDEO ---
def make_video_hf(image_path):
    print("🎥 Hugging Face: Making Video...")
    client = Client("multimodalart/stable-video-diffusion", hf_token=HF_TOKEN)
    
    result_path = client.predict(
        image_path, "0.0", 25, 14, api_name="/predict"
    )
    
    final_vid = "final_output.mp4"
    if os.path.exists(final_vid): os.remove(final_vid)
    Path(result_path).rename(final_vid)
    print("✅ Video Ready!")
    return final_vid

# --- STEP 4: SEND ---
def deliver_content(video_path):
    print("🚀 Delivering...")
    if TELEGRAM_TOKEN:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
        with open(video_path, 'rb') as f:
            requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID}, files={'video': f})
        print("📬 Sent to Telegram.")
    
    if WEBHOOK_URL:
        with open(video_path, 'rb') as f:
            requests.post(WEBHOOK_URL, files={'file': f})
        print("📡 Sent to Webhook.")

if __name__ == "__main__":
    try:
        img_url = search_random_character()
        local_img = download_image(img_url)
        gemini_img = gemini_process(local_img)
        final_video = make_video_hf(gemini_img)
        deliver_content(final_video)
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)
