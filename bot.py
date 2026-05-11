import discord
from discord.ext import commands
import random
import asyncio
import re
from collections import defaultdict
from datetime import datetime, timedelta

# ТОКЕН ВАШЕГО БОТА
TOKEN = 'MTIzODc4ODM0NDkyNjk2NTgzMQ.GaB5Nk.7T1lTDMzFzUlWZJ3Z96LTqIW2Zp3gOb7-x2kno'

# Настройка бота
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Хранилище сообщений
message_history = defaultdict(list)  # История сообщений по каналам
word_bank = []  # Банк слов

# Настройки для рандомной отправки
RANDOM_MESSAGE_INTERVAL = 60  # Секунды между автоматическими сообщениями (можно изменить)
auto_message_enabled = True  # Включена ли автоматическая отправка

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

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен!')
    print(f'📡 На {len(bot.guilds)} серверах')
    print(f'🕐 Рандомная отправка чужих сообщений каждые {RANDOM_MESSAGE_INTERVAL} секунд')
    print('=' * 50)
    
    # Запускаем фоновую задачу для рандомной отправки сообщений
    bot.loop.create_task(random_message_sender())

async def random_message_sender():
    """Функция для рандомной отправки чужих сообщений в каналы"""
    await bot.wait_until_ready()
    
    while not bot.is_closed():
        if auto_message_enabled:
            # Перебираем все серверы и каналы
            for guild in bot.guilds:
                for channel in guild.text_channels:
                    # Проверяем права бота на отправку сообщений
                    if channel.permissions_for(guild.me).send_messages:
                        # Получаем историю сообщений канала
                        if message_history[channel.id]:
                            # Шанс 30% что бот отправит сообщение в этот канал
                            if random.random() < 0.3:
                                # Выбираем случайное сообщение из истории
                                old_message = random.choice(message_history[channel.id])
                                
                                # Не отправляем слишком короткие сообщения
                                if len(old_message['text']) > 5:
                                    # Добавляем небольшую задержку перед отправкой
                                    await asyncio.sleep(random.uniform(1, 5))
                                    
                                    try:
                                        # Форматируем сообщение (иногда добавляем кавычки)
                                        if random.random() < 0.5:
                                            final_message = f'*"{old_message["text"]}"* - {old_message["author"]} когда-то сказал...'
                                        else:
                                            final_message = old_message['text']
                                        
                                        await channel.send(final_message)
                                        print(f'📨 Отправлено в #{channel.name}: {final_message[:50]}...')
                                        
                                        # Небольшая задержка между отправками в разные каналы
                                        await asyncio.sleep(2)
                                        
                                    except Exception as e:
                                        print(f'❌ Ошибка отправки: {e}')
        
        # Ждем следующий цикл
        await asyncio.sleep(RANDOM_MESSAGE_INTERVAL)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Сохраняем сообщение в историю (только обычные сообщения, не команды)
    if not message.content.startswith('!'):
        clean_content = message.content.lower()
        words = re.findall(r'\b[а-яa-z0-9]+\b', clean_content)
        
        message_info = {
            'text': message.content,  # Оригинальный текст
            'clean_text': clean_content,
            'words': words,
            'author': message.author.name,
            'author_id': message.author.id,
            'timestamp': datetime.now()
        }
        
        message_history[message.channel.id].append(message_info)
        word_bank.extend(words)
        
        # Ограничиваем историю 200 сообщениями
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

# КОМАНДА: Включить/выключить автоматическую отправку
@bot.command(name='авто')
async def toggle_auto(ctx, status: str = None):
    """Включить/выключить автоматическую отправку. Пример: !авто вкл"""
    global auto_message_enabled
    
    if status and status.lower() in ['вкл', 'on', 'да', 'true']:
        auto_message_enabled = True
        await ctx.send("✅ Автоматическая отправка чужих сообщений **ВКЛЮЧЕНА**!")
    elif status and status.lower() in ['выкл', 'off', 'нет', 'false']:
        auto_message_enabled = False
        await ctx.send("❌ Автоматическая отправка чужих сообщений **ВЫКЛЮЧЕНА**!")
    else:
        status_text = "включена" if auto_message_enabled else "выключена"
        await ctx.send(f"🔄 Автоматическая отправка сейчас **{status_text}**")

# КОМАНДА: Ручная отправка случайного сообщения
@bot.command(name='вспомни')
async def recall_random(ctx):
    """Отправить случайное сообщение из истории прямо сейчас"""
    channel_history = message_history[ctx.channel.id]
    
    if len(channel_history) < 3:
        await ctx.send("❌ Недостаточно сообщений в этом канале! (нужно минимум 3)")
        return
    
    # Выбираем случайное сообщение
    old_msg = random.choice(channel_history)
    
    # Иногда показываем автора
    if random.random() < 0.3:
        await ctx.send(f'*"{old_msg["text"]}"* — {old_msg["author"]}')
    else:
        await ctx.send(old_msg['text'])

# КОМАНДА: Показать статистику по сообщениям
@bot.command(name='статистика')
async def message_stats(ctx):
    """Показать сколько сообщений сохранено в этом канале"""
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

# КОМАНДА: Пропустить и отправить сейчас
@bot.command(name='отправь')
async def force_send(ctx):
    """Принудительно отправить случайное сообщение сейчас"""
    channel_history = message_history[ctx.channel.id]
    
    if not channel_history:
        await ctx.send("❌ Нет сохраненных сообщений!")
        return
    
    old_msg = random.choice(channel_history)
    await ctx.send(f'📢 {old_msg["text"]}')
    await ctx.send(f"*(Напомнил {old_msg['author']})*")

# КОМАНДА: Собрать из слов
@bot.command(name='собери')
async def make_message(ctx):
    """Собирает случайное сообщение из слов других участников"""
    if len(word_bank) < 5:
        await ctx.send("❌ Недостаточно слов в банке! Нужно больше сообщений.")
        return
    
    num_words = random.randint(4, 10)
    random_words = random.sample(word_bank, min(num_words, len(word_bank)))
    
    result = ' '.join(random_words)
    if result:
        result = result[0].upper() + result[1:]
    
    await ctx.send(f'🤖 **{result}**')

# Остальные команды из предыдущего скрипта (стиль, триггеры и т.д.)

# Запуск
if __name__ == '__main__':
    bot.run(TOKEN)
