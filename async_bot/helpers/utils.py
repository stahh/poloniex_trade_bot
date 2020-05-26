import requests
import asyncio
import time
import coloredlogs
import logging
from multiprocessing import current_process
import ctypes
import os
from datetime import datetime, timezone

libc = ctypes.cdll.LoadLibrary('libc.so.6')
# System dependent, see e.g. /usr/include/x86_64-linux-gnu/asm/unistd_64.h
SYS_gettid = 186


def get_thread_id():
    """Returns OS thread id - Specific to Linux"""
    return libc.syscall(SYS_gettid)


def get_logger(name):
    if not os.path.exists(f'{os.getcwd()}/../../logs/'):
        os.mkdir(f'{os.getcwd()}/../../logs/')
    frmt = '%(asctime)s %(name)s[' + str(get_thread_id()) + '] ' \
           '%(levelname)s %(message)s'
    logging.basicConfig(level=logging.INFO, format=frmt)
    log = logging.getLogger(name)
    file_handler = logging.FileHandler('../../logs/coin_bot.log')
    # stream_handler = logging.StreamHandler()
    log.addHandler(file_handler)
    # log.addHandler(stream_handler)
    coloredlogs.install(level='INFO', logger=log, fmt=frmt)
    return log


async def current_state(exit_event):
    """
    calc alive workers in loop with coroutine
    :param exit_event_inner: event to stop logging
    :param loop: asyncio event loop
    :return:
    """
    log = logging.getLogger(current_process().name)
    while not exit_event.is_set():
        current_tasks = asyncio.Task.all_tasks()
        log.info('Active tasks count: {} / {}.'.format(
            len([task for task in current_tasks if not task.done()]),
            len(current_tasks)
        ))
        await asyncio.sleep(10)


def get_btc_value(coin_name=None, count=None):
    time.sleep(0.1)
    if not coin_name or not count:
        return 0
    else:
        if coin_name.lower() == 'dsh':
            coin_name = 'dash'
        response = None
        try:
            response = requests.get(f'https://api.cryptonator.com/api/'
                                    f'ticker/btc-{coin_name.lower()}').json()
        except:
            pass
        if response and response.get('success'):
            return float(count) / float(response['ticker']['price'])
        else:
            return 0


def get_usd_value(coin_name=None, count=None):
    time.sleep(0.1)
    if not coin_name or not count:
        return 0
    else:
        if coin_name.lower() == 'dsh':
            coin_name = 'dash'
        response = None
        try:
            response = requests.get(f'https://api.cryptonator.com/api/ticker/'
                                    f'usd-{coin_name.lower()}').json()
        except:
            pass
        if response and response.get('success'):
            return float(count) / float(response['ticker']['price'])
        else:
            return 0


def get_next_point(x1, x2, y1, y2, x):
    k = (y1 - y2) / (x1 - x2) or 1
    b = y2 - k * x2
    y = k * x + b
    return y


def calculate_upper_bottom(point):
    up_x1 = point.point_high_first_date.timestamp()
    up_y1 = float(point.point_high_first)
    up_x2 = point.point_high_last_date.timestamp()
    up_y2 = float(point.point_high_last)
    up_x3 = datetime.now(timezone.utc).timestamp()

    bt_x1 = point.point_low_first_date.timestamp()
    bt_y1 = float(point.point_low_first)
    bt_x2 = point.point_low_last_date.timestamp()
    bt_y2 = float(point.point_low_last)
    bt_x3 = datetime.now(timezone.utc).timestamp()

    up_y3 = get_next_point(up_x1, up_x2, up_y1, up_y2, up_x3)
    bt_y3 = get_next_point(bt_x1, bt_x2, bt_y1, bt_y2, bt_x3)

    upper_line = [(datetime.fromtimestamp(up_x1), up_y1),
                  (datetime.fromtimestamp(up_x2), up_y2),
                  (datetime.fromtimestamp(up_x3), up_y3)]
    bottom_line = [(datetime.fromtimestamp(bt_x1), bt_y1),
                   (datetime.fromtimestamp(bt_x2), bt_y2),
                   (datetime.fromtimestamp(bt_x3), bt_y3)]

    return up_y3, bt_y3, upper_line, bottom_line
