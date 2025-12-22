# импорт библиотек
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import sqlite3
import json

# проверяем существует токен или нет 
def main():
    if not TOKEN:
        print("токен не найден")
        return

    import os
    # проверяем, существует ли файл базы данных
    if not os.path.exists("chefbot.db"):
        print("Файл базы данных не найден")
        return

# импортируем токен из файла config.py
try:
    from config import TOKEN
except ImportError:
    print("ошибочка, нет токена")
    TOKEN = None

# импорт функций бэка
from bot_back import (
    SearchHistory,
    search_in_database,
    get_recipe_from_db,
    get_similar_recipes,
    DB_FILE,
    HISTORY_FILE
)


# главное меню, создаём кнопку для поиска рецептов на старте 
def create_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Найти рецепт", callback_data="new_search")]
    ])

# создаём клавиатуру из кнопочек,основная менюшка из 4х кнопок 
def create_new_search_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Начать новый поиск", callback_data="start_search")],
        [InlineKeyboardButton("📋 История поиска", callback_data="show_history")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help_menu")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]
    ])

# кнопки под рецептами, навигация после просмотра рецепта 
def create_recipe_keyboard(recipe_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Найти новый рецепт", callback_data="new_search")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]
    ])


# команда старта, приветсвенное сообщение с инструкцией 
# обработка для большого количества пользователей
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Напиши продукты (каждый с новой строки):\n\n"
        "Пример:\nмакароны\nсыр\nкартошка\n\n"
        "Или нажми кнопку:",
        reply_markup=create_main_menu_keyboard(),
        parse_mode="Markdown"
    )

# обработка ввода продуктов 
async def handle_ingredients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    ingredients = [line.strip() for line in user_text.split('\n') if line.strip()]

    if not ingredients:
        await update.message.reply_text("Напиши продукты!")
        return

    await update.message.reply_text("🔍 Ищу рецепты...")
    recipes, found_ingredients = search_in_database(ingredients)

# сохранение истории поиска рецептов
    history = SearchHistory(update.effective_user.id)
    history.add_search(ingredients, recipes)
