import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from huggingface_hub import InferenceClient

# Tokens (Inhe hum baad mein environment variables mein set karenge)
TG_TOKEN = os.environ.get("TG_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

# Qwen Model Setup (Free API)
repo_id = "Qwen/Qwen2.5-72B-Instruct"
client = InferenceClient(model=repo_id, token=HF_TOKEN)

# AI se jawaab lene ka function
def get_qwen_response(user_text):
    try:
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant in Hindi and English."},
            {"role": "user", "content": user_text}
        ]
        # Max tokens badha sakte hain agar lamba answer chahiye
        response = client.chat_completion(messages=messages, max_tokens=800)
        return response.choices[0].message.content
    except Exception as e:
        return "Sorry, AI server busy hai. Thodi der baad try karein."

# Jab bhi message aayega ye function turant trigger hoga
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    print(f"Message received: {user_text}")
    
    # User ko batayein ki AI likh raha hai (Typing status...)
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # AI se response lein
    ai_reply = get_qwen_response(user_text)
    
    # Turant reply bhej de
    await context.bot.send_message(chat_id=chat_id, text=ai_reply)

if __name__ == '__main__':
    # Bot Application Build karein
    application = ApplicationBuilder().token(TG_TOKEN).build()
    
    # Sirf text messages handle karein
    msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(msg_handler)
    
    print("Bot is running instantly...")
    # Polling start karein (Ye lagatar check karta rahega)
    application.run_polling()
