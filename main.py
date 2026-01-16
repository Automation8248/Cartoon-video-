import os
import random
import requests
import google.generativeai as genai
from gradio_client import Client
from duckduckgo_search import DDGS
from pathlib import Path
import time

# --- CONFIGURATION ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# --- CARTOON LIST ---
CARTOON_LIST = [
    "Doraemon", "Shinchan", "Pikachu", "Tom and Jerry",
    "SpongeBob SquarePants", "Motu Patlu", "Chhota Bheem",
    "Oggy", "Mickey Mouse", "Donald Duck"
]

genai.configure(api_key=GEMINI_KEY)

# --- STEP 1: SEARCH ---
def search_random_character():
    char_name = random.choice(CARTOON_LIST)
    query = f"{char_name} full body cartoon"
    print(f"🔍 Searching for: {query}...")
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=1))
        
        if results:
            return results[0]['image'], char_name
        else:
            print("⚠️ Search empty, using backup.")
            return "https://cdn.pixabay.com/photo/2020/05/08/02/55/cartoon-5143714_1280.png", "Cartoon Character"
    except Exception as e:
        print(f"⚠️ Search Error: {e}, using backup.")
        return "https://cdn.pixabay.com/photo/2020/05/08/02/55/cartoon-5143714_1280.png", "Cartoon Character"

def download_image(url, filename="input.jpg"):
    print(f"⬇️ Downloading Image...")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            return filename
    except:
        pass
    return None

# --- STEP 2: ANALYZE ---
def get_image_prompt(input_path, character_name):
    print("🤖 Attempting Gemini Analysis...")
    if input_path is None:
        return f"{character_name} cartoon character"

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        myfile = genai.upload_file(input_path)
        result = model.generate_content([myfile, "Describe this character in 5 words."])
        return result.text.strip()
    except Exception as e:
        print(f"⚠️ Gemini Skipped. Using Name only.")
        return f"{character_name} cartoon character"

# --- STEP 3: GENERATE IMAGE (POLLINATIONS) ---
def generate_pollinations_image(prompt):
    print("🎨 Generating 9:16 Image...")
    final_prompt = f"{prompt}, full body standing, 3d render style, vibrant, vertical wallpaper, 8k"
    encoded_prompt = requests.utils.quote(final_prompt)
    url = f"https://pollinations.ai/p/{encoded_prompt}?width=720&height=1280&seed={random.randint(1, 1000)}&nologo=true"
    
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        with open("gen_image_9x16.jpg", 'wb') as f:
            f.write(response.content)
        return "gen_image_9x16.jpg"
    raise Exception("Pollinations Generation Failed")

# --- STEP 4: MAKE VIDEO (SUPER ROBUST MODE) ---
def make_video_hf(image_path):
    print("🎥 Hugging Face: Making Video...")
    
    # METHOD A: Try Official Stability AI Space
    try:
        print("👉 Trying Server 1 (Stability AI)...")
        # Note: Removing 'api_name' lets the client find the default function automatically
        client = Client("stabilityai/stable-video-diffusion-img2vid-xt")
        result_path = client.predict(
            image_path, "0.0", 25, 14, 
            # No api_name provided, relying on default
        )
        return process_result(result_path)
    except Exception as e1:
        print(f"⚠️ Server 1 Failed: {e1}")

    # METHOD B: Try Multimodal Art (Backup)
    try:
        print("👉 Trying Server 2 (Multimodal Art)...")
        client = Client("multimodalart/stable-video-diffusion")
        # Using a slightly different parameter set often used by this space
        result_path = client.predict(
            image_path, "0.0", 25, 14
        )
        return process_result(result_path)
    except Exception as e2:
        print(f"⚠️ Server 2 Failed: {e2}")

    raise Exception("All Video Servers are busy or broken right now.")

def process_result(result_path):
    # HF sometimes returns a folder or a tuple, handle both
    if isinstance(result_path, tuple): result_path = result_path[0]
    
    final_vid = "final_output.mp4"
    if os.path.exists(final_vid): os.remove(final_vid)
    
    # Rename securely
    import shutil
    shutil.move(result_path, final_vid)
    print("✅ Video Ready!")
    return final_vid

# --- STEP 5: SEND ---
def deliver_content(video_path):
    print("🚀 Delivering...")
    if TELEGRAM_TOKEN:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
        with open(video_path, 'rb') as f:
            requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID}, files={'video': f})
        print("📬 Telegram Sent.")
    
    if WEBHOOK_URL:
        with open(video_path, 'rb') as f:
            requests.post(WEBHOOK_URL, files={'file': f})

if __name__ == "__main__":
    try:
        img_url, char_name = search_random_character()
        local_img = download_image(img_url)
        prompt_text = get_image_prompt(local_img, char_name)
        new_img = generate_pollinations_image(prompt_text)
        final_video = make_video_hf(new_img)
        deliver_content(final_video)
    except Exception as e:
        print(f"❌ Final Error: {e}")
        if TELEGRAM_TOKEN:
             requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=Bot Error: {e}")
        exit(1)
