from time import sleep
from importlib import import_module

from bloody_hell_bot.core.bot import BloodyHellBot


def main(config_module='config.dev'):
    config = import_module(config_module)
    bot = BloodyHellBot(config)
    bot.message_loop()

    while 1:
        sleep(10)


if __name__ == '__main__':
    main()
