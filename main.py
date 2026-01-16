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
# Hum prompt mein hi chilla kar bolenge ki 9:16 chahiye
USER_GEMINI_PROMPT = "Recreate this character in a full body standing pose. IMPORTANT: The image MUST be VERTICAL (9:16 aspect ratio) for mobile phone wallpaper. High quality, 3D render style, clean background."

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
    try:
        # 'ddgs' library update ke baad syntax thoda change ho sakta hai, 
        # isliye hum safe tarika use kar rahe hain
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=1))
        
        if results:
            image_url = results[0]['image']
            print(f"✅ Found Image URL: {image_url}")
            return image_url
        else:
            # Fallback agar search fail ho jaye
            print("⚠️ Search failed, using backup image.")
            return "https://cdn.pixabay.com/photo/2020/05/08/02/55/cartoon-5143714_1280.png"
    except Exception as e:
        print(f"⚠️ Search Error: {e}, using backup image.")
        return "https://cdn.pixabay.com/photo/2020/05/08/02/55/cartoon-5143714_1280.png"

def download_image(url, filename="input.jpg"):
    print(f"⬇️ Downloading Image...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            return filename
    except:
        pass
    raise Exception("Failed to download image.")

# --- STEP 2: GEMINI (SIMPLIFIED - NO CONFIG) ---
def gemini_process(input_path):
    print("🤖 Gemini: Analyzing & Regenerating...")
    imagen_model = genai.GenerativeModel("imagen-3.0-generate-001")
    
    myfile = genai.upload_file(input_path)
    full_prompt = f"Based on the character in this image {myfile.uri}, {USER_GEMINI_PROMPT}"
    
    # --- ERROR FIX ---
    # Maine 'generation_config' poori tarah hata diya hai.
    # Ab library crash nahi karegi.
    result = imagen_model.generate_content(full_prompt)
    
    output_file = "gemini_output.png"
    # Result check karte hain
    if result.parts:
        result.parts[0].save(output_file)
        print(f"✅ Generated Image: {output_file}")
        return output_file
    else:
        raise Exception("Gemini generated no image. Prompt blocked or model busy.")

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
        # Telegram Error Notification
        if TELEGRAM_TOKEN:
             requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=Bot Error: {e}")
        exit(1)
