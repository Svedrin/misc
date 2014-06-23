# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django        import forms
from django.conf   import settings
from django.forms  import Form
from django.utils.translation import ugettext_lazy as _, ugettext

from mptt.forms    import TreeNodeChoiceField

from hosts.models  import Domain

class ConfirmHostDeleteForm( Form ):
    fqdn    = forms.CharField(help_text=_("Please enter the FQDN of the host you wish to delete to confirm."))

class AddHostForm( Form ):
    fqdn    = forms.CharField(help_text=_("host.somedomain.com"))
    pubkey  = forms.CharField(help_text=_("the contents of .keys/id_rsa_4096.pub"), widget=forms.Textarea())
