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
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

load_dotenv()


class BOT:
    __token: str | None = None
    __app: Application | None = None

    def __init__(self):
        self.__token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.__app = Application.builder().token(self.__token).build()

    async def command_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "👋 Добро пожаловать в Мебель Модно Стильно \n\n"
            "🛋️ Превращаем пространство в уютное место для жизни. Диваны, кресла, столы, шкафы — всё для вашего интерьера.\n\n"
            "🛍️ Где посмотреть ассортимент магазина?\n"
            "👇 Нажмите синюю кнопку «Открыть» внизу"
        )

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
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "✅ Открыть бота", callback_data="/open_bot"
                            ),
                            InlineKeyboardButton("🔗 Сайт", url=os.getenv("URL_WEB")),
                        ],
                    ]
                    welcome_text = (
                        "🤖 В группу добавлен бот магазина «Мебель Модно Стильно»! \n"
                        "😊 Создан, чтобы сделать магазин удобным и быстрым.\n\n"
                        "📌 Что он умеет:\n\n"
                        "🛍️ Напишите команду /show, чтобы увидеть каталог товаров прямо в боте\n"
                        "📢 Делиться анонсами новых поступлений\n"
                        "🧹 Удаляет рекламные ссылки сохраняя чат чистым.\n\n"
                        "👉 Используйте команду /bot, чтобы открыть бота."
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
                # Добавляем протокол для проверки
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
        message_id = message.id
        text = message.text or message.caption

        if self.contains_links(text):
            is_admin = await self.check_user_admin(chat_id, user_id, context.bot)
            if is_admin == True:
                await message.delete()
                notice = await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ {message.from_user.mention_html()} ваше сообщение в группе было удалено, "
                    f"так как содержит ссылку.\n\n"
                    f"Ссылки могут отправлять только администратор группы",
                    parse_mode="HTML",
                )

                await asyncio.sleep(2)
                await notice.delete()

    def start(self):
        try:
            print("БОТ ЗАПУЩЕН")
            self.__app.add_handler(CommandHandler("start", self.command_start))
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
