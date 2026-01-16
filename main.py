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
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=1))
        
        if results:
            image_url = results[0]['image']
            print(f"✅ Found Image URL: {image_url}")
            return image_url
        else:
            return "https://cdn.pixabay.com/photo/2020/05/08/02/55/cartoon-5143714_1280.png"
    except Exception as e:
        print(f"⚠️ Search Error: {e}")
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

# --- STEP 2: ANALYZE WITH GEMINI (VISION ONLY) ---
def get_image_prompt(input_path):
    print("🤖 Gemini: Analyzing image to create prompt...")
    # We use Gemini 1.5 Flash just to SEE the image and describe it
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    myfile = genai.upload_file(input_path)
    # Ask Gemini to describe it for an image generator
    result = model.generate_content(
        [myfile, "Describe this cartoon character's appearance, clothing, and colors in one short sentence. Do not include background details."]
    )
    description = result.text.strip()
    print(f"📋 Prompt Created: {description}")
    return description

# --- STEP 3: GENERATE 9:16 IMAGE (VIA POLLINATIONS - FREE) ---
def generate_pollinations_image(prompt):
    print("🎨 Generating 9:16 Image (Pollinations AI)...")
    
    # We force 9:16 aspect ratio here (720x1280)
    final_prompt = f"{prompt}, full body shot, 3d render style, cute, standing pose, plain background, high quality, 8k"
    # Encoding prompt for URL
    encoded_prompt = requests.utils.quote(final_prompt)
    
    url = f"https://pollinations.ai/p/{encoded_prompt}?width=720&height=1280&seed={random.randint(1, 1000)}&nologo=true"
    
    response = requests.get(url)
    if response.status_code == 200:
        filename = "gen_image_9x16.jpg"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"✅ Image Generated: {filename}")
        return filename
    else:
        raise Exception("Pollinations AI failed to generate image.")

# --- STEP 4: MAKE VIDEO (HUGGING FACE) ---
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
        # 1. Search
        img_url = search_random_character()
        local_img = download_image(img_url)
        
        # 2. Analyze (Gemini)
        prompt_text = get_image_prompt(local_img)
        
        # 3. Generate 9:16 Image (Pollinations)
        new_img = generate_pollinations_image(prompt_text)
        
        # 4. Generate Video (Hugging Face)
        final_video = make_video_hf(new_img)
        
        # 5. Send
        deliver_content(final_video)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if TELEGRAM_TOKEN:
             requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=Bot Error: {e}")
        exit(1)
