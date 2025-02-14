import aiosqlite
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import F


# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Замените "YOUR_BOT_TOKEN" на токен, который вы получили от BotFather
API_TOKEN = ''

# Объект бота
bot = Bot(token=API_TOKEN)
# Диспетчер
dp = Dispatcher()

# Зададим имя базы данных
DB_NAME = 'quiz_bot.db'

# Структура квиза
quiz_data = [
    {
        'question': 'Что такое Python?',
        'options': ['Язык программирования', 'Фреймворк', 'Иностранный язык', 'Викторина'],
        'correct_option': 0
    },
    {
        'question': 'Какой тип данных используется для хранения целых чисел?',
        'options': ['str', 'int', 'bool', 'float'],
        'correct_option': 1
    },
    {
        'question': 'Выбери из списка тот вариант, который НЕ является нейронной сетью:',
        'options': ['DeepSeek', 'ChatGPT', 'YandexGPT', 'Генератор случайных чисел'],
        'correct_option': 3
    },
    {
        'question': 'Выбери из списка тот вариант, который НЕ является языком программирования:',
        'options': ['Python', 'Java', 'HTML', 'C#'],
        'correct_option': 2
    },
    {
        'question': 'Кто основал язык программирования Python?',
        'options': ['Гвидо ван Россум', 'Илон Маск', 'Стив Джобс', 'Билл Гейтс'],
        'correct_option': 0
    },
    {
        'question': 'Какой язык программирования является самым часто используемым?',
        'options': ['Python', 'C++', 'Java', 'JS'],
        'correct_option': 0
    },
    {
        'question': 'Выбери из списка тот вариант, который НЕ является фреймворком, созданном на основе Python:',
        'options': ['Django', 'Flask', 'Kivy', 'ASP.NET Core'],
        'correct_option': 3
    },
    {
        'question': 'В каком году был основан язык программирования Python?',
        'options': ['1989', '2001', '1991', '1984'],
        'correct_option': 0
    },
    {
        'question': 'На каком языке программирования написан ChatGPT?',
        'options': ['C++', 'Python', 'Java', 'C#'],
        'correct_option': 1
    },
    {
        'question': 'Кто является основателем DeepSeek?',
        'options': ['Лян Вэньфэн', 'Сергей Брин', 'Ларри Пейдж', 'Том Престон-Вернер'],
        'correct_option': 0
    },
]


# Генерация клавиатуры с вариантами ответов
def generate_options_keyboard(answer_options, correct_option_index):
    builder = InlineKeyboardBuilder()
    for index, option in enumerate(answer_options):
        builder.add(types.InlineKeyboardButton(
            text=option,
            callback_data=f"answer_{index}"  # Уникальный идентификатор для каждого варианта
        ))
    builder.adjust(1)
    return builder.as_markup()

# Получение текущего индекса вопроса
async def get_quiz_index(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = ?', (user_id,)) as cursor:
            results = await cursor.fetchone()
            return results[0] if results else 0

#Обновление индекса вопроса
async def update_quiz_index(user_id, index):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index) VALUES (?, ?)', (user_id, index))
        await db.commit()

# Сохранение ответа пользователя
async def save_user_answer(user_id, question_index, is_correct):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT INTO quiz_answers (user_id, question_index, is_correct) VALUES (?, ?, ?)',
                         (user_id, question_index, int(is_correct)))
        await db.commit()

# Подсчет правильных ответов
async def calculate_score(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT COUNT(*) FROM quiz_answers WHERE user_id = ? AND is_correct = 1', (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

# Сохранение результата квиза
async def save_quiz_result(user_id, score):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR REPLACE INTO quiz_results (user_id, score, last_played) VALUES (?, ?, datetime("now"))',
                         (user_id, score))
        await db.commit()

# Получение текущего вопроса
async def get_question(message, user_id):
    current_question_index = await get_quiz_index(user_id)
    correct_index = quiz_data[current_question_index]['correct_option']
    opts = quiz_data[current_question_index]['options']
    kb = generate_options_keyboard(opts, opts[correct_index])
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)

