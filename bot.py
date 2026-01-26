import os
import re
import asyncio
from dotenv import load_dotenv
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from db import POSTGRES
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

load_dotenv()


class BOT:
    __token: str | None = None
    __app: Application | None = None
    __db_connect = POSTGRES().get_connection()
    __db = POSTGRES()
    __shedulder: AsyncIOScheduler | None = None

    def __init__(self):
        self.__token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.__app = Application.builder().token(self.__token).build()
        self.__shedulder = AsyncIOScheduler()

    async def command_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat

        if context.args:
            param = context.args
            await update.message.reply_text(
                "🤖 Это бот магазина «Мебель Модно Стильно» \n\n"
                "🛍️ У нас вы найдете мебель, которая создает настроение и делает дом идеальным\n"
                "❔ Готовы открыть для себя коллекцию диванов, кресел, столов и шкафов?\n\n"
                "👇 Чтобы увидеть весь ассортимент, нажмите на синюю кнопку «Открыть» ниже.\n",
            )
        else:
            if chat.type == "supergroup" or chat.type == "group":
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "✅ Посмотреть",
                            url=f"https://t.me/{os.getenv("USERNAME_BOT")}?start=from_group_{chat.title}",
                        ),
                    ],
                ]

                await update.message.reply_text(
                    "👋 Вас приветствует бот магазина Мебель Модно Стильно \n\n"
                    "🛋️ Превращаем пространство в уютное место для жизни. Диваны, кресла, столы, шкафы и т.д — всё для вашего интерьера.\n\n"
                    "🛍️ Могу показать ассортимент и данные магазина\n"
                    "👇 Нажмите кнопку «Посмотреть» внизу",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            if chat.type == "private":
                await update.message.reply_text(
                    "👋 Вас приветствует бот магазина Мебель Модно Стильно \n\n"
                    "🛋️ Превращаем пространство в уютное место для жизни. Диваны, кресла, столы, шкафы и т.д — всё для вашего интерьера.\n\n"
                    "🛍️ Я могу показать ассортимент магазина\n"
                    "👇 Нажмите синюю кнопку «Открыть» внизу",
                )

    async def callback_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        query = update.callback_query
        await query.answer()

        print("command bot")

    async def new_chat_members(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """
        Обработчик новых участников чата (когда бота добавляют в группу)
        """
        try:
            # ✅ Проверяем, что есть новые участники
            if not update.message or not update.message.new_chat_members:
                return

            chat = update.effective_chat

            # ✅ Проверяем тип чата
            if chat.type not in ["group", "supergroup"]:
                print(f"❌ Чат не является группой/супергруппой. Тип: {chat.type}")
                return

            # ✅ Проверяем, что среди новых участников есть наш бот
            bot_was_added = False
            for member in update.message.new_chat_members:
                if member.id == context.bot.id:
                    bot_was_added = True
                    table_exists = self.__db.table_exists("telegram_groups")

                    if table_exists == True:
                        cursor = self.__db_connect.cursor()
                        data = (chat.id, chat.title)
                        cursor.execute(
                            f"INSERT INTO telegram_groups (chat_id, title) VALUES (%s, %s)",
                            data,
                        )
                        self.__db_connect.commit()

                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "✅ Открыть бота",
                                url=f"https://t.me/{os.getenv("USERNAME_BOT")}?start=from_group_{chat.title}",
                            ),
                            InlineKeyboardButton("🔗 Сайт", url=os.getenv("URL_WEB")),
                        ],
                    ]
                    welcome_text = (
                        "🤖 В группу добавлен бот магазина «Мебель Модно Стильно»! \n"
                        "😊 Создан, чтобы сделать магазин удобным и быстрым.\n\n"
                        "📌 Что он умеет:\n\n"
                        "📢 Делиться анонсами новых поступлений\n"
                        "🧹 Удаляет рекламные ссылки сохраняя чат чистым.\n\n"
                        "👉 Используйте команду /start, чтобы взаимодействовать с ботом."
                    )
                    await context.bot.send_message(
                        chat_id=chat.id,
                        text=welcome_text,
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )
                    break

            if not bot_was_added:
                return

            print(f"🤖 Бот добавлен в группу: {chat.title} (ID: {chat.id})")

        except Exception as e:
            self.__db_connect.rollback()
            print(f"❌ Ошибка в обработчике новых участников: {e}")

    def contains_links(self, text: Optional[str]) -> bool:
        """
        Проверяет наличие ссылок в тексте.
        Определяет все виды ссылок: с протоколом, без протокола, Telegram-ссылки,
        IP-адреса, Markdown и HTML ссылки.
        """
        # Проверка на None или пустую строку
        if not text or not isinstance(text, str):
            return False

        # Очистка текста от разметки
        # Удаление Markdown ссылок [текст](URL)
        clean_text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        # Удаление HTML ссылок <a href="URL">текст</a>
        clean_text = re.sub(
            r'<a\s+[^>]*href="[^"]*"[^>]*>([^<]+)</a>',
            r"\1",
            clean_text,
            flags=re.IGNORECASE,
        )
        # Удаление остальных HTML тегов
        clean_text = re.sub(r"<[^>]+>", "", clean_text)

        # Комбинированный паттерн для всех типов ссылок
        link_patterns = [
            # 1. URL с протоколом (http, https, ftp, ftps)
            r'(?:https?|ftp|ftps)://[^\s<>"\'\[\]{}|\\^`]+',
            # 2. www.домены (начинающиеся с www.)
            r'\bwww\.[^\s<>"\'\[\]{}|\\^`]+',
            # 3. Домены без протокола (с популярными TLD)
            r"\b(?!@)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
            r"(?:com|org|net|edu|gov|mil|int|info|biz|ru|рф|ua|by|kz|"
            r"uk|de|fr|es|it|pl|cz|sk|hu|ro|bg|gr|tr|ir|il|sa|ae|"
            r"in|cn|jp|kr|vn|th|id|my|ph|sg|au|nz|ca|mx|br|ar|cl|co|"
            r"[a-z]{2,})"
            r"(?::\d{2,5})?"
            r"(?:/[\w\-\.~!$&\'()*+,;=:@%]*)?"
            r'(?:\?[^\s<>"\']*)?'
            r'(?:#[^\s<>"\']*)?',
            # 4. Telegram-специфичные ссылки
            r"\b(?:t\.me/|telegram\.me/|tg://|@)[a-zA-Z0-9_][a-zA-Z0-9_\-/]*",
            # 5. IP-адреса с портами/путями
            r"\b(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\."
            r"(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\."
            r"(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\."
            r"(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])"
            r"(?::\d{2,5})?"
            r"(?:/[\w\-\.~!$&\'()*+,;=:@%]*)?",
        ]

        # Объединяем все паттерны в один
        combined_pattern = re.compile(
            "|".join(f"({pattern})" for pattern in link_patterns), re.IGNORECASE
        )

        # Ищем совпадения
        matches = combined_pattern.finditer(clean_text)

        # Список исключений (ложные срабатывания)
        exceptions = {
            "example.com",
            "example.org",
            "example.net",
            "example.edu",
            "test.com",
            "test.org",
            "demo.com",
            "sample.com",
            "localhost",
            "localdomain",
            "127.0.0.1",
            "0.0.0.0",
            "api",
            "www",
            "http",
            "https",
            "ftp",
        }

        # Проверяем каждое найденное совпадение
        for match in matches:
            for group_num in range(1, len(match.groups()) + 1):
                match_text = match.group(group_num)
                if match_text:
                    # Приводим к нижнему регистру для проверки
                    match_lower = match_text.lower().strip()

                    # Проверяем исключения
                    is_exception = False
                    for exc in exceptions:
                        # Проверяем, содержит ли исключение как подстроку
                        if exc in match_lower:
                            # Если это полное совпадение или часть домена
                            if (
                                exc == match_lower
                                or match_lower.endswith("." + exc)
                                or f".{exc}." in match_lower
                                or match_lower.startswith(exc + ".")
                            ):
                                is_exception = True
                                break

                    if not is_exception:
                        # Дополнительные проверки для уменьшения ложных срабатываний

                        # Проверка на email (исключаем)
                        if re.match(
                            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                            match_text,
                        ):
                            continue

                        # Проверка на слишком короткие "ссылки"
                        if len(match_text) < 5:
                            continue

                        # Проверка на случайные слова с точками
                        if "." in match_text and not any(
                            c in match_text for c in ["/", ":", "@"]
                        ):
                            parts = match_text.split(".")
                            # Если это просто слово.точка.слово без других признаков ссылки
                            if (
                                len(parts) == 2
                                and len(parts[0]) < 4
                                and len(parts[1]) < 4
                            ):
                                continue

                        # Если дошли сюда, значит это похоже на настоящую ссылку
                        return True

        # Дополнительная проверка: ищем URL в Markdown и HTML, которые могли быть пропущены
        # Проверяем оригинальный текст на наличие паттернов ссылок
        if re.search(r"\[[^\]]+\]\([^)]+\)", text):  # Markdown ссылки
            return True
        if re.search(
            r'<a\s+[^>]*href="[^"]*"[^>]*>', text, re.IGNORECASE
        ):  # HTML ссылки
            return True

        # Проверка на скрытые ссылки с использованием Unicode или обфускации
        # (например, использование похожих символов)
        suspicious_patterns = [
            r"[а-яА-ЯёЁ]*\.(?:рф|com|org|net)[а-яА-ЯёЁ]*",  # Кириллические домены
            r"\b[\w\-]+\.[\w\-]+\.[\w\-]+\b",  # Многоточечные структуры
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, clean_text, re.IGNORECASE):
                # Проверяем, не является ли это обычным текстом
                suspicious_match = re.search(pattern, clean_text, re.IGNORECASE)
                if suspicious_match:
                    match_text = suspicious_match.group()
                    # Исключаем очевидные не-ссылки
                    if not any(
                        exc in match_text.lower()
                        for exc in ["example", "test", "localhost"]
                    ):
                        # Проверяем, похоже ли это на домен
                        if re.search(r"\.[a-z]{2,}$", match_text, re.IGNORECASE):
                            return True

        return False

    async def check_user_admin(self, chat_id: int, user_id: int, bot) -> bool:
        try:
            chat_member = await bot.get_chat_member(chat_id, user_id)
            return chat_member.status in ["administrator", "creator"]
        except Exception as e:
            return False

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message

        if not message.text and not message.caption:
            return

        chat_id = message.chat_id
        user_id = message.from_user.id
        text = message.text or message.caption

        if self.contains_links(text):
            is_admin = await self.check_user_admin(chat_id, user_id, context.bot)
            if is_admin == False:
                await message.delete()
                notice = await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ {message.from_user.mention_html()} ваше сообщение в группе было удалено, "
                    f"так как содержит ссылку.\n\n"
                    f"Ссылки могут отправлять только администратор группы",
                    parse_mode="HTML",
                )

                await asyncio.sleep(10)
                await notice.delete()

    async def test(self) -> None:
        print("11")

    def setup_scheduler(self):
        try:
            self.__shedulder.add_job(self.test, "interval", seconds=3, id="test_job")
            self.__shedulder.start()
            print("Планировщик запущен")
        except Exception as err:
            print(f"Ошибка настройки планировщика: {err}")

    def start(self):
        try:
            print("БОТ ЗАПУЩЕН")
            self.__app.add_handler(CommandHandler("start", self.command_start))
            self.__app.add_handler(CallbackQueryHandler(self.callback_handler))
            self.__app.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
            )
            self.__app.add_handler(
                MessageHandler(
                    filters.StatusUpdate.NEW_CHAT_MEMBERS, self.new_chat_members
                )
            )
            self.__app.run_polling()
        except BaseException as err:
            print(f"При запуске бота произошла ошибка: {err}")
