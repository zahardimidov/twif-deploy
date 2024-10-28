import asyncio
import json
import os
import ssl

import certifi
import redis
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, URLInputFile
from aiohttp import ClientSession
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
BOT_TOKEN = os.environ.get('BOT_TOKEN')  # Исправлено на получение токена бота
BACKEND_HOST = os.environ.get('BACKEND_HOST')

sslcontext = ssl.create_default_context(cafile=certifi.where())

r = redis.Redis(host=REDIS_HOST, port=6379, db=0)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(
    parse_mode=ParseMode.HTML))


async def send_message_to_users(users: list, message_data: dict):
    for user_id in users:
        try:
            photo = None if not message_data.get('photo') else BACKEND_HOST + '/media/message/' + message_data['photo'].split('/')[-1]
            
            if message_data.get('buttons'):
                buttons = []
                for btn in message_data['buttons']:
                    buttons.append([
                        InlineKeyboardButton(text=btn['label'], url=btn['url'])
                    ])
                markup = InlineKeyboardMarkup(inline_keyboard=buttons)

                if photo:
                    await bot.send_photo(user_id, photo=URLInputFile(url=photo), caption=message_data['text'], reply_markup=markup)
                else:
                    await bot.send_message(user_id, text=message_data['text'], reply_markup=markup)
            elif photo:
                await bot.send_photo(user_id, photo=URLInputFile(url=photo), caption=message_data['text'])
            else:
                await bot.send_message(user_id, message_data['text'])
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")


async def process_tasks():
    while True:
        task: bytes = r.lpop('spread_message')
        if task is not None:
            async with ClientSession() as session:
                pk = task.decode()
                response = await session.get(BACKEND_HOST + f'/messages/get?pk={pk}', ssl=sslcontext)
                message = await response.json()

                print(f'{message=}')
                
                response = await session.get(BACKEND_HOST + f'/users/all', ssl=sslcontext)
                users = (await response.json())['users']

                print(f'{users=}')

            await send_message_to_users(users, message)
        else:
            await asyncio.sleep(3)  # Ждем 1 секунду перед следующей проверкой

async def check_users_requirements():
    while True:
        try:
            async with ClientSession() as session:
                response = await session.get(BACKEND_HOST + f'/users/all', ssl=sslcontext)
                users = (await response.json())['users']

                seconds_per_hour = 3600 /360
                sleep = seconds_per_hour / len(users)

                for user_id in users:
                    response = await session.get(BACKEND_HOST + f'/party/get_user_party?user_id={user_id}', ssl=sslcontext)

                    if response.status == 200:
                        party = await response.json()

                        res = await session.get(BACKEND_HOST + f'/party/check_user_party_requirements?user_id={user_id}&party_id={party["id"]}', ssl=sslcontext)

                        if res.status != 200:
                            print(await res.json())
                    
                    await asyncio.sleep(sleep)
        except Exception as e:
            print(e)

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.create_task(check_users_requirements())

    loop.run_until_complete(process_tasks())


if __name__ == "__main__":
    run_bot()
