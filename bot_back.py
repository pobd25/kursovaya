# импорт библиотек
import sqlite3
import logging
import json
from datetime import datetime

# настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# настройки
DB_FILE = "chefbot.db"
HISTORY_FILE = "search_history.json"


# настройки истории поиска
class SearchHistory:
    def __init__(self, user_id):
        self.user_id = user_id
        self.history = self._load_history()

    def _load_history(self):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get(str(self.user_id), [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_history(self):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        data[str(self.user_id)] = self.history[-10:]
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_search(self, ingredients, recipes_found):
        search_entry = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'ingredients': ingredients,
            'recipes_count': len(recipes_found),
            'recipes': recipes_found[:3]
        }
        self.history.append(search_entry)
        if len(self.history) > 10:
            self.history = self.history[-10:]
        self._save_history()

    def get_history(self):
        return self.history[::-1]


# поиск в базе данных, подключение бд к боту
def search_in_database(ingredients):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        placeholders = ','.join('?' for _ in ingredients)
        cursor.execute(f"""
            SELECT id FROM ingredients 
            WHERE LOWER(name) IN ({placeholders})
        """, [ing.lower() for ing in ingredients])

        ingredient_ids = [row[0] for row in cursor.fetchall()]

        if not ingredient_ids:
            conn.close()
            return [], []

        cursor.execute(f"""
            SELECT name FROM ingredients 
            WHERE id IN ({','.join('?' for _ in ingredient_ids)})
        """, ingredient_ids)
        found_ingredients = [row[0] for row in cursor.fetchall()]

        query = f"""
        SELECT r.id, r.title 
        FROM recipes r
        WHERE r.id IN (
            SELECT ri.recipe_id 
            FROM recipe_ingredients ri 
            WHERE ri.ingredient_id IN ({','.join('?' for _ in ingredient_ids)})
            GROUP BY ri.recipe_id 
            HAVING COUNT(DISTINCT ri.ingredient_id) = ?
        )
        ORDER BY r.title
        """

        cursor.execute(query, ingredient_ids + [len(ingredient_ids)])
        recipes = cursor.fetchall()
        conn.close()

        return recipes, found_ingredients

    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        return [], []

# функция получения рецепта
def get_recipe_from_db(recipe_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT title, instructions, cooking_time 
            FROM recipes 
            WHERE id = ?
        """, (recipe_id,))

        recipe = cursor.fetchone()
        if not recipe:
            return None

        title, instructions, cooking_time = recipe

        cursor.execute("""
            SELECT i.name, ri.quantity
            FROM ingredients i
            JOIN recipe_ingredients ri ON i.id = ri.ingredient_id
            WHERE ri.recipe_id = ?
            ORDER BY i.name
        """, (recipe_id,))

        ingredients = cursor.fetchall()
        conn.close()

        # форматируем ингредиенты с количеством
        formatted_ingredients = []
        for name, quantity in ingredients:
            if quantity and quantity.strip():
                formatted_ingredients.append(f"{name} — {quantity}")
            else:
                formatted_ingredients.append(name)

        return {
            'title': title,
            'instructions': instructions,
            'cooking_time': cooking_time,
            'ingredients': formatted_ingredients
        }

    except Exception as e:
        logger.error(f"Ошибка получения рецепта: {e}")
        return None

# поиск похожих рецептов (где есть хотя бы один ингредиент)
def get_similar_recipes(found_ingredients):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        placeholders = ','.join('?' for _ in found_ingredients)
        cursor.execute(f"""
            SELECT id FROM ingredients 
            WHERE LOWER(name) IN ({placeholders})
        """, [ing.lower() for ing in found_ingredients])

        ingredient_ids = [row[0] for row in cursor.fetchall()]

        if not ingredient_ids:
            return []

        query = f"""
        SELECT r.id, r.title, COUNT(ri.ingredient_id) as match_count
        FROM recipes r
        JOIN recipe_ingredients ri ON r.id = ri.recipe_id
        WHERE ri.ingredient_id IN ({','.join('?' for _ in ingredient_ids)})
        GROUP BY r.id, r.title
        HAVING match_count >= 1
        ORDER BY match_count DESC, r.title
        LIMIT 5
        """

        cursor.execute(query, ingredient_ids)
        recipes = [(row[0], row[1]) for row in cursor.fetchall()]
        conn.close()

        return recipes

    except Exception as e:
        logger.error(f"Ошибка поиска похожих: {e}")
        return []