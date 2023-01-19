class BaseCustomException(Exception):
    pass


class RequestException(BaseCustomException):
    pass


class CustomTelegramError(BaseCustomException):
    pass


class HTTPError(BaseCustomException):
    pass


class PractikumException(BaseCustomException):
    pass
