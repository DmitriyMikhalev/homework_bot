import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import SendMessageError

load_dotenv()

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()

logger.setLevel(logging.INFO)
logger.addHandler(handler)

formatter = logging.Formatter(
    '%(levelname)s - %(asctime)s - %(funcName)s'
    + ' - %(lineno)d - %(name)s - %(message)s'
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
    """Return list of homeworks from API response.
    Args: response --> json formatted to python types.
    """
    if not isinstance(response, dict):
        raise TypeError('Response is not a dict!')

    if not all(key in response for key in ('homeworks', 'current_date')):
        raise KeyError('Response doesn\'t have needed keys!')

    if not isinstance(response['homeworks'], list):
        raise TypeError('Response has incorrect format of homeworks sequence!')

    logger.debug('Reponse has correct format.')
    return response['homeworks']


def check_tokens():
    """Return True if private data is available, other cases return False."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        logger.debug('Private data is correct.')
        return True

    logger.critical('Private data is not given!')
    return False


def get_api_answer(timestamp=0):
    """Return API response -> json formatted to python types if it possible.
    Throwing exception if any problems with API answer.
    Arg: timestamp (int), default is 0 ---> UNIX timestamp.
    Timestamp defines the start of new answer is awaiting.
    """
    response = requests.get(
        headers=HEADERS,
        params={'from_date': timestamp},
        url=ENDPOINT
    )
    if response.status_code != HTTPStatus.OK:
        response.raise_for_status()

    logger.debug('JSON was formatted successfully.')
    return response.json()


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    errors_occured = True

    while True:
        try:
            response = get_api_answer(int(time.time()) - RETRY_TIME)
            homeworks = check_response(response)

            if homeworks:
                send_message(
                    bot=bot,
                    message=parse_status(homeworks[0])
                )
            else:
                logger.info(
                    'Everything was correct but where is no message to send.'
                )
        except Exception as error:
            message = f'Сбой в работе программы:\n{error}'
            logger.exception(msg=message)

            if errors_occured:
                errors_occured = False
                bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=message
                )
        finally:
            time.sleep(RETRY_TIME)


def parse_status(homework):
    """Return str message about update at API answer."""
    if 'homework_name' not in homework or 'status' not in homework:
        raise KeyError('No homework name or status at homework dict!')

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES.get(homework_status)

    if verdict is None:
        raise KeyError('Homework status is undefined!')

    logger.debug('Status was parsed successfully.')
    return f'Изменился статус проверки работы "{homework_name}".\n\n{verdict}'


def send_message(bot, message):
    """Ask bot to send message. Args: telegram.Bot and message (str)."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
    except telegram.error.TelegramError as error:
        raise SendMessageError(f'Unable to send message! {error}')

    logger.debug('Telegram message was submitted.')


if __name__ == '__main__':
    main()
