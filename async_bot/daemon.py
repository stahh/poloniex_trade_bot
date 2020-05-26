import sys
import signal
from concurrent.futures import ThreadPoolExecutor
sys.path.append('../')
from asyncio import Event
from async_bot.workers.checker import Checker
from async_bot.workers.ticker import Ticker
from async_bot.workers.subscriber import Subscriber


def start(claz):
    claz.run()


def sigterm_handler(signum, frame):
    for claz in classes:
        claz.ex_ev.set()


if __name__ == '__main__':
    # Создание таблицы
    # Base.metadata.drop_all(engine)
    # Base.metadata.create_all(engine)
    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)
    ev = Event()
    classes = [
        Checker(ev),
        Ticker(ev),
        Subscriber(ev)
    ]
    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = executor.map(start, classes)

    except KeyboardInterrupt:
        for clazz in classes:
            clazz.ex_ev.set()
