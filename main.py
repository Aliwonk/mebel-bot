from bot import BOT
from db import POSTGRES


def main() -> None:
    postgres = POSTGRES()
    if postgres.connect() != None:
        BOT().start()


if __name__ == "__main__":
    main()
