import json
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- Твой токен ---
TOKEN = "7883022139:AAGz7VOUdmoC_dwr7_EumyxSFY74IEcjb1k"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()

DATA_FILE = "data.json"

# --- Функции сохранения/загрузки данных ---
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"tasks": [], "schedule": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- Главное меню ---
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Үй тапсырмасын қосу"), KeyboardButton(text="📋 Тізімді қарау")],
        [KeyboardButton(text="⏰ Еске салғыш"), KeyboardButton(text="🧹 Тазалау")],
        [KeyboardButton(text="🗓️ Сабақ кестесі"), KeyboardButton(text="🔗 Пайдалы сілтемелер")],
    ],
    resize_keyboard=True
)

# --- FSM состояния ---
class AddTask(StatesGroup):
    waiting_for_task = State()

class Schedule(StatesGroup):
    waiting_for_day = State()

class Reminder(StatesGroup):
    waiting_for_text = State()

# --- /start ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Сәлем 👋\nМен — студенттің көмекші құралымын!\n\n"
        "📚 /add - үй тапсырмасын қосу\n"
        "📋 /list - тапсырмалар тізімі\n"
        "🗓️ /schedule - сабақ кестесі\n"
        "⏰ /remind - еске салғыш орнату\n"
        "🧹 /clear - барлық тапсырмаларды өшіру\n"
        "🔗 /links - пайдалы сілтемелер",
        reply_markup=main_menu
    )

# --- /add ---
@dp.message(F.text.in_({"/add", "➕ Үй тапсырмасын қосу"}))
async def add_task(message: types.Message, state: FSMContext):
    await message.answer("✍️ Тапсырманы енгіз (мысалы: 'Информатика — 25 қазан')")
    await state.set_state(AddTask.waiting_for_task)

@dp.message(AddTask.waiting_for_task)
async def save_task(message: types.Message, state: FSMContext):
    data = load_data()
    data["tasks"].append(message.text)
    save_data(data)
    await message.answer("✅ Тапсырма қосылды!", reply_markup=main_menu)
    await state.clear()

# --- /list ---
@dp.message(F.text.in_({"/list", "📋 Тізімді қарау"}))
async def list_tasks(message: types.Message):
    data = load_data()
    if not data["tasks"]:
        await message.answer("📭 Тапсырмалар тізімі бос.", reply_markup=main_menu)
    else:
        tasks = "\n".join([f"{i+1}. {t}" for i, t in enumerate(data["tasks"])])
        await message.answer(f"📋 Үй тапсырмалары:\n\n{tasks}", reply_markup=main_menu)

# --- /clear ---
@dp.message(F.text.in_({"/clear", "🧹 Тазалау"}))
async def clear_tasks(message: types.Message):
    save_data({"tasks": [], "schedule": load_data().get("schedule", {})})
    await message.answer("🧹 Барлық тапсырмалар өшірілді!", reply_markup=main_menu)

# --- /links ---
@dp.message(F.text.in_({"/links", "🔗 Пайдалы сілтемелер"}))
async def links(message: types.Message):
    text = (
        "🌐 Пайдалы сілтемелер:\n\n"
        "🖥 [Canvas](http://canvas.narxoz.kz/)\n"
        "💼 [Platonus](https://platonus.narxoz.kz/)"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu)

# --- /schedule ---
week_days = ["Дүйсенбі", "Сейсенбі", "Сәрсенбі", "Бейсенбі", "Жұма"]

@dp.message(F.text.in_({"/schedule", "🗓️ Сабақ кестесі"}))
async def schedule(message: types.Message, state: FSMContext):
    chat_id = str(message.chat.id)
    data = load_data()
    if chat_id not in data["schedule"] or not data["schedule"][chat_id]:
        await message.answer("📅 Сабақ кестесі табылмады. Кеттік, орнатайық!")
        await state.update_data(day_index=0)
        await message.answer(f"{week_days[0]} күнінің пәндерін енгіз:")
        await state.set_state(Schedule.waiting_for_day)
    else:
        text = "🗓️ *Сенің сабақ кестең:*\n\n"
        for day, subjects in data["schedule"][chat_id].items():
            text += f"📘 {day}: {subjects}\n"
        await message.answer(text, parse_mode="Markdown", reply_markup=main_menu)

@dp.message(Schedule.waiting_for_day)
async def save_schedule(message: types.Message, state: FSMContext):
    data_state = await state.get_data()
    day_index = data_state["day_index"]
    chat_id = str(message.chat.id)
    data = load_data()

    if "schedule" not in data:
        data["schedule"] = {}
    if chat_id not in data["schedule"]:
        data["schedule"][chat_id] = {}

    data["schedule"][chat_id][week_days[day_index]] = message.text
    save_data(data)

    if day_index + 1 < len(week_days):
        await state.update_data(day_index=day_index + 1)
        await message.answer(f"{week_days[day_index + 1]} күнінің пәндерін енгіз:")
    else:
        await message.answer("✅ Кесте сақталды!", reply_markup=main_menu)
        await state.clear()

# --- /remind ---
@dp.message(F.text.in_({"/remind", "⏰ Еске салғыш"}))
async def remind(message: types.Message, state: FSMContext):
    await message.answer("⏰ Уақыт пен мәтінді енгіз (мысалы: 21:30 информатика жасау)")
    await state.set_state(Reminder.waiting_for_text)

@dp.message(Reminder.waiting_for_text)
async def set_reminder(message: types.Message, state: FSMContext):
    try:
        time_str, text = message.text.split(" ", 1)
        hour, minute = map(int, time_str.split(":"))
        now = datetime.now()
        remind_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if remind_time < now:
            remind_time = remind_time.replace(day=now.day + 1)

        scheduler.add_job(send_reminder, "date", run_date=remind_time, args=[message.chat.id, text])
        await message.answer(f"✅ Еске салғыш орнатылды: {time_str} — {text}", reply_markup=main_menu)
        await state.clear()
    except Exception:
        await message.answer("⚠️ Қате формат! Мысалы: 22:10 информатика жасау", reply_markup=main_menu)

async def send_reminder(chat_id, text):
    await bot.send_message(chat_id, f"🔔 Еске салғыш: {text}")

# --- Запуск ---
async def main():
    scheduler.start()
    print("✅ Бот іске қосылды!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
