 
import myjdapi
import time
import os
import subprocess
import random
from swibots import BotApp
from pyrogram import Client, filters
from pyrogram.types import (ReplyKeyboardMarkup, InlineKeyboardMarkup,
                            InlineKeyboardButton)
import asyncio
import logging
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

logging.info('Waiting for JD To Start')
time.sleep(60)


api_id = os.environ.get('TELEGRAM_API', '')
if len(api_id) == 0:
    logging.error("TELEGRAM_API variable is missing! Exiting now")
    exit(1)

api_hash = os.environ.get('TELEGRAM_HASH', '')
if len(api_hash) == 0:
    logging.error("TELEGRAM_HASH variable is missing! Exiting now")
    exit(1)
    
bot_token = os.environ.get('BOT_TOKEN', '')
if len(bot_token) == 0:
    logging.error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

dump_id = os.environ.get('DUMP_CHAT_ID', '')
if len(dump_id) == 0:
    logging.error("DUMP_CHAT_ID variable is missing! Exiting now")
    exit(1)
else:
    dump_id = int(dump_id)


        

async def upload_progress_handler(progress):
    logging.info(f"Upload progress: {format_bytes(progress.readed + progress.current)}")

async def progress(current, total):
    logging.info(f"{current * 100 / total:.1f}%")
    
async def tg_upload(file, chat_id,thumbnail, link=""):
    logging.info("Getting Duration for TG Upload")                                  
    dur = get_video_duration(file)
    res = await app.send_video(
        chat_id=chat_id,
        video=file,
        caption=f"{os.path.basename(file)}",
        thumb=thumbnail,
        file_name=os.path.basename(file),
        duration=dur,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Direct Download Link", url=link)]]),
        progress=progress
    )
    
    return res


async def switch_upload(file, thumbnail):
    res = await bot.send_media(
        message=f"{os.path.basename(file)}",
        document=file,
        description=file,
        thumb=thumbnail,
        part_size=50 * 1024 * 1024,
        task_count=10,
        progress=upload_progress_handler
    )    
    return res


def connect_to_jd(app_key, email, password):
    jd = myjdapi.Myjdapi()
    jd.set_app_key(app_key)

    connected = False
    while not connected:
        try:
            jd.connect(email, password)
            jd.update_devices()
            connected = True
        except myjdapi.exception.MYJDConnectionException as e:
            logging.error(f"Failed to connect to My.JDownloader: {e}")
            logging.info("Retrying in 10 seconds...")
            time.sleep(10)

    return jd


def clear_downloads(device):
    try:
        downloads = device.downloads.query_links()
        for i in downloads:
            device.downloads.remove_links([i["uuid"]], [i['packageUUID']])
    except myjdapi.exception.MYJDConnectionException as e:
        logging.error(f"Failed to clear downloads: {e}")


def format_bytes(byte_count):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    index = 0
    while byte_count >= 1024 and index < len(suffixes) - 1:
        byte_count /= 1024
        index += 1
    return f"{byte_count:.2f} {suffixes[index]}"


def get_video_duration(file_name):
    command = ['ffmpeg', '-i', file_name, '-hide_banner']
    result = subprocess.run(command, stderr=subprocess.PIPE, text=True)
    duration_line = [x for x in result.stderr.split('\n') if 'Duration' in x]
    if duration_line:
        duration = duration_line[0].split()[1]
        h, m, s = duration.split(':')
        total_seconds = int(h) * 3600 + int(m) * 60 + float(s[:-1])
        return total_seconds
    return None


