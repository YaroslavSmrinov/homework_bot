class MyException(Exception):
    pass


class RequestException(MyException):
    pass


class CustomTelegramError(MyException):
    pass


class HTTPError(MyException):
    pass


class PractikumException(MyException):
    pass
