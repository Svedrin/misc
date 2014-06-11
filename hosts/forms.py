# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django        import forms
from django.conf   import settings
from django.forms  import Form
from django.utils.translation import ugettext_lazy as _, ugettext

class ConfirmHostDeleteForm( Form ):
    fqdn    = forms.CharField(help_text=_("Please enter the FQDN of the host you wish to delete to confirm."))
