import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


class POSTGRES:
    _instance = None
    _connection = None

    def __new__(cls):
        """Переопределение метода создания экземпляра для реализации Singleton"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Инициализация экземпляра (вызывается только один раз)"""
        if self._initialized:
            return

        # Попытка установить соединение при инициализации
        self.connect()
        self._initialized = True

    def __del__(self):
        """Деструктор для автоматического закрытия соединения"""
        self.close()

    def connect(self):
        """Установка соединения с базой данных"""
        try:
            if self._connection is None or self._connection.closed:
                self._connection = psycopg2.connect(
                    dbname=os.getenv("POSTGRES_DB_NAME"),
                    user=os.getenv("POSTGRES_DB_USER"),
                    password=os.getenv("POSTGRES_DB_PASSWORD"),
                    host=os.getenv("POSTGRES_DB_HOST"),
                    port=os.getenv("POSTGRES_DB_PORT"),
                )
                print("Подключение к базе данных PostgreSQL успешно")
            return self._connection
        except Exception as err:
            print(f"При подключении к базе данных произошла ошибка: {err}")
            return None

    def get_connection(self):
        """Получение текущего соединения"""
        return self._connection

    def close(self):
        """Закрытие соединения с базой данных"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            print("Соединение с базой данных закрыто")

    def table_exists(self, table_name, schema="public"):
        """
        Проверяет существование таблицы в указанной схеме

        Args:
            table_name (str): Имя таблицы
            schema (str): Имя схемы (по умолчанию 'public')

        Returns:
            bool: True если таблица существует, False в противном случае
        """
        if not self._connection or self._connection.closed:
            print("Нет соединения с базой данных")
            return False

        query = """
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name = %s
            );
        """

        try:
            with self._connection.cursor() as cursor:
                cursor.execute(query, (schema, table_name))
                result = cursor.fetchone()
                return result[0] if result else False
        except psycopg2.Error as err:
            print(f"Ошибка при проверке таблицы: {err}")
            return False
