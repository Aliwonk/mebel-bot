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

load_dotenv()


class BOT:
    __token: str | None = None
    __app: Application | None = None
    __db_connect = POSTGRES().get_connection()
    __db = POSTGRES()

    def __init__(self):
        self.__token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.__app = Application.builder().token(self.__token).build()

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

    def contains_links(self, text: str) -> bool:
        if not text:
            return False

        url_pattern = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|"
            r"(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        )

        # Также ищем ссылки без http (например, example.com)
        domain_pattern = re.compile(
            r"(?:www\.)?[a-zA-Z0-9-]+(\.[a-zA-Z]{2,})+(?:[/?#][^\s]*)?"
        )

        urls = url_pattern.findall(text)

        # Добавляем найденные домены, если они не являются частью URL
        for domain_match in domain_pattern.finditer(text):
            domain = domain_match.group()
            # Проверяем, не является ли это частью уже найденного URL
            if not any(domain in url for url in urls):
                if not domain.startswith(("http://", "https://", "www.")):
                    domain = "http://" + domain
                urls.append(domain)

        return len(urls) > 0

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
