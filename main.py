import os
import random
import requests
import google.generativeai as genai
from gradio_client import Client
from duckduckgo_search import DDGS # Image search ke liye
from pathlib import Path

# --- CONFIGURATION ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# --- FIXED PROMPTS (Jo tumne kaha fix rahenge) ---
# Note: "this character" likha hai taaki jo bhi image aaye uspe apply ho jaye.
USER_GEMINI_PROMPT = "Recreate this character in a full body standing pose, looking happy and cute. High quality, 3D render style, clean background. Aspect ratio 9:16 vertical."

USER_VIDEO_PROMPT = "Gentle movement, blinking eyes, breathing motion, high quality animation."

# --- CHARACTER LIST (Yahan wo naam daalo jo tum chahte ho search ho) ---
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

# --- STEP 1: AUTO-SEARCH IMAGE ---
def search_random_character():
    # 1. Randomly ek topic choose karo
    query = random.choice(CARTOON_LIST)
    print(f"🔍 Searching for: {query}...")

    # 2. Search using DuckDuckGo (Free & No API Key needed)
    with DDGS() as ddgs:
        # 1 image dhundo
        results = list(ddgs.images(query, max_results=1))
    
    if results:
        image_url = results[0]['image']
        print(f"✅ Found Image URL: {image_url}")
        return image_url
    else:
        raise Exception("Could not find any image on search.")

def download_image(url, filename="input.jpg"):
    print(f"⬇️ Downloading Image...")
    # Browser jaisa behavior dikhane ke liye headers add kiye
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        return filename
    raise Exception("Failed to download image from internet.")

# --- STEP 2: GEMINI PROCESSING ---
def gemini_process(input_path):
    print("🤖 Gemini: Analyzing & Regenerating 9:16...")
    imagen_model = genai.GenerativeModel("imagen-3.0-generate-001")
    
    # Upload Input
    myfile = genai.upload_file(input_path)
    
    # Prompt combination
    full_prompt = f"Based on the character in this image {myfile.uri}, {USER_GEMINI_PROMPT}"
    
    result = imagen_model.generate_content(
        full_prompt,
        generation_config=genai.types.GenerationConfig(
            aspect_ratio="9:16",
            number_of_images=1
        )
    )
    
    output_file = "gemini_9x16.png"
    result.parts[0].save(output_file)
    print(f"✅ Generated 9:16 Image: {output_file}")
    return output_file

# --- STEP 3: VIDEO GENERATION ---
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
    # Telegram
    if TELEGRAM_TOKEN:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
        with open(video_path, 'rb') as f:
            requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID}, files={'video': f})
        print("📬 Sent to Telegram.")
    
    # Webhook
    if WEBHOOK_URL:
        with open(video_path, 'rb') as f:
            requests.post(WEBHOOK_URL, files={'file': f})
        print("📡 Sent to Webhook.")

# --- MAIN ---
if __name__ == "__main__":
    try:
        # 1. Search & Download
        img_url = search_random_character()
        local_img = download_image(img_url)
        
        # 2. Process
        gemini_img = gemini_process(local_img)
        final_video = make_video_hf(gemini_img)
        
        # 3. Send
        deliver_content(final_video)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        # Telegram Error Notification
        if TELEGRAM_TOKEN:
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=Bot Error: {e}")
        exit(1)
