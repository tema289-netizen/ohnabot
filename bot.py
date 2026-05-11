import discord
from discord.ext import commands
import random
import asyncio
import re
import os
from collections import defaultdict
from datetime import datetime
from flask import Flask, jsonify
from threading import Thread

# ТОКЕН берется из переменных окружения на Render
TOKEN = os.environ.get('BOT_TOKEN')

# Настройка бота
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Создаем Flask приложение для веб-сервера
app = Flask('')

# Хранилище сообщений
message_history = defaultdict(list)
word_bank = []

# Настройки для рандомной отправки
RANDOM_MESSAGE_INTERVAL = 60
auto_message_enabled = True

# Слова для триггеров
TRIGGERS = {
    'дубду': 'ДБДДЕДИУМ! 🔪',
    'дбд': 'ДБДДЕДИУМ! 🔪',
    'dbd': 'ДБДДЕДИУМ! 🔪',
    'го в': 'В ГООО! 🔥',
    'гоу в': 'В ГООО! 🔥',
    'килл': '🔪 ВСЕХ УБЬЮ! 🔪',
    'ран': '🏃 БЕГИ БЕГИ БЕГИ! 🏃'
}

# ========== ВЕБ-СЕРВЕР ДЛЯ RENDER ==========
@app.route('/')
def home():
    """Главная страница для проверки работы бота"""
    return jsonify({
        'status': 'online',
        'bot': str(bot.user) if bot.user else 'starting',
        'servers': len(bot.guilds),
        'auto_message': auto_message_enabled,
        'messages_stored': sum(len(msgs) for msgs in message_history.values())
    })

@app.route('/ping')
def ping():
    """Проверка работоспособности"""
    return jsonify({'status': 'ok', 'message': 'pong'})

@app.route('/stats')
def stats():
    """Статистика работы бота"""
    return jsonify({
        'total_messages': sum(len(msgs) for msgs in message_history.values()),
        'total_words': len(word_bank),
        'auto_enabled': auto_message_enabled,
        'interval_seconds': RANDOM_MESSAGE_INTERVAL
    })

