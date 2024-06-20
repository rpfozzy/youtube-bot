import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytube import YouTube
from moviepy.editor import AudioFileClip
import os
import requests

token = '6805284889:AAGL4cMNt9sciYUxHMTRJDlamcGJPNjlbo8'
bot = telebot.TeleBot(token)
user_state = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Отправьте ссылку на видео с YouTube для скачивания.")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    link = message.text
    if 'youtube.com/watch' in link or 'youtu.be/' in link:
        try:
            yt = YouTube(link)
            video_title = yt.title
            thumbnail_url = yt.thumbnail_url
            keyboard = InlineKeyboardMarkup()
            resolutions = ['144p', '240p', '360p', '480p', '540p', '720p', '720p60', '920p', '1080p', '1080p60']
            
            for res in resolutions:
                stream = yt.streams.filter(res=res.replace('60', ''), fps=60 if '60' in res else None, file_extension='mp4').first()
                if stream:
                    size = round(stream.filesize / (1024 * 1024), 2)
                    button_text = f'{res} MP4 ({size} MB)'
                    callback_data = f'download|{stream.itag}'
                    keyboard.add(InlineKeyboardButton(button_text, callback_data=callback_data))
            
            audio_stream = yt.streams.filter(only_audio=True).first()
            if audio_stream:
                audio_size = round(audio_stream.filesize / (1024 * 1024), 2)
                keyboard.add(InlineKeyboardButton(f'320kbps .mp3 ({audio_size} MB)', callback_data=f'download_audio|{audio_stream.itag}'))

            bot.send_photo(message.chat.id, thumbnail_url, caption=f"Видео: {video_title}")
            bot.send_message(message.chat.id, "Выберите разрешение для скачивания:", reply_markup=keyboard)

            user_state[message.chat.id] = {
                'link': link,
                'title': video_title,
                'thumbnail_url': thumbnail_url
            }
        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка при обработке видео. Проверьте ссылку и попробуйте снова.\nОшибка: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('download|'))
def handle_download(call):
    try:
        chat_id = call.message.chat.id
        if chat_id not in user_state or 'link' not in user_state[chat_id]:
            bot.send_message(chat_id, "Ошибка состояния. Попробуйте снова.")
            return

        itag = call.data.split('|')[1]
        link = user_state[chat_id]['link']
        video_title = user_state[chat_id]['title']
        thumbnail_url = user_state[chat_id]['thumbnail_url']

        yt = YouTube(link)
        stream = yt.streams.get_by_itag(itag)
        filename = stream.default_filename
        stream.download(filename=filename)

        thumbnail_path = 'thumbnail.jpg'
        with open(thumbnail_path, 'wb') as thumb_file:
            thumb_file.write(requests.get(thumbnail_url).content)

        with open(filename, 'rb') as file:
            bot.send_video(chat_id, file, thumb=open(thumbnail_path, 'rb'), caption=video_title)

        bot.send_message(chat_id, f"Скачивание завершено. Видео сохранено как {filename}.")
        os.remove(filename)
        os.remove(thumbnail_path)
        user_state.pop(chat_id)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Ошибка при скачивании видео. Попробуйте снова.\nОшибка: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('download_audio|'))
def handle_download_audio(call):
    try:
        chat_id = call.message.chat.id
        if chat_id not in user_state or 'link' not in user_state[chat_id]:
            bot.send_message(chat_id, "Ошибка состояния. Попробуйте снова.")
            return

        itag = call.data.split('|')[1]
        link = user_state[chat_id]['link']
        video_title = user_state[chat_id]['title']

        yt = YouTube(link)
        stream = yt.streams.get_by_itag(itag)
        filename = stream.default_filename
        stream.download(filename=filename)

        audio = AudioFileClip(filename)
        audio_filename = filename.replace('.mp4', '.mp3')
        audio.write_audiofile(audio_filename, codec='libmp3lame', bitrate='320k')

        with open(audio_filename, 'rb') as audio_file:
            bot.send_audio(chat_id, audio_file, caption=video_title)

        bot.send_message(chat_id, f"Скачивание завершено. Аудио сохранено как {audio_filename}.")
        os.remove(filename)
        os.remove(audio_filename)
        user_state.pop(chat_id)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Ошибка при скачивании аудио. Попробуйте снова.\nОшибка: {str(e)}")

bot.polling()
