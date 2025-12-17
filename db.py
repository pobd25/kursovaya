import sqlite3

print("Создаю файл базы данных...")
conn = sqlite3.connect('chefbot.db')
cursor = conn.cursor()

print("Создаю таблицу 'recipes'...")
cursor.execute('''
CREATE TABLE recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    instructions TEXT NOT NULL,
    cooking_time TEXT
)
''')

print("Создаю таблицу 'ingredients'...")
cursor.execute('''
CREATE TABLE ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
)
''')

print("Создаю таблицу 'recipe_ingredients'...")
cursor.execute('''
CREATE TABLE recipe_ingredients (
    recipe_id INTEGER,
    ingredient_id INTEGER,
    quantity TEXT,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id),
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id),
    PRIMARY KEY (recipe_id, ingredient_id)
)
''')

conn.commit()
conn.close()

print("\n База данных создана.")
print("Файл: 'chefbot.db'")
