import sqlite3
import logging
import difflib

quotes_filename = "quotes.txt"
db_name = "bot_database.db"


def are_similar(str1, str2, threshold=0.9):
    similarity = difflib.SequenceMatcher(None, str1, str2).ratio()
    return similarity >= threshold


def remove_similar_phrases(input_file, output_file, threshold=0.9):
    with open(input_file, "r", encoding="utf-8") as file:
        lines = file.readlines()

    unique_lines = []

    for line in lines:
        line = line.strip()
        if not any(
            are_similar(line, unique_line, threshold) for unique_line in unique_lines
        ):
            unique_lines.append(line)

    with open(output_file, "w", encoding="utf-8") as file:
        for line in unique_lines:
            file.write(line + "\n")


def escape_markdown(data):
    special_characters = r"_*[]()~`>#!+-.|{}"
    quote, author = data
    for char in special_characters:
        quote = quote.replace(char, f"\\{char}")
        author = author.replace(char, f"\\{char}")
    return quote, author


class Database:
    _instance = None

    def __new__(cls, db_name=db_name):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.conn = sqlite3.connect(db_name)
            cls._instance.cursor = cls._instance.conn.cursor()
            cls._instance.create_tables()
            logging.info("Загружаю цитаты...")
            cls._instance.load_initial_quotes()
        return cls._instance

    def create_tables(self):
        logging.info("Проверяю есть ли таблицы...")
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            time TEXT,
            active INTEGER DEFAULT 1
        )"""
        )

        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY,
            quote TEXT,
            author TEXT
        )"""
        )

        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS pending_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            quote TEXT NOT NULL,
            author TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )"""
        )

        self.conn.commit()
        logging.info("Таблицы есть.")

    def is_quotes_empty(self):
        self.cursor.execute("SELECT COUNT(*) FROM quotes")
        count = self.cursor.fetchone()[0]
        return count == 0

    def load_initial_quotes(self):
        if not self.is_quotes_empty():
            logging.info("База данных уже содержит цитаты. Пропускаю загрузку.")
            return
        logging.info("Пытаюсь убрать повторяющиеся цитаты...")
        remove_similar_phrases(quotes_filename, quotes_filename, threshold=0.85)
        logging.info("Убрал повторяющиеся цитаты")
        logging.info("Добавляю цитаты...")
        try:
            with open(quotes_filename, "r", encoding="utf-8") as file:
                for line in file:
                    if " - " in line:
                        quote, author = line.rsplit(" - ", 1)
                        quote = quote.strip().strip('"')
                        author = author.strip()
                        self.add_quote(quote, author)
            logging.info("Цитаты добавлены.")
        except FileNotFoundError:
            logging.error(f"Файл {quotes_filename} не найден.")
        except Exception as e:
            logging.error(f"Ошибка при загрузке цитат: {e}")

    def add_user(self, user_id, username, time):
        try:
            self.cursor.execute(
                "INSERT INTO users (id, username, time) VALUES (?, ?, ?)",
                (user_id, username, time),
            )
            self.conn.commit()
            logging.info(f"Добавил пользователя @{username}({user_id}).")
        except sqlite3.IntegrityError:
            logging.error(f"Пользователь @{username}({user_id}) уже существует.")

    def add_quote(self, quote, author):
        try:
            self.cursor.execute(
                "INSERT INTO quotes (quote, author) VALUES (?, ?)", (quote, author)
            )
            self.conn.commit()
            logging.info(f'Добавил цитату "{quote}" - {author}')
            return self.cursor.execute(
                "SELECT id FROM quotes WHERE quote = ?", (quote,)
            ).fetchone()
        except Exception as e:
            logging.error(f"Ошибка при добавлении цитаты: {e}")

    def add_pending_quote(self, user_id, quote, author):
        try:
            username = self.get_user(user_id)[1]
            self.cursor.execute(
                "INSERT INTO pending_quotes (user_id, quote, author) VALUES (?, ?, ?)",
                (user_id, quote, author),
            )
            self.conn.commit()
            logging.info(
                f'Пользователь @{username}({user_id}) предложил цитату "{quote}" - {author}'
            )
            return self.cursor.execute(
                "SELECT id FROM pending_quotes WHERE quote = ?", (quote,)
            ).fetchone()[0]
        except Exception as e:
            logging.error(f"Ошибка при предложении цитаты: {e}")

    def delete_quote(self, quote_id):
        try:
            quote, author = self.cursor.execute(
                "SELECT quote, author FROM quotes WHERE id = ?", (quote_id,)
            ).fetchone()
            self.cursor.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
            self.conn.commit()
            logging.info(f'Удалил цитату "{quote}" - {author}')
        except Exception as e:
            logging.error(f"Ошибка при удалении цитаты: {e}")

    def delete_pending_quote(self, quote):
        try:
            quote, author = self.cursor.execute(
                "SELECT quote, author FROM pending_quotes WHERE quote = ?", (quote,)
            ).fetchone()
            self.cursor.execute("DELETE FROM pending_quotes WHERE id = ?", (quote,))
            self.conn.commit()
            logging.info(f'Удалил цитату "{quote}" - {author}')
        except Exception as e:
            logging.error(f"Ошибка при удалении цитаты: {e}")

    def update_user_time(self, user_id, time):
        username = self.get_user(user_id)[1]
        self.cursor.execute("UPDATE users SET time = ? WHERE id = ?", (time, user_id))
        self.conn.commit()
        logging.info(f"Пользователь @{username}({user_id}) установил время {time}")

    def get_user(self, user_id):
        return self.cursor.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()

    def delete_user(self, user_id):
        try:
            username = self.get_user(user_id)[1]
            self.cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            logging.info(f"Удалил пользователя @{username}({user_id})")
        except Exception as e:
            logging.error(f"Ошибка при удалении пользователя: {e}")

    def get_all_users(self):
        return self.cursor.execute(
            "SELECT id, username, time FROM users WHERE active = 1"
        ).fetchall()

    def get_quote(self, quote_id):
        quote, author = self.cursor.execute(
            "SELECT quote, author FROM quotes WHERE id = ?", (quote_id,)
        ).fetchone()
        escaped_quote, escaped_author = escape_markdown((quote, author))
        return escaped_quote, escaped_author

    def get_pending_quote(self, quote_id):
        quote, author = self.cursor.execute(
            "SELECT quote, author FROM pending_quotes WHERE id = ?", (quote_id,)
        ).fetchone()
        escaped_quote, escaped_author = escape_markdown((quote, author))
        return escaped_quote, escaped_author

    def get_random_quote(self, user_id):
        username = self.get_user(user_id)[1]
        quote, author = self.cursor.execute(
            "SELECT quote, author FROM quotes ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
        logging.info(
            f'Отправил цитату "{quote}" - {author} пользователю @{username}({user_id})'
        )
        escaped_quote, escaped_author = escape_markdown((quote, author))
        return escaped_quote, escaped_author

    def get_all_quotes(self):
        return self.cursor.execute("SELECT id, quote, author FROM quotes").fetchall()

    def close(self):
        self.conn.close()