def run_web_server():
    """Запускает Flask веб-сервер в отдельном потоке"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ========== ФУНКЦИИ БОТА ==========
@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен!')
    print(f'📡 На {len(bot.guilds)} серверах')
    print(f'🕐 Рандомная отправка каждые {RANDOM_MESSAGE_INTERVAL} секунд')
    print(f'🌐 Веб-сервер запущен на порту {os.environ.get("PORT", 10000)}')
    print('=' * 50)
    
    # Запускаем фоновую задачу
    bot.loop.create_task(random_message_sender())

async def random_message_sender():
    """Функция для рандомной отправки чужих сообщений"""
    await bot.wait_until_ready()
    
    while not bot.is_closed():
        if auto_message_enabled:
            for guild in bot.guilds:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        if message_history[channel.id] and random.random() < 0.3:
                            old_message = random.choice(message_history[channel.id])
                            
                            if len(old_message['text']) > 5:
                                await asyncio.sleep(random.uniform(1, 3))
                                
                                try:
                                    if random.random() < 0.5:
                                        final_message = f'*"{old_message["text"]}"* - {old_message["author"]} когда-то сказал...'
                                    else:
                                        final_message = old_message['text']
                                    
                                    await channel.send(final_message)
                                    print(f'📨 Отправлено в #{channel.name}')
                                    await asyncio.sleep(1)
                                except Exception as e:
                                    print(f'❌ Ошибка: {e}')
        
        await asyncio.sleep(RANDOM_MESSAGE_INTERVAL)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Сохраняем сообщение в историю
    if not message.content.startswith('!'):
        clean_content = message.content.lower()
        words = re.findall(r'\b[а-яa-z0-9]+\b', clean_content)
        
        message_info = {
            'text': message.content,
            'clean_text': clean_content,
            'words': words,
            'author': message.author.name,
            'author_id': message.author.id,
            'timestamp': datetime.now()
        }
        
        message_history[message.channel.id].append(message_info)
        word_bank.extend(words)
        
        # Ограничиваем историю
        if len(message_history[message.channel.id]) > 200:
            old_msg = message_history[message.channel.id].pop(0)
            for word in old_msg['words']:
                if word in word_bank:
                    try:
                        word_bank.remove(word)
                    except ValueError:
                        pass
    
    # Проверяем триггеры
    msg_lower = message.content.lower()
    for trigger, response in TRIGGERS.items():
        if trigger in msg_lower:
            await message.channel.send(response)
            break
    
    await bot.process_commands(message)

# ========== КОМАНДЫ БОТА ==========
@bot.command(name='авто')
async def toggle_auto(ctx, status: str = None):
    global auto_message_enabled
    
    if status and status.lower() in ['вкл', 'on', 'да', 'true']:
        auto_message_enabled = True
        await ctx.send("✅ Автоматическая отправка **ВКЛЮЧЕНА**!")
    elif status and status.lower() in ['выкл', 'off', 'нет', 'false']:
        auto_message_enabled = False
        await ctx.send("❌ Автоматическая отправка **ВЫКЛЮЧЕНА**!")
    else:
        status_text = "включена" if auto_message_enabled else "выключена"
        await ctx.send(f"🔄 Авто-отправка сейчас **{status_text}**")

@bot.command(name='вспомни')
async def recall_random(ctx):
    channel_history = message_history[ctx.channel.id]
    
    if len(channel_history) < 3:
        await ctx.send("❌ Недостаточно сообщений! (нужно минимум 3)")
        return
    
    old_msg = random.choice(channel_history)
    
    if random.random() < 0.3:
        await ctx.send(f'*"{old_msg["text"]}"* — {old_msg["author"]}')
    else:
        await ctx.send(old_msg['text'])

@bot.command(name='статистика')
async def message_stats(ctx):
    count = len(message_history[ctx.channel.id])
    unique_users = len(set(msg['author'] for msg in message_history[ctx.channel.id]))
    
    embed = discord.Embed(
        title="📊 Статистика канала",
        color=discord.Color.blue()
    )
    embed.add_field(name="Сохранено сообщений", value=str(count), inline=True)
    embed.add_field(name="Уникальных авторов", value=str(unique_users), inline=True)
    embed.add_field(name="Интервал авто-отправки", value=f"{RANDOM_MESSAGE_INTERVAL} сек", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='отправь')
async def force_send(ctx):
    channel_history = message_history[ctx.channel.id]
    
    if not channel_history:
        await ctx.send("❌ Нет сохраненных сообщений!")
        return
    
    old_msg = random.choice(channel_history)
    await ctx.send(f'📢 {old_msg["text"]}')
    await ctx.send(f"*(Напомнил {old_msg['author']})*")

@bot.command(name='собери')
async def make_message(ctx):
    if len(word_bank) < 5:
        await ctx.send("❌ Недостаточно слов в банке!")
        return
    
    num_words = random.randint(4, 10)
    random_words = random.sample(word_bank, min(num_words, len(word_bank)))
    
    result = ' '.join(random_words)
    if result:
        result = result[0].upper() + result[1:]
    
    await ctx.send(f'🤖 **{result}**')

@bot.command(name='триггеры')
async def show_triggers(ctx):
    if not TRIGGERS:
        await ctx.send("Нет активных триггеров")
        return
    
    trigger_list = '\n'.join([f'• `{t}` → {r}' for t, r in TRIGGERS.items()])
    embed = discord.Embed(
        title="🔔 Активные триггеры",
        description=trigger_list,
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    # Запускаем веб-сервер в отдельном потоке
    web_thread = Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    
    # Запускаем Discord бота
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ОШИБКА: Токен не найден!")
        print("Добавьте переменную окружения BOT_TOKEN на Render!")
