import re
import sys

from tempfile import gettempdir

TEMP = gettempdir()

try:
    # settings is not a module; it's an instance of a class
    from django.conf import settings

    current_module = sys.modules[__name__]

    # loop through class properties
    for setting in dir(settings):
        # if the property name matches the variable name for a django setting,
        # e.g., INSTALLED_APPS, set it as a variable for this module
        # with the same name
        if re.match("^[A-Z]+(?:_[A-Z]+)*$", setting):
            setattr(current_module, setting, getattr(settings, setting))
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
