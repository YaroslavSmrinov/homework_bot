import requests


class RequestException(requests.exceptions.RequestException):
    def __str__(self):
        return 'Something went wrong'
    pass


class Not200status(requests.exceptions.HTTPError):
    def __str__(self):
        return 'Something went wrong'
    pass
