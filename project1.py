import os
import json
import uuid
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# — Настройки —
BOT_TOKEN = os.getenv("BOT_TOKEN") or "token from tg"
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID") or 882607004)
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID") or -1002533354742)

PENDING_FILE = "pending_requests.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# — Загрузка заявок из файла —
try:
    with open(PENDING_FILE, "r", encoding="utf-8") as f:
        pending_requests = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    pending_requests = {}

def save_pending():
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(pending_requests, f, ensure_ascii=False, indent=2)

# — Одноразовые ссылки —
one_time_links = {}

# — Команда /start —
@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Запросить доступ в канал", callback_data="request_access")]
    ])
    await m.answer("Нажмите, чтобы запросить доступ в канал:", reply_markup=kb)

# — Пользователь нажал “Запросить доступ” —
@dp.callback_query(F.data == "request_access")
async def request_access(cq: types.CallbackQuery):
    user = cq.from_user
    request_id = str(uuid.uuid4())
    pending_requests[request_id] = user.id
    save_pending()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{request_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline:{request_id}")
        ]
    ])
    text = (
        f"Новая заявка на доступ:\n"
        f"<b>{user.full_name}</b> (<code>{user.id}</code>)\n"
        f"request_id: <code>{request_id}</code>"
    )
    await bot.send_message(ADMIN_CHAT_ID, text, parse_mode="HTML", reply_markup=kb)
    await cq.answer("Заявка отправлена администратору.")

# — Админ одобряет заявку —
@dp.callback_query(F.data.startswith("approve:"))
async def approve(cq: types.CallbackQuery):
    if cq.from_user.id != ADMIN_CHAT_ID:
        return await cq.answer("Недостаточно прав.", show_alert=True)

    request_id = cq.data.split(":", 1)[1]
    user_id = pending_requests.pop(request_id, None)
    save_pending()

    if not user_id:
        return await cq.answer("Заявка не найдена или уже обработана.", show_alert=True)

    expire = datetime.now() + timedelta(minutes=2)
    link = await bot.create_chat_invite_link(
        chat_id=TARGET_CHANNEL_ID,
        member_limit=1,
        expire_date=expire
    )
    one_time_links[link.invite_link] = True

    await bot.send_message(
        user_id,
        f"Ваша одноразовая ссылка для входа в канал (действует 2 минуты):\n{link.invite_link}"
    )
    await cq.message.edit_text(cq.message.text + "\n\n✅ Одобрено")
    await cq.answer()

# — Админ отклоняет заявку с возможностью повторить запрос —
@dp.callback_query(F.data.startswith("decline:"))
async def decline(cq: types.CallbackQuery):
    if cq.from_user.id != ADMIN_CHAT_ID:
        return await cq.answer("Недостаточно прав.", show_alert=True)

    request_id = cq.data.split(":", 1)[1]
    user_id = pending_requests.pop(request_id, None)
    save_pending()

    # Кнопка для повторной заявки
    kb_retry = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="request_access")]
    ])
    if user_id:
        await bot.send_message(user_id, "Ваш запрос отклонён.", reply_markup=kb_retry)

    await cq.message.edit_text(cq.message.text + "\n\n❌ Отклонено")
    await cq.answer()

# — Проверка ссылки вручную (опционально) —
@dp.message(Command("join"))
async def cmd_join(m: types.Message):
    invite = m.get_args().strip()
    if one_time_links.pop(invite, None):
        await m.reply("Ссылка принята! Добро пожаловать в канал.")
    else:
        await m.reply("Неверная или истёкшая ссылка.")



if __name__ == "__main__":
    dp.run_polling(bot, skip_updates=True)
