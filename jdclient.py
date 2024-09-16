 
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

TOKEN = os.getenv("TOKEN")  # Set this environment variable
bot = BotApp(TOKEN)


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

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)


async def upload_progress_handler(progress):
    logging.info(f"Upload progress: {format_bytes(progress.readed + progress.current)}")

async def progress(current, total,arg):
    start = arg
    now = time.time()
    diff = now - start
    percentage = current * 100 / total
    speed = current / diff
    logging.info(f"{format_bytes(speed)}")
    
async def tg_upload(app,file, thumbnail, link,arg):
    logging.info("Getting Duration for TG Upload")                                  
    dur = get_video_duration(file)
    res = await app.send_video(
        chat_id=dump_id,
        video=file,
        caption=f"{os.path.basename(file)}",
        thumb=thumbnail,
        file_name=os.path.basename(file),
        duration=dur,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Direct Download Link", url=link)]]),
        progress=progress,
        progress_args=arg
    )
    return res


async def switch_upload(file, thumbnail):
    res = await bot.send_media(
        message=f"{os.path.basename(file)}",
        community_id=os.getenv("COMMUNITY_ID"),
        group_id=os.getenv("GROUP_ID"),
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


def obtener_links(device, url):
    folder = "/jdownloader/downloads"
    linkgrabber = device.linkgrabber
    linkgrabber.add_links([{
        "autostart": False,
        "links": url,
        "packageName": url.split("/")[4],
        "extractPassword": None,
        "priority": "DEFAULT",
        "downloadPassword": None,
        "destinationFolder": folder,
        "overwritePackagizerRules": True
    }])


async def main():
   async with app:
        APP_KEY = os.getenv("JD_APP_KEY")  # Set this environment variable
        EMAIL = os.getenv("JD_EMAIL")  # Set this environment variable
        PASSWORD = os.getenv("JD_PASSWORD")  # Set this environment variable

        jd = connect_to_jd(APP_KEY, EMAIL, PASSWORD)
        device = jd.get_device("ActionJD")
        logging.info('Connected')
        clear_downloads(device)
        logging.info('Cleared Downloads')
        obtener_links(device, "https://www.pornhub.com/model/mr-ms-vins/videos")
        logging.info('Collecting...')

        linkgrabber = device.linkgrabber
        while True:
            try:
                while linkgrabber.is_collecting():
                    await asyncio.sleep(2)

                link_list = linkgrabber.query_links()

                videos = []
                package_ids = []
                link_ids = []

                downloads = device.downloads.query_links()

                download_files = [dic['name'] for dic in downloads]
                files = [dic['name'] for dic in link_list]

                for dic in link_list:
                    file = dic['name']
                    if "480p" in file:
                        if file not in download_files:
                            videos.append(file)
                            package_ids.append(dic.get('packageUUID'))
                            link_ids.append(dic.get('uuid'))

                linkgrabber.move_to_downloadlist(link_ids, package_ids)
                linkgrabber.clear_list()
                uploaded = []
                downloaded = []
                logging.info("Downloading")
                while True:
                    try:
                        downloads = device.downloads.query_links()
                        old_dl = ""
                        count = 0
                        logging.info(f"{len(downloads)}|{len(downloaded)}|{len(uploaded)}")
                        if old_dl != f"{len(downloads)}|{len(downloaded)}|{len(uploaded)}":
                             old_dl = f"{len(downloads)}|{len(downloaded)}|{len(uploaded)}"
                        else:
                           count += 1
                        if count == 20:
                                 return
                
                             
                        if len(downloads) == len(downloaded) and len(uploaded) == len(downloaded):
                            logging.info("Downloads and uploads completed")
                            await asyncio.sleep(20)
                            clear_downloads(device)
                            clear_downloads(device)
                            await asyncio.sleep(10)
                            logging.info('Cleared Downloads')
                            return
                        for i in downloads:
                            if i['bytesTotal'] == i['bytesLoaded']:
                                if i["name"] not in downloaded:
                                    file_path = f"downloads/{i['name']}"
                                    if os.path.exists(file_path):
                                        logging.info(f"{i['name']} is downloaded")
                                        downloaded.append(i["name"])
                                        thumbnail_name = f"""{i["name"]}_thumb.png"""
                                        logging.info("Generating Thumbnail")
                                        gen_thumb(file_path, thumbnail_name)
                                        logging.info("Generation Thumbnail Completed")                      
                                        logging.info("Uploading To Switch")
                                        message = await switch_upload(file_path, thumbnail_name)
                                        while not message.media_link.startswith("http"):
                                            await asyncio.sleep(5)
                                        logging.info("Uploaded To Switch")
                                        logging.info("Uploading To Telegram")
                                        start = time.time()
                                        tg_msg = await tg_upload(app,file_path, thumbnail_name, message.media_link,(start,))
                                        uploaded.append([i["name"], message.media_link,tg_msg.id])
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

if __name__ == "__main__":
    app.run(main())
