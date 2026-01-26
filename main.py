# main.py
from bot import BOT
from db import POSTGRES
import asyncio


def main() -> None:
    postgres = POSTGRES()
    if postgres.connect() != None:
        # Создание таблицы для групп, если она не существует
        cursor = postgres.get_connection().cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_groups (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT UNIQUE NOT NULL,
                title VARCHAR(255),
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_reminder_date TIMESTAMP
            )
        """
        )
        postgres.get_connection().commit()
        cursor.close()

        # Запуск бота
        BOT().start()


if __name__ == "__main__":
    main()