# Класс для обработки ответов
class QuizHandler:
    def __init__(self, dp, quiz_data, get_quiz_index, update_quiz_index, save_user_answer, calculate_score, save_quiz_result, get_question):
        self.dp = dp
        self.quiz_data = quiz_data
        self.get_quiz_index = get_quiz_index
        self.update_quiz_index = update_quiz_index
        self.save_user_answer = save_user_answer
        self.calculate_score = calculate_score
        self.save_quiz_result = save_quiz_result
        self.get_question = get_question

        # Регистрируем обработчики
        self.dp.callback_query(F.data.startswith("answer_"))(self.handle_answer)

    async def handle_answer(self, callback: types.CallbackQuery):
        # Удаляем кнопки
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.from_user.id,
            message_id=callback.message.message_id,
            reply_markup=None
        )

        # Получаем индекс выбранного ответа из callback_data
        selected_index = int(callback.data.split("_")[1])

        # Получаем текст выбранного ответа
        selected_answer = callback.message.reply_markup.inline_keyboard[selected_index][0].text

        # Определяем, правильный ли ответ
        current_question_index = await self.get_quiz_index(callback.from_user.id)
        correct_option_index = self.quiz_data[current_question_index]['correct_option']
        is_correct = selected_index == correct_option_index

        # Выводим текст ответа пользователя
        await callback.message.answer(f"Вы выбрали: {selected_answer}\n{'Верно!' if is_correct else 'Неправильно.'}")

        # Сохраняем ответ
        await self.save_user_answer(callback.from_user.id, current_question_index, is_correct)

        # Если ответ неправильный, показываем правильный ответ
        if not is_correct:
            correct_option = self.quiz_data[current_question_index]['options'][correct_option_index]
            await callback.message.answer(f"Правильный ответ: {correct_option}")

        # Обновление номера текущего вопроса в базе данных
        current_question_index += 1
        await self.update_quiz_index(callback.from_user.id, current_question_index)

        if current_question_index < len(self.quiz_data):
            await self.get_question(callback.message, callback.from_user.id)
        else:
            # Сохраняем результат (всего правильных ответов)
            score = await self.calculate_score(callback.from_user.id)
            await self.save_quiz_result(callback.from_user.id, score)
            await callback.message.answer(f"Это был последний вопрос. Квиз завершен! Ваш результат: {score}/{len(self.quiz_data)}")

# Создаем экземпляр класса QuizHandler
quiz_handler = QuizHandler(
    dp=dp,
    quiz_data=quiz_data,
    get_quiz_index=get_quiz_index,
    update_quiz_index=update_quiz_index,
    save_user_answer=save_user_answer,
    calculate_score=calculate_score,
    save_quiz_result=save_quiz_result,
    get_question=get_question
)

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать квиз"))
    await message.answer("Добро пожаловать на квиз! Для старта нажмите на кнопку 'Начать квиз'!", reply_markup=builder.as_markup(resize_keyboard=True))

# Команда /quiz
@dp.message(F.text == "Начать квиз")
@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    await message.answer(f"Давайте начнем квиз! Всего будет {len(quiz_data)} вопросов.")
    await new_quiz(message)

# Создание таблиц в базе данных
async def create_table():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS quiz_state
                           (user_id INTEGER PRIMARY KEY, question_index INTEGER)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS quiz_results
                           (user_id INTEGER PRIMARY KEY, score INTEGER, last_played TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS quiz_answers
                           (user_id INTEGER, question_index INTEGER, is_correct INTEGER)''')
        await db.commit()

# Начало нового квиза
async def new_quiz(message):
    user_id = message.from_user.id
    await update_quiz_index(user_id, 0)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM quiz_answers WHERE user_id = ?', (user_id,))
        await db.commit()
    await get_question(message, user_id)

# Запуск бота
async def main():
    await create_table()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())