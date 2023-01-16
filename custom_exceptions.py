import requests
from telegram.error import TelegramError


class RequestException(requests.exceptions.RequestException):
    pass


class CustomTelegramError(TelegramError):
    pass


class HTTPError(requests.exceptions.HTTPError):
    pass


class PractikumException(Exception):
    pass

