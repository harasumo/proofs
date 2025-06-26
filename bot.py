import asyncio
import subprocess
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from config import TELEGRAM_TOKEN

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

class FormFilling(StatesGroup):
    waiting_for_form_url = State()
    waiting_for_field_values = State()

def get_main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Заполнить Google Форму")],
            [KeyboardButton(text="❌ Отменить заполнение")]
        ],
        resize_keyboard=True
    )
    return keyboard

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Привет! Нажми '📝 Заполнить Google Форму', чтобы я помог заполнить форму.",
        reply_markup=get_main_menu()
    )

@dp.message(F.text == "📝 Заполнить Google Форму")
async def ask_form_url(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, отправь ссылку на Google Форму.")
    await state.set_state(FormFilling.waiting_for_form_url)

@dp.message(F.text == "❌ Отменить заполнение")
async def cancel_filling(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Заполнение формы отменено.", reply_markup=get_main_menu())

@dp.message(FormFilling.waiting_for_form_url)
async def analyze_form(message: Message, state: FSMContext):
    form_url = message.text.strip()
    if not form_url.startswith("http"):
        await message.answer("⚠️ Пожалуйста, отправь корректную ссылку на Google Форму.")
        return

    await message.answer("🔍 Анализирую форму...")
    try:
        result = subprocess.run(
            ["python3", "rpa_fill_google_form.py", "analyze", form_url],
            capture_output=True,
            text=True
        )
        num_fields = int(result.stdout.strip())
        if num_fields == 0:
            await message.answer("⚠️ В форме не найдено ни одного текстового поля. Попробуй другую ссылку.")
            await state.clear()
            return

        await state.update_data(form_url=form_url, num_fields=num_fields, field_values=[])
        await message.answer(f"✅ В форме найдено {num_fields} текстовых полей. Давай заполним их по порядку.\nЧто ввести в первое поле?")
        await state.set_state(FormFilling.waiting_for_field_values)
    except Exception as e:
        await message.answer(f"⚠️ Произошла ошибка при анализе формы: {e}")
        await state.clear()

@dp.message(FormFilling.waiting_for_field_values)
async def collect_field_values(message: Message, state: FSMContext):
    data = await state.get_data()
    field_values = data.get('field_values', [])
    num_fields = data.get('num_fields', 0)

    field_values.append(message.text.strip())
    if len(field_values) < num_fields:
        await state.update_data(field_values=field_values)
        await message.answer(f"Что ввести в поле №{len(field_values)+1}?")
    else:
        await state.update_data(field_values=field_values)
        form_url = data.get('form_url')

        # Подтверждение перед запуском
        result_message = "🚀 Отлично! Я заполню форму с этими данными:\n"
        for idx, value in enumerate(field_values, start=1):
            result_message += f"{idx}️⃣ {value}\n"
        result_message += f"Форма: {form_url}\n\nЗапускаю скрипт..."

        await message.answer(result_message)

        try:
            result = subprocess.run(
                ["python3", "rpa_fill_google_form.py", "fill", form_url] + field_values,
                capture_output=True,
                text=True
            )
            await message.answer(f"Результат:\n{result.stdout}")
        except Exception as e:
            await message.answer(f"⚠️ Ошибка при запуске RPA-скрипта: {e}")

        await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
