import os
import asyncio
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright

# রেন্ডারে environment variable থেকে টোকেন নেওয়া
TOKEN = os.getenv('TOKEN', '8515561351:AAHdfsdy7ShGoCWShwTwU6XbWSdRb_TZXq8')

async def clean_and_format_html(raw_html):
    """ডিক্রিপ্ট হওয়া কোড থেকে ময়লা পরিষ্কার করা"""
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # এনক্রিপ্টরের বাড়তি স্ক্রিপ্ট ট্যাগগুলো রিমুভ করা (ঐচ্ছিক)
    scripts_to_remove = soup.find_all("script")
    for script in scripts_to_remove:
        if len(script.text) > 500: # বড় স্ক্রিপ্টগুলো সাধারণত এনক্রিপশন মেকানিজম হয়
            script.decompose()

    return soup.prettify()

async def decrypt_html_logic(file_path):
    """ব্রাউজারের মেমোরি থেকে ডাটা বের করার আসল লজিক"""
    async with async_playwright() as p:
        # রেন্ডারের জন্য chromium লঞ্চ করার সময় extra আর্গুমেন্ট
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu',
                '--single-process'
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            # রেন্ডারে User-Agent সেট করা
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        # ফাইল পাথ সেট করা
        abs_path = f"file://{os.path.abspath(file_path)}"
        
        try:
            # ব্রাউজারে ফাইলটি ওপেন করা
            await page.goto(abs_path, wait_until="networkidle", timeout=30000)
            
            # জাভাস্ক্রিপ্ট ডিক্রিপ্ট হওয়ার জন্য সময় দিন
            await asyncio.sleep(7)

            # ব্রাউজারের বর্তমান রেন্ডার করা কন্টেন্ট নেওয়া
            content = await page.content()
            
        except Exception as e:
            print(f"Error in playwright: {str(e)}")
            content = f"<html><body><h1>Error: {str(e)}</h1></body></html>"
        finally:
            await browser.close()
            
        return content

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_name = update.message.document.file_name

    if file_name.endswith(".html"):
        status_msg = await update.message.reply_text("🔍 ফাইলটি এনালাইজ করা হচ্ছে...")
        
        download_path = f"temp_{file_name}"
        await file.download_to_drive(download_path)

        try:
            await status_msg.edit_text("🔓 ডিক্রিপ্ট করা হচ্ছে (Virtual Browser-এ রান হচ্ছে)...")
            
            # স্টেপ ১: ব্রাউজার থেকে রেন্ডার করা কোড আনা
            raw_decrypted = await decrypt_html_logic(download_path)
            
            # স্টেপ ২: কোড ক্লিন করা
            await status_msg.edit_text("✨ কোড বিউটিফাই করা হচ্ছে...")
            clean_html = await clean_and_format_html(raw_decrypted)
            
            # স্টেপ ৩: ফাইল সেভ করা
            output_file = f"decrypted_{file_name}"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(clean_html)

            # ইউজারকে পাঠানো
            await update.message.reply_document(
                document=open(output_file, "rb"), 
                caption="✅ সফলভাবে ডিক্রিপ্ট করা হয়েছে!\n\nবটটি ব্রাউজার রেন্ডারিং মেথড ব্যবহার করেছে।"
            )
            
            # ক্লিনআপ
            if os.path.exists(download_path):
                os.remove(download_path)
            if os.path.exists(output_file):
                os.remove(output_file)
            await status_msg.delete()

        except Exception as e:
            await update.message.reply_text(f"❌ এরর: {str(e)}")
            # ক্লিনআপ
            if os.path.exists(download_path):
                os.remove(download_path)
            if os.path.exists(f"decrypted_{file_name}"):
                os.remove(f"decrypted_{file_name}")
    else:
        await update.message.reply_text("❌ দয়া করে একটি HTML ফাইল পাঠান।")

def main():
    print("বট স্টার্ট হচ্ছে...")
    print(f"রেন্ডার এনভায়রনমেন্ট: {'RENDER' in os.environ}")
    
    # রেন্ডারে টোকেন চেক
    if 'RENDER' in os.environ and TOKEN.startswith('8515561351'):
        print("⚠️  Warning: রেন্ডারে টোকেন environment variable হিসেবে সেট করুন!")
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # রেন্ডারে পোলিং স্টার্ট
    print("বট রেডি...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()