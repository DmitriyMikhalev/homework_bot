import os
import time
import logging
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (
    ConnectApiError,
    ResponseStatusError,
)

load_dotenv()

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()

logger.setLevel(logging.INFO)
logger.addHandler(handler)

formatter = logging.Formatter(
    '%(levelname)s - %(asctime)s - %(name)s - %(message)s'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
RETRY_TIME = 600


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
    'reviewing': 'Работа взята на проверку ревьюером.',
}


def check_response(response):
    """Return dict from API response.
    Args: response --> json formatted to python types.
    """
    return response["homeworks"][0]


def check_tokens():
    """Return True if private data is available, other cases return False."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True

    logger.error('Private data is not given!')


def get_api_answer(timestamp=0):
    """Return API response -> json formatted to python types if it possible.
    Throwing exception if any problems with API answer.
    Arg: timestamp (int), default is 0 ---> UNIX timestamp.
    Timestamp defines the start of new answer is awaiting.
    """
    try:
        response = requests.get(
            headers=HEADERS,
            params={'from_date': timestamp},
            url=ENDPOINT
        )

        if response.status_code != HTTPStatus.OK:
            raise ResponseStatusError(
                f'API response status code {response.status_code}.'
                + 'Should be 200!'
            )

    except Exception:
        raise ConnectApiError('Failed to get API answer!')

    return response.json()


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    while True:
        try:
            response = get_api_answer(int(time.time()) - RETRY_TIME)
            homework = check_response(response)

            if homework:
                bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=parse_status(homework)
                )

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.critical(message)

            bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message
            )

        finally:
            time.sleep(RETRY_TIME)


def parse_status(homework):
    """Return str message about update at API answer."""
    if "homework_name" not in homework:
        raise KeyError('No homework name at homework dict!')

    if "status" not in homework:
        raise KeyError('No status at homework dict!')

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    try:
        verdict = HOMEWORK_STATUSES[homework_status]

    except Exception:
        logger.error('Status is undefined!')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Ask bot to send message. Args: telegram.Bot and message (str)."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.info('Telegram message is submitted.')

    except telegram.TelegramError as error:
        logger.error(f'Telegram message was not submitted: {error}')


if __name__ == '__main__':
    main()
