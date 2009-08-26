# -*- coding: utf-8 -*-

"""  Autopatch
Copyright (C) 2009 Michael Ziegler <diese-addy@funzt-halt.net>

Mercurial hook that patches one file according to changes to another one.

This is useful if you distribute a config file for your project by renaming
it to something like settings.py.dist and adding the original settings.py
to .hgignore, but still want to keep it up-to-date when someone makes changes
to it.

Autopatch uses the [autopatch] section in hgrc for its configuration and
understands the following fields:

mail (boolean): Should emails be sent? If so, remember to configure the 
		[email] and [smtp] sections!
sourcefile:	The distributed file to diff, relative from the repo's
		root directory (the one .hg is in).
patchfile:	The hgignored file to apply patches to.

To enable it, set autopatch as the incoming hook for your repos in hgrc.

Autopatch is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This script is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import subprocess
import smtplib

from difflib import unified_diff

from mercurial import util

def autopatch( ui, repo, hooktype, node, **kwargs ):
	
	cc = repo.changectx( node );
	
	fromfile = ui.config( "autopatch", "sourcefile" );
	tofile   = ui.config( "autopatch", "patchfile" );
	
	if not fromfile or not tofile:
		ui.warn( "Repomaster should have configured sourcefile and patchfile in the autopatch section!" );
		return True;
	
	if fromfile not in cc.files():
		ui.status( "%s not affected -> no need to patch.\n" % fromfile );
		return False;
	
	file_after  = cc.filectx( fromfile ).data().splitlines();
	file_before = cc.parents()[0].filectx( fromfile ).data().splitlines();
	
	diff = unified_diff( file_before, file_after, fromfile=( 'a/%s' % tofile ), tofile=( 'b/%s' % tofile ), lineterm="" );
	fulldiff = '\n'.join( [ chunk for chunk in diff ] )
	
	ui.debug( fulldiff );
	
	patch = subprocess.Popen(
		( 'patch', '-Nt', tofile ),
		stdin  = subprocess.PIPE,
		stdout = subprocess.PIPE,
		stderr = subprocess.PIPE,
		cwd    = repo.root,
		);
	patchout, patcherr = patch.communicate( input=fulldiff );
	
	if patch.returncode:
		if repo.ui.configbool( "autopatch", "mail", default=True ) and ui.config( "email", "to" ):
			ui.warn( "failed patching %s, mailing details to repomaster.\n" % tofile );
			ui.debug( patchout );
			ui.debug( patcherr );
			
			fromaddr = ui.config( "email", "from" );
			toaddr   = ui.config( "email", "to"   );
			smtphost = ui.config( "smtp",  "host", default="localhost" );
			
			if not fromaddr or not toaddr:
				ui.warn( "Repomaster should have configured from and to in the email section!" );
				return True;
			
			mail =  "From: %(fromaddr)s\n" \
				"To: %(toaddr)s\n" \
				"Subject: %(tofile)s patch report for commit %(rev)d\n" \
				"\n" \
				"Hai Admins,\n" \
				"\n" \
				"%(fromfile)s has been changed in commit %(rev)d by %(user)s, but patching failed.\n" \
				"\n" \
				"Log message:\n" \
				"%(desc)s\n\n" \
				"I tried to apply this patch: \n" \
				"%(diff)s\n\n" \
				"Here comes the patch report:\n" \
				"%(patch)s\n\n" \
				"\n" % {
					'fromaddr': fromaddr,
					'toaddr':   toaddr,
					'fromfile': fromfile,
					'tofile':   tofile,
					'rev':      cc.rev(),
					'user':     cc.user(),
					'desc':     cc.description(),
					'diff':     fulldiff,
					'patch':    patchout + patcherr
					};
			
			serv = smtplib.SMTP( smtphost );
			serv.sendmail( util.email(fromaddr), util.email(toaddr), mail );
			serv.quit();
		
		else:
			ui.warn( "failed patching %s and emailing is disabled! Patch said:" % tofile );
			ui.warn( patchout );
			ui.warn( patcherr );
	
	else:
		ui.status( "Successfully patched %s.\n" % tofile );
	
	return False;
	


