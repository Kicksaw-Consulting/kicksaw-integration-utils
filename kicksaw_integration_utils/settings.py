from tempfile import gettempdir


TEMP = gettempdir()

try:
    from django.conf.settings import *
except ModuleNotFoundError:
    pass

try:
    from chalicelib.settings import *
except ModuleNotFoundError:
    pass

try:
    from config.settings import *
except ModuleNotFoundError:
    pass