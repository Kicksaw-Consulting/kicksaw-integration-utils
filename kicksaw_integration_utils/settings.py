from tempfile import gettempdir


TEMP = gettempdir()

try:
    from django.conf import settings

    TEMP = settings.TEMP
except ModuleNotFoundError:
    pass

try:
    from chalicelib import settings

    TEMP = settings.TEMP
except ModuleNotFoundError:
    pass
