# db.py
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


class POSTGRES:
    _instance = None
    _connection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.connect()
        self._initialized = True

    def __del__(self):
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
                    connect_timeout=10,
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=3,
                )
                self._connection.autocommit = False
                print("✅ Подключение к базе данных PostgreSQL успешно")
            return self._connection
        except Exception as err:
            print(f"❌ При подключении к базе данных произошла ошибка: {err}")
            return None

    def get_connection(self):
        """Получение текущего соединения с проверкой"""
        try:
            if self._connection is None or self._connection.closed:
                print("⚠️ Соединение с БД потеряно, переподключаемся...")
                return self.connect()
            return self._connection
        except Exception:
            return self.connect()

    def close(self):
        """Закрытие соединения с базой данных"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            print("🔒 Соединение с базой данных закрыто")

    def table_exists(self, table_name, schema="public"):
        """
        Проверяет существование таблицы в указанной схеме
        """
        connection = self.get_connection()
        if not connection or connection.closed:
            print("❌ Нет соединения с базой данных")
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
            with connection.cursor() as cursor:
                cursor.execute(query, (schema, table_name))
                result = cursor.fetchone()
                return result[0] if result else False
        except psycopg2.Error as err:
            print(f"❌ Ошибка при проверке таблицы: {err}")
            return False
