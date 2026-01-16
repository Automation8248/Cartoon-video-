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
    "Doraemon",
    "Shinchan",
    "Pikachu",
    "Tom and Jerry",
    "SpongeBob SquarePants",
    "Motu Patlu",
    "Chhota Bheem",
    "Oggy",
    "Mickey Mouse",
    "Donald Duck"
]

genai.configure(api_key=GEMINI_KEY)

# --- STEP 1: SEARCH ---
def search_random_character():
    # Character name select karte hain
    char_name = random.choice(CARTOON_LIST)
    query = f"{char_name} full body cartoon"
    print(f"🔍 Searching for: {query}...")
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=1))
        
        if results:
            image_url = results[0]['image']
            print(f"✅ Found Image URL: {image_url}")
            return image_url, char_name # URL aur Naam dono wapas bhej rahe hain
        else:
            print("⚠️ Search empty, using backup.")
            return "https://cdn.pixabay.com/photo/2020/05/08/02/55/cartoon-5143714_1280.png", "Cartoon Character"
    except Exception as e:
        print(f"⚠️ Search Error: {e}")
        return "https://cdn.pixabay.com/photo/2020/05/08/02/55/cartoon-5143714_1280.png", "Cartoon Character"

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
    # Agar download fail bhi ho, toh hum bina image ke bhi aage badh sakte hain
    print("⚠️ Download failed, skipping analysis step.")
    return None

# --- STEP 2: ANALYZE (WITH FALLBACK) ---
def get_image_prompt(input_path, character_name):
    print("🤖 Attempting Gemini Analysis...")
    
    # Agar image download nahi hui, toh direct fallback
    if input_path is None:
        print("⚠️ No input image. Using Character Name only.")
        return f"{character_name} cartoon character"

    try:
        # Try using Gemini 1.5 Flash
        model = genai.GenerativeModel('gemini-1.5-flash')
        myfile = genai.upload_file(input_path)
        result = model.generate_content(
            [myfile, "Describe this character's appearance and clothes in one sentence."]
        )
        description = result.text.strip()
        print(f"✅ Gemini Analysis Success: {description}")
        return description

    except Exception as e:
        # YAHAN MAGIC HAI: Agar Gemini Error de (404 etc), toh hum rukenge nahi!
        print(f"⚠️ Gemini Failed ({e}). Switching to Backup Mode.")
        print(f"👉 Using Character Name '{character_name}' directly.")
        return f"{character_name} cartoon character, cute style"

# --- STEP 3: GENERATE 9:16 IMAGE (POLLINATIONS) ---
def generate_pollinations_image(prompt):
    print("🎨 Generating 9:16 Image (Pollinations AI)...")
    
    # Force 9:16 aspect ratio
    final_prompt = f"{prompt}, full body standing, 3d render style, vibrant colors, clean background, vertical wallpaper, 8k, high quality"
    encoded_prompt = requests.utils.quote(final_prompt)
    
    # Pollinations URL for vertical image
    url = f"https://pollinations.ai/p/{encoded_prompt}?width=720&height=1280&seed={random.randint(1, 1000)}&nologo=true"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            filename = "gen_image_9x16.jpg"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✅ Image Generated: {filename}")
            return filename
    except Exception as e:
        print(f"❌ Generation Error: {e}")
    
    raise Exception("Failed to generate image from Pollinations.")

# --- STEP 4: MAKE VIDEO (HUGGING FACE) ---
def make_video_hf(image_path):
    print("🎥 Hugging Face: Making Video...")
    try:
        client = Client("multimodalart/stable-video-diffusion", hf_token=HF_TOKEN)
        result_path = client.predict(image_path, "0.0", 25, 14, api_name="/predict")
        
        final_vid = "final_output.mp4"
        if os.path.exists(final_vid): os.remove(final_vid)
        Path(result_path).rename(final_vid)
        print("✅ Video Ready!")
        return final_vid
    except Exception as e:
        raise Exception(f"Video Generation Failed: {e}")

# --- STEP 5: SEND ---
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
        # 1. Search (Returns URL and Name)
        img_url, char_name = search_random_character()
        local_img = download_image(img_url)
        
        # 2. Get Prompt (Gemini OR Fallback to Name)
        prompt_text = get_image_prompt(local_img, char_name)
        
        # 3. Generate 9:16 Image
        new_img = generate_pollinations_image(prompt_text)
        
        # 4. Generate Video
        final_video = make_video_hf(new_img)
        
        # 5. Send
        deliver_content(final_video)
        
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        if TELEGRAM_TOKEN:
             requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=Bot Error: {e}")
        exit(1)
