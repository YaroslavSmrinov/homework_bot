import json
import logging
import os
import time
from http import HTTPStatus
from sys import exit, stdout

import requests
import telegram
from dotenv import load_dotenv

from custom_exceptions import (CustomTelegramError, HTTPError,
                               PractikumException, RequestException)

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


def check_tokens() -> bool:
    """.
    Проверяет доступность переменных окружения,
    которые необходимы для работы программы.
    """
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    for token in tokens:
        if not tokens[token]:
            logger.critical(f'{token} не найден. Остановил работу программы')
            return False
    logger.info('Все токены в порядке.')
    return True


def send_message(bot, message) -> None:
    """.
    Отправляет сообщение в Telegram чат, определяемый переменной
    окружения TELEGRAM_CHAT_ID. Принимает на вход два параметра:
    экземпляр класса Bot и строку с текстом сообщения
    """
    try:
        logger.info('Попытка отправить сообщение в телеграм.')
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.debug('Сообщение в телеграм успешно отправлено.')
    except telegram.error.TelegramError as error:
        logger.error(f'Ошибка при отправке. Причина: {error}')
        raise CustomTelegramError(f'Ошибка телеграм {error}')
    except CustomTelegramError as error:
        logger.error(f'Ошибка при отправке. Причина: {error}')
        raise CustomTelegramError(f'Ошибка телеграм {error}')


def get_api_answer(timestamp) -> dict:
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
        if response.status_code == HTTPStatus.OK:
            logger.info('Успешно получили информацию от практикума.')
            try:
                logger.info('Преобразуем ответ в json формат.')
                return response.json()
            except json.decoder.JSONDecodeError as error:
                raise json.decoder.JSONDecodeError(f'Ошибка преобазования '
                                                   f'ответа в json {error}')
        else:
            raise PractikumException(f'Практикум недоступен {HTTPError}')
    except requests.exceptions.RequestException as error:
        raise RequestException(f'Ошибка в запросе к практикуму. {error}')


def check_response(response) -> dict | None:
    """
    проверяет ответ API на соответствие документации.
    В качестве параметра функция получает ответ API,
    приведенный к типам данных Python.
    В случае успеха возвращает последнюю домашку
    """
    if not isinstance(response, dict):
        raise TypeError(f'Ожидал получить словарь, '
                        f'получил {response}.')
    if 'homeworks' not in response:
        raise PractikumException(f'Нужных ключей нет, '
                                 f'только это {response.keys()}')
    if not isinstance(response['homeworks'], list):
        raise TypeError(f'Ожидал список c ключом homeworks, '
                        f'получил {response["homeworks"]}.')
    if len(response['homeworks']) < 1:
        logging.info('Отсутствуют работы в списке')
        return None
    return response.get('homeworks')[0]


def parse_status(homework) -> str:
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает только один элемент из списка
    домашних работ. В случае успеха, возвращает подготовленную для отправки
    в Telegram строку, содержащую один из вердиктов словаря HOMEWORK_VERDICTS.
    """
    if homework.get('status') not in HOMEWORK_VERDICTS.keys():
        raise KeyError(f'Неожиданный статус {homework.get("status")}')
    if 'homework_name' not in homework:
        raise KeyError(f'Не нашел ключик "homework_name", '
                       f'только вот это {homework.keys()}')
    hw_status = homework.get('status')
    hw_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS.get(hw_status)
    return f'Изменился статус проверки работы "{hw_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logger.info('Start program')
    if not check_tokens():
        logger.info('Program stopped')
        exit(os.EX_DATAERR)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error = None

    while True:
        practicum_resp = get_api_answer(timestamp)
        try:
            homework = check_response(practicum_resp)
            msg = parse_status(homework)
            if msg:
                send_message(bot, msg)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if error is not last_error:
                send_message(bot, message)
                last_error = error

        finally:
            timestamp = practicum_resp.get('current_date')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