def gen_thumb(file_name, output_filename, retry_interval=10, max_retries=10):
    retries = 0
    while retries < max_retries:
        if os.path.exists(file_name):
            video_duration = get_video_duration(file_name)
            if video_duration is None:
                logging.error("Could not retrieve video duration.")
                return False

            random_time = random.uniform(0, video_duration)
            random_time_str = time.strftime('%H:%M:%S', time.gmtime(random_time))

            command = ['ffmpeg', '-ss', random_time_str, '-i', file_name, '-vframes', '1', output_filename]
            try:
                subprocess.run(command, check=True, capture_output=True, text=True)
                logging.info(f"Thumbnail saved as {output_filename} at {random_time_str}")
                return True
            except subprocess.CalledProcessError as e:
                logging.error(f"Error: {e}")
                logging.error(f"Command output: {e.output}")
                return False
        else:
            logging.info(f"File {file_name} does not exist. Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)
            retries += 1

    logging.error(f"{max_retries} retries.")
    return False


def obtener_links(device,url,user_id):
    folder = "/jdownloader/downloads"
    linkgrabber = device.linkgrabber
    res = linkgrabber.add_links([{
        "autostart": False,
        "links": url,
        "packageName": user_id,
        "extractPassword": None,
        "priority": "DEFAULT",
        "downloadPassword": None,
        "destinationFolder": folder,
        "overwritePackagizerRules": True
       }])
    return res 


#Telegram
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

#Switch
TOKEN = os.getenv("TOKEN")  # Set this environment variable
bot = BotApp(TOKEN)

#Connectimg to JD
APP_KEY = os.getenv("JD_APP_KEY")  # Set this environment variable
EMAIL = os.getenv("JD_EMAIL")  # Set this environment variable
PASSWORD = os.getenv("JD_PASSWORD")  # Set this environment variable

jd = connect_to_jd(APP_KEY, EMAIL, PASSWORD)
device = jd.get_device("TeraJD")
logging.info('Connected')
clear_downloads(device)
logging.info('Cleared Downloads')



@app.on_message(filters.command("start"))
async def start_command(client, message):
        reply_msg = await message.reply_text("Welcome to Spidy Jd Terabox Downloader..")
        await asyncio.sleep(2)
        reply_msg = await reply_msg.edit_text("This is Just A Prototype Project i Tried and May Have Many Bugs and Error Occurred While Downloading...,So Take it Easy and Report the Error")
        await asyncio.sleep(2)
        reply_msg = await reply_msg.edit_text("Send Any TeraBox link to Download ")

@app.on_message(filters.text)
async def handle_message(client, message):
    link = message.text.strip()
    reply_msg = await message.reply_text("Processing The Link")

    try:
        user_id = message.from_user.id
        video = obtener_links(device,link, user_id)
        logging.info('Collecting...')
        await asyncio.sleep(2)
        linkgrabber = device.linkgrabber
        while True:
            try:
                while linkgrabber.is_collecting():
                    await asyncio.sleep(2)
                link_list = linkgrabber.query_links()
                link_pkg = linkgrabber.query_packages()
                #await app.send_message(message.chat.id,str(link_list))
                dls = []
                package_ids = []
                link_ids = []

                downloads = device.downloads.query_links()

                download_files = [dic['name'] for dic in downloads]
                files = [dic['name'] for dic in link_list]
                #await app.send_message(message.chat.id,str(download_files))
                #await app.send_message(message.chat.id,str(files))
              
                for dic in link_list:
                        file = dic['name']
                        if file not in download_files:
                            dls.append(file)
                            package_ids.append(dic.get('packageUUID'))
                            link_ids.append(dic.get('uuid'))
                linkgrabber.move_to_downloadlist(link_ids, package_ids)
                uploaded = []
                downloaded = []
                logging.info(f"Downloading {video['id']}")
                reply_msg = await reply_msg.edit_text("Download Started\nYou Will Get Your File Soon")
                #await app.send_message(message.chat.id,str(video))
                while True:
                    try:
                        downloads = device.downloads.query_links()
                        #await app.send_message(message.chat.id,str(downloads))
                        old_dl = ""
                        count = 0
                        logging.info(f"{len(downloads)}|{len(downloaded)}|{len(uploaded)}")
                        if old_dl != f"{len(downloads)}|{len(downloaded)}|{len(uploaded)}":
                             old_dl = f"{len(downloads)}|{len(downloaded)}|{len(uploaded)}"
                        else:
                           count += 1
                        if count == 20:
                                 await reply_msg.edit_text("Error Occurred While Downloading...")
                                 return  
                        if len(downloads) == len(downloaded) and len(uploaded) == len(downloaded):
                            logging.info("Downloads and uploads completed")
                            return
                        for i in downloads:
                            logging.info(f"{i['uuid']}{i['packageUUID']}")
                            if 'status' in i and i['status'] == 'Finished':
                                logging.info(f"{i['uuid']} {i['packageUUID']}")
                                if i["name"] not in downloaded:
                                    file_path = f"downloads/{i['name']}"
                                    if os.path.exists(file_path):
                                        logging.info(f"{i['name']} is downloaded")
                                        downloaded.append(i["name"])
                                        thumbnail_name = f"""{i["name"]}_thumb.png"""
                                        logging.info("Generating Thumbnail")
                                        gen_thumb(file_path, thumbnail_name)
                                        logging.info("Generation Thumbnail Completed")                      
                                        logging.info("Uploading To Telegram")                                                               
                                        tg_msg = await tg_upload(file_path,message.chat.id,thumbnail_name,link)
                                        uploaded.append([i["name"],tg_msg.id])
                                        await asyncio.sleep(5)
                                        device.downloads.remove_links([i["uuid"]], [i['packageUUID']])
                                        os.remove(file_path)
                                        logging.info("File Removed")
                                        return
                        await asyncio.sleep(5)
                    except myjdapi.exception.MYJDConnectionException as e:
                        logging.error(f"Failed to query downloads during download: {e}")
                        await asyncio.sleep(10)
                    except Exception as e:
                        logging.error(f"Error: {e}")
                        await asyncio.sleep(10)
            except Exception as e:
                logging.error(f"Error: {e}")
                await asyncio.sleep(10)
    except Exception as e:
        logging.error(f"Error handling message: {e}")
        await reply_msg.edit_text("Error Occurred While Downloading...")


        
        
if __name__ == "__main__":
    app.run()