# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import json
import requests

from django.db import models
from django.contrib.sites.models import Site
from django.contrib.auth.models import User

class PushOverNetError(Exception):
    pass

class PushOverNetApp(models.Model):
    site        = models.OneToOneField(Site)
    app_token   = models.CharField(max_length=35)

class PushOverNetUser(models.Model):
    owner       = models.OneToOneField(User)
    user_token  = models.CharField(max_length=35)

    def notify(self, message, **kwargs):
        """ Send a notification to the user.

            For documentation on kwargs see <https://pushover.net/api>.
        """
        kwcopy = kwargs.copy()
        kwcopy.update({
            "token":    Site.objects.get_current().pushovernetapp.app_token,
            "user":     self.user_token,
            "message":  message,
            "priority": kwcopy.get("priority", -1),
        })

        resp = requests.post("https://api.pushover.net/1/messages.json", kwcopy)

        try:
            respdata = json.loads(resp.text)
        except ValueError, err:
            raise PushOverNetError("Response failed to decode: " + unicode(err))

        if resp.status_code != 200 or respdata.get("status", None) != 1:
            raise PushOverNetError(respdata.get("errors", "Unknown error"))
