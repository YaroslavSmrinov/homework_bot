import logging
import os
import requests
from sys import stdout
import time

import telegram
from dotenv import load_dotenv

from custom_exceptions import RequestException, Not200status


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(funcName)s,  %(message)s'
)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stdout)
logger.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверяет доступность переменных окружения,
    которые необходимы для работы программы.
    """
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    for token in tokens:
        if tokens[token] is None:
            logger.critical(f'Can\'t get {token} from venv. Check .env file')
            return False
    logger.info('All tokens found.')
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат, определяемый переменной
    окружения TELEGRAM_CHAT_ID. Принимает на вход два параметра:
    экземпляр класса Bot и строку с текстом сообщения
    """
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.debug('Message to telegram successfully sent')
    except Exception as error:
        logger.error(f'Message to telegram wasn\'t sent. Reason {error}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра в функцию передается временная метка.
    В случае успешного запроса должна вернуть ответ API,
    приведя его из формата JSON к типам данных Python.
    """
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp})
        if response.status_code == 200:
            logger.info('Got data from endpoint')
            return response.json()
        else:
            logger.error(f'Практикум недоступен {response.status_code}')
            raise Not200status
    except requests.exceptions.RequestException as error:
        logger.error(f'Что-то не так {error}')
        raise (RequestException, error)


def check_response(response):  # loging required
    """
    проверяет ответ API на соответствие документации.
    В качестве параметра функция получает ответ API,
    приведенный к типам данных Python.
    В случае успеха возвращает последнюю домашку
    """
    if not isinstance(response, dict):
        logger.error('Wrong API RESP')
        raise TypeError
    if 'homeworks' not in response:
        logger.error('Can\' find keys')
        raise KeyError
    if not isinstance(response['homeworks'], list):
        logger.error('Wrong API RESP')
        raise TypeError
    if len(response['homeworks']) < 1:
        logger.debug('Отсутствуют работы в списке')
        raise IndexError
    return response.get('homeworks')[0]


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает только один элемент из списка
    домашних работ. В случае успеха, возвращает подготовленную для отправки
    в Telegram строку, содержащую один из вердиктов словаря HOMEWORK_VERDICTS.
    """
    if homework.get('status') not in HOMEWORK_VERDICTS.keys():
        logger.error(f'Unexpected status {homework.get("status")}')
        raise KeyError
    if 'homework_name' not in homework:
        logger.error('Can\' find keys')
        raise KeyError
    hw_status = homework.get('status')
    hw_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS.get(hw_status)
    return f'Изменился статус проверки работы "{hw_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logger.info('Start program')
    if not check_tokens():
        logger.info('Program stopped')
        return None

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error = None

    while True:
        try:
            practicum_resp = get_api_answer(timestamp)
            homework = check_response(practicum_resp)
            msg = parse_status(homework)
            if msg:
                send_message(bot, msg)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if error is last_error:
                send_message(bot, message)
                last_error = error

        finally:
            timestamp = int(time.time())
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
