import os
import re
import asyncio
import threading
from datetime import datetime
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
    __db_connect = None
    __db = None
    __scheduler: AsyncIOScheduler | None = None

    def __init__(self):
        self.__token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.__app = Application.builder().token(self.__token).build()
        self.__db = POSTGRES()
        self.__db_connect = self.__db.get_connection()

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
                            url=f"https://t.me/{os.getenv('USERNAME_BOT')}?start=from_group_{chat.title}",
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
                            "INSERT INTO telegram_groups (chat_id, title) VALUES (%s, %s)",
                            data,
                        )
                        self.__db_connect.commit()

                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "✅ Открыть бота",
                                url=f"https://t.me/{os.getenv('USERNAME_BOT')}?start=from_group_{chat.title}",
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

    async def send_morning_reminder(self):
        """
        Отправка утреннего напоминания во все группы
        """
        try:
            cursor = self.__db_connect.cursor()
            cursor.execute("SELECT chat_id, title FROM telegram_groups")
            groups = cursor.fetchall()

            morning_messages = [
                "🌅 Доброе утро, друзья! Напоминаем, что наш бот всегда готов помочь вам с выбором мебели.\n\n"
                # "🛋️ Уже определились с выбором дивана или шкафа?",
                "☀️ Добрый день начинается с хорошего настроения и удобной мебели!\n\n"
                "🛍️ Не забывайте, что наш бот может показать весь ассортимент магазина.",
                # "🌇 С добрым утром! Ваш дом может стать еще уютнее с правильной мебелью.\n\n"
                # "❓ Есть вопросы по выбору? Наш бот всегда на связи!",
            ]

            import random

            message = random.choice(morning_messages)
            chat_id = groups[0][0]
            title = groups[0][1]
            try:
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "✅ Открыть",
                            url=f"https://t.me/{os.getenv('USERNAME_BOT')}?start=reminder_morning",
                        ),
                        # InlineKeyboardButton(
                        #     "📞 Связаться", url="https://t.me/manager_username"
                        # ),
                    ],
                ]

                await self.__app.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                print(f"✅ Утреннее напоминание отправлено в группу: {title}")
            except Exception as e:
                print(f"❌ Ошибка при отправке в группу {title}: {e}")
                # Если бот удален из группы, удаляем запись из БД
                if "Chat not found" in str(e) or "bot was kicked" in str(e):
                    cursor.execute(
                        "DELETE FROM telegram_groups WHERE chat_id = %s", (chat_id,)
                    )
                    self.__db_connect.commit()
            # for chat_id, title in groups:
            #     try:
            #         keyboard = [
            #             [
            #                 InlineKeyboardButton(
            #                     "✅ Открыть",
            #                     url=f"https://t.me/{os.getenv('USERNAME_BOT')}?start=reminder_morning",
            #                 ),
            #                 # InlineKeyboardButton(
            #                 #     "📞 Связаться", url="https://t.me/manager_username"
            #                 # ),
            #             ],
            #         ]

            #         await self.__app.bot.send_message(
            #             chat_id=chat_id,
            #             text=message,
            #             parse_mode="HTML",
            #             reply_markup=InlineKeyboardMarkup(keyboard),
            #         )
            #         print(f"✅ Утреннее напоминание отправлено в группу: {title}")
            #     except Exception as e:
            #         print(f"❌ Ошибка при отправке в группу {title}: {e}")
            #         # Если бот удален из группы, удаляем запись из БД
            #         if "Chat not found" in str(e) or "bot was kicked" in str(e):
            #             cursor.execute(
            #                 "DELETE FROM telegram_groups WHERE chat_id = %s", (chat_id,)
            #             )
            #             self.__db_connect.commit()

            cursor.close()

        except Exception as e:
            print(f"❌ Ошибка в утреннем напоминании: {e}")

    async def send_evening_reminder(self):
        """
        Отправка вечернего напоминания во все группы
        """
        try:
            cursor = self.__db_connect.cursor()
            cursor.execute("SELECT chat_id, title FROM telegram_groups")
            groups = cursor.fetchall()

            evening_messages = [
                "🌙 Добрый вечер! Время подумать об уюте в вашем доме.\n\n"
                "🛋️ Наш магазин предлагает мебель для создания комфортной атмосферы.",
                "✨ Вечер - отличное время для планирования обновления интерьера!\n\n"
                "🌟 Добрый вечер! Не забывайте, что удобная мебель - залог хорошего отдыха.\n\n",
            ]

            import random

            message = random.choice(evening_messages)
            chat_id = groups[0][0]
            title = groups[0][1]
            try:
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "🌃 Открыть бот",
                            url=f"https://t.me/{os.getenv('USERNAME_BOT')}?start=reminder_evening",
                        ),
                        InlineKeyboardButton("🏪 Сайт", url=os.getenv("URL_WEB")),
                    ],
                ]

                await self.__app.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                print(f"✅ Вечернее напоминание отправлено в группу: {title}")
            except Exception as e:
                print(f"❌ Ошибка при отправке в группу {title}: {e}")
                # Если бот удален из группы, удаляем запись из БД
                if "Chat not found" in str(e) or "bot was kicked" in str(e):
                    cursor.execute(
                        "DELETE FROM telegram_groups WHERE chat_id = %s", (chat_id,)
                    )
                    self.__db_connect.commit()
            # for chat_id, title in groups:
            #     try:
            #         keyboard = [
            #             [
            #                 InlineKeyboardButton(
            #                     "🌃 Открыть бот",
            #                     url=f"https://t.me/{os.getenv('USERNAME_BOT')}?start=reminder_evening",
            #                 ),
            #                 InlineKeyboardButton("🏪 Сайт", url=os.getenv("URL_WEB")),
            #             ],
            #         ]

            #         await self.__app.bot.send_message(
            #             chat_id=chat_id,
            #             text=message,
            #             parse_mode="HTML",
            #             reply_markup=InlineKeyboardMarkup(keyboard),
            #         )
            #         print(f"✅ Вечернее напоминание отправлено в группу: {title}")
            #     except Exception as e:
            #         print(f"❌ Ошибка при отправке в группу {title}: {e}")
            #         # Если бот удален из группы, удаляем запись из БД
            #         if "Chat not found" in str(e) or "bot was kicked" in str(e):
            #             cursor.execute(
            #                 "DELETE FROM telegram_groups WHERE chat_id = %s", (chat_id,)
            #             )
            #             self.__db_connect.commit()

            cursor.close()

        except Exception as e:
            print(f"❌ Ошибка в вечернем напоминании: {e}")

    async def send_weekly_update(self):
        """
        Еженедельное обновление о новинках и акциях
        """
        try:
            cursor = self.__db_connect.cursor()
            cursor.execute("SELECT chat_id, title FROM telegram_groups")
            groups = cursor.fetchall()

            weekly_messages = [
                "📢 Новая неделя - новые возможности обновить интерьер!\n\n"
                # "🔥 Специально для вас на этой неделе:\n"
                # "• Новые модели диванов\n"
                # "• Скидки на офисную мебель\n"
                # "• Бесплатная доставка при заказе от 30 000₽\n\n"
                "✨ Не упустите шанс сделать свой дом лучше!",
                # "🌟 Неделя начинается с отличных новостей!\n\n"
                # "🎁 В нашем магазине появились:\n"
                # "• Стильные кресла для гостиной\n"
                # "• Практичные столы для кухни\n"
                # "• Современные шкафы-купе\n\n"
                # "🏃‍♂️ Успейте первыми оценить новинки!",
                # "📈 Первый день недели - время для новых идей!\n\n"
                # "💡 На этой неделе у нас:\n"
                # "• Обновление коллекции спальных гарнитуров\n"
                # "• Специальные условия для постоянных клиентов\n"
                # "• Акция «Приведи друга»\n\n"
                "🎯 Сделайте ваш дом уютнее уже сегодня!",
            ]

            import random

            message = random.choice(weekly_messages)

            for chat_id, title in groups:
                try:
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "🆕 Смотреть новинки",
                                url=f"https://t.me/{os.getenv('USERNAME_BOT')}?start=weekly_new",
                            ),
                            InlineKeyboardButton(
                                "🏷️ Акции",
                                url=f"https://t.me/{os.getenv('USERNAME_BOT')}?start=sales",
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                "📞 Заказать звонок", callback_data="request_call"
                            ),
                            InlineKeyboardButton(
                                "🗺️ Как добраться",
                                url=os.getenv("URL_WEB") + "/contacts",
                            ),
                        ],
                    ]

                    await self.__app.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )
                    print(f"✅ Еженедельное обновление отправлено в группу: {title}")
                except Exception as e:
                    print(f"❌ Ошибка при отправке в группу {title}: {e}")
                    # Если бот удален из группы, удаляем запись из БД
                    if "Chat not found" in str(e) or "bot was kicked" in str(e):
                        cursor.execute(
                            "DELETE FROM telegram_groups WHERE chat_id = %s", (chat_id,)
                        )
                        self.__db_connect.commit()

            cursor.close()

        except Exception as e:
            print(f"❌ Ошибка в еженедельном обновлении: {e}")

    def setup_scheduler(self):
        """
        Настройка планировщика для отправки напоминаний
        """
        try:
            # Создаем планировщик с собственным event loop
            self.__scheduler = AsyncIOScheduler(timezone="Asia/Krasnoyarsk")

            # Утреннее напоминание в 9:00 каждый день
            self.__scheduler.add_job(
                self.send_morning_reminder,
                CronTrigger(hour=9, minute=0, timezone="Asia/Krasnoyarsk"),
                id="morning_reminder",
                replace_existing=True,
            )

            # Вечернее напоминание в 20:00 каждый день
            self.__scheduler.add_job(
                self.send_evening_reminder,
                CronTrigger(hour=20, minute=0, timezone="Asia/Krasnoyarsk"),
                id="evening_reminder",
                replace_existing=True,
            )

            # Еженедельное напоминание о новинках (понедельник, 11:00)
            # self.__scheduler.add_job(
            #     self.send_weekly_update,
            #     CronTrigger(
            #         day_of_week="mon", hour=11, minute=0, timezone="Asia/Krasnoyarsk"
            #     ),
            #     id="weekly_update",
            #     replace_existing=True,
            # )

            print("✅ Планировщик настроен")
            print("📅 Расписание:")
            print("   - Утреннее напоминание: 09:00 каждый день")
            print("   - Вечернее напоминание: 20:00 каждый день")

        except Exception as err:
            print(f"❌ Ошибка настройки планировщика: {err}")

    async def start_scheduler(self):
        """
        Запуск планировщика после запуска бота
        """
        try:
            if self.__scheduler and not self.__scheduler.running:
                self.__scheduler.start()
                print("✅ Планировщик запущен")

                # Проверка запланированных задач
                jobs = self.__scheduler.get_jobs()
                print(f"📋 Запланировано задач: {len(jobs)}")
                for job in jobs:
                    print(f"   - {job.id}: следующее выполнение в {job.next_run_time}")

        except Exception as e:
            print(f"❌ Ошибка при запуске планировщика: {e}")

    async def stop_scheduler(self):
        """
        Остановка планировщика при остановке бота
        """
        try:
            if self.__scheduler and self.__scheduler.running:
                self.__scheduler.shutdown(wait=False)
                print("⏹️ Планировщик остановлен")
        except Exception as e:
            print(f"❌ Ошибка при остановке планировщика: {e}")

    def start(self):
        try:
            print("🤖 ЗАПУСК БОТА...")

            # Регистрация обработчиков
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

            # Настройка планировщика
            print("⚙️ Настройка планировщика...")
            self.setup_scheduler()

            # Создаем и запускаем event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Запускаем планировщик
                if self.__scheduler and not self.__scheduler.running:
                    loop.run_until_complete(self.start_scheduler())

                print("🚀 Запуск бота...")
                # Запуск бота с нашим event loop
                self.__app.run_polling(
                    allowed_updates=Update.ALL_TYPES,
                    close_loop=False,
                )

            finally:
                # Останавливаем планировщик
                if self.__scheduler and self.__scheduler.running:
                    loop.run_until_complete(self.stop_scheduler())
                loop.close()
                print("👋 Бот завершил работу")

        except KeyboardInterrupt:
            print("\n🛑 Бот остановлен пользователем")
        except BaseException as err:
            print(f"❌ При запуске бота произошла ошибка: {err}")
