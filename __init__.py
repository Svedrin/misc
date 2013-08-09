# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from sensor import SensorMeta

def __import_sensors():
    import os
    for module in os.listdir(os.path.dirname(__file__)):
        if module.endswith(".py") and module != "__init__.py":
            __import__("sensors." + module.replace(".py", ""))

__import_sensors()