# логика ответа при ненайденных рецептах
    if not recipes:
        if found_ingredients:
            similar_recipes = get_similar_recipes(found_ingredients)
            response = f"❌ *Не нашёл рецептов*\n\n✅ *Найдены:* {', '.join(found_ingredients)}\n\n"
            keyboard = []
            if similar_recipes:
                response += f"🍳 *Похожие рецепты:*\n"
                for recipe_id, title in similar_recipes[:3]:
                    response += f"• {title}\n"
                    keyboard.append([InlineKeyboardButton(f"🍽 {title}", callback_data=f"recipe_{recipe_id}")])
                response += "\n📝 *Совет:* добавь другие продукты"
            else:
                response += "😢 *Похожих рецептов тоже нет*\n\n💡 *Попробуй:*\n• Проверь написание\n• Другие продукты\n• Базовые продукты"
        else:
            response = f"❌ *Продукты не найдены в базе!*\n\n📋 *Ты писал:* {', '.join(ingredients)}"
            keyboard = []

        keyboard.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="start_search")])
        keyboard.append([InlineKeyboardButton("📋 Меню", callback_data="new_search")])

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        await update.message.reply_text(
            response,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    # если рецепты найдены 
    keyboard = []
    for recipe_id, title in recipes:
        keyboard.append([InlineKeyboardButton(title, callback_data=f"recipe_{recipe_id}")])
    keyboard.append([InlineKeyboardButton("📋 Меню", callback_data="new_search")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ *Нашёл {len(recipes)} рецептов:*\n\n" +
        "\n".join([f"• {title}" for _, title in recipes]) +
        "\n\n👇 *Выбери рецепт:*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# показ рецепта при нажатии на кнопку 
async def handle_recipe_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    recipe_id = int(query.data.split('_')[1])
    recipe_data = get_recipe_from_db(recipe_id)

    if not recipe_data:
        recipe_text = """
🍴 Макароны с сосисками

Ингредиенты:
• макароны — 200 г
• сосиски — 2–3 шт.
• сыр — по желанию

Время: ~20 минут

Рецепт:
1. Отвари макароны
2. Поджарь сосиски
3. Смешай всё

Приятного аппетита! 😊
"""
    else:
        ingredients_list = "\n".join([f"• {ing}" for ing in recipe_data['ingredients']])
        recipe_text = f"""
🍴 *{recipe_data['title']}*

*Ингредиенты:*
{ingredients_list}

*Время:* {recipe_data['cooking_time']}

*Рецепт:*
{recipe_data['instructions']}

Приятного аппетита! 😊
"""
    await query.edit_message_text(
        recipe_text + "\n\n *Что дальше?*",
        reply_markup=create_recipe_keyboard(recipe_id),
        parse_mode="Markdown"
    )

# показ менюшки с 4 кнопками 
async def show_new_search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📋 *Меню*\n\n"
        "Выбери действие:\n\n"
        "🔍 *Найти рецепт* — поиск по продуктам\n"
        "📋 *История* — твои последние поиски\n"
        "ℹ️ *Помощь* — инструкция\n"
        "🏠 *Главное меню* — назад\n\n"
        "Или просто напиши продукты!",
        reply_markup=create_new_search_keyboard(),
        parse_mode="Markdown"
    )

#кнопка новый поиск
async def start_new_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🔍 *Новый поиск*\n\n"
        "Напиши продукты (каждый с новой строки):\n\n"
        "*Пример:*\n"
        "макароны\n"
        "сыр\n"
        "картошка\n\n"
        "Я найду рецепты! 🍳",
        parse_mode="Markdown"
    )

# кнопка помощи 
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🔍 Начать поиск", callback_data="start_search")],
        [InlineKeyboardButton("📋 Меню", callback_data="new_search")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "ℹ️ *Помощь*\n\n"
        "📝 *Как использовать:*\n"
        "1. Напиши продукты (каждый с новой строки)\n"
        "2. Я найду рецепты\n"
        "3. Выбери рецепт\n"
        "4. Получи инструкцию\n\n"
        "🍳 *Пример:*\n"
        "макароны\nсыр\nкартошка\n\n"
        "👇 *Нажми кнопку чтобы начать:*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# вкладка истории рецептов 
async def show_search_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    history = SearchHistory(user_id)
    search_history = history.get_history()

    if not search_history:
        response = "📋 *История поиска пуста*\n\nНачни поиск рецептов!"
    else:
        response = "📋 *Твои поиски:*\n\n"
        for i, search in enumerate(search_history, 1):
            date = search['timestamp']
            ingredients = ", ".join(search['ingredients'][:3])
            if len(search['ingredients']) > 3:
                ingredients += f" и ещё {len(search['ingredients']) - 3}"
            recipes_count = search['recipes_count']
            response += f"*{i}. {date}*\n   🛒 Продукты: {ingredients}\n   🍳 Найдено: {recipes_count}\n\n"

    keyboard = [
        [InlineKeyboardButton("🔍 Новый поиск", callback_data="start_search")],
        [InlineKeyboardButton("📋 Меню", callback_data="new_search")],
        [InlineKeyboardButton("🗑️ Очистить историю", callback_data="clear_history")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        response,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    if str(user_id) in data:
        del data[str(user_id)]
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        message = "✅ *История очищена!*"
    else:
        message = "ℹ️ *История уже пуста*"

    keyboard = [
        [InlineKeyboardButton("🔍 Новый поиск", callback_data="start_search")],
        [InlineKeyboardButton("📋 Меню", callback_data="new_search")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        message + "\n\n👇 *Выбери действие:*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🏠 *Главное меню*\n\n"
        "Напиши продукты или нажми кнопку\n"
        "чтобы начать поиск рецептов!\n\n"
        "👇 *Выбери действие:*",
        reply_markup=create_main_menu_keyboard(),
        parse_mode="Markdown"
    )


# запуск бота
def main():
    if not TOKEN:
        print("токен не найден")
        return
# проверка подключения к базе данных
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM recipes")
        recipes_count = cursor.fetchone()[0]
        conn.close()
        print(f" база данных: {DB_FILE}")
        print(f" рецепты: {recipes_count}")
    except Exception as e:
        print(f" ошибка в базе: {e}")


    app = Application.builder().token(TOKEN).build()

    # обработка команд 
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_menu))
    app.add_handler(CommandHandler("menu", show_new_search_menu))
    app.add_handler(CommandHandler("history", show_search_history))

    # обработчики сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ingredients))

    # обработчики кнопок
    app.add_handler(CallbackQueryHandler(handle_recipe_button, pattern="^recipe_"))
    app.add_handler(CallbackQueryHandler(start_new_search, pattern="^start_search$"))
    app.add_handler(CallbackQueryHandler(show_new_search_menu, pattern="^new_search$"))
    app.add_handler(CallbackQueryHandler(help_menu, pattern="^help_menu$"))
    app.add_handler(CallbackQueryHandler(show_search_history, pattern="^show_history$"))
    app.add_handler(CallbackQueryHandler(clear_history, pattern="^clear_history$"))
    app.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    print("все работает")

    app.run_polling()

if __name__ == "__main__":

    main()

