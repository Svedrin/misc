#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Script to run the Valve Map compilers.
# This thing also takes care of running bspzip and renaming files for RCs accordingly.
#
# Copyright (C) Michael "Svedrin" Ziegler
#
# Invocation:
#   compilemap.py <config file> [<target>]

import sys, os, re

from shutil import copy
from os.path import join, exists
from subprocess import Popen
from ConfigParser import ConfigParser


if len(sys.argv) == 1:
	raise RuntimeError( "Usage: compilemap <config file> [<target>]" );

if not exists( sys.argv[1] ):
	raise RuntimeError( "Config file not found..." );

conf = ConfigParser();
conf.read( sys.argv[1] );

if len(sys.argv) > 2:
	target = sys.argv[2];
else:
	target = "default";

targetsec = ":%s" % target;

if not conf.has_section( targetsec ):
	raise KeyError( "Can't build target %s: Section %s not found in the config file." % ( target, targetsec ) );
else:
	print "Building Target", target;
	
mapname      = conf.get( "general", "mapname" );
materialsdir = conf.get( "general", "materialsdir" );
mapsrcdir    = conf.get( "general", "mapsrcdir" );
gamedir      = conf.get( "general", "gamedir" );

vbsp   = conf.get( "programs", "vbsp"   );
vvis   = conf.get( "programs", "vvis"   );
vrad   = conf.get( "programs", "vrad"   );
bspzip = conf.get( "programs", "bspzip" );

confirm = conf.getboolean( targetsec, "confirm" );
showargs = conf.getboolean( targetsec, "showargs" );

bspzip_files  = [];
cleanup_files = [];


# Detect map name
if conf.get( targetsec, "nametag" ):
	tag = conf.get( targetsec, "nametag" );
	regex = re.compile( r"%s_%s(?P<index>\d+)\.bsp" % ( mapname, tag ) );
	maxidx = 0;
	
	for filename in os.listdir( join( gamedir, "maps" ) ):
		m = regex.match( filename );
		if m is not None:
			idx = int( m.group( "index" ) );
			if idx > maxidx:
				maxidx = idx;
	
	mapfilename = "%s_%s%d" % ( mapname, tag, maxidx+1 );

else:
	mapfilename = mapname


print "Source file:", mapname
print "Target file:", mapfilename
print "-" * ( 13 + len(mapfilename) )

if confirm:
	print "Hit enter to start the build process."
	raw_input();


# Skybox preparation
if conf.has_section( "skybox" ):
	skyboxname   = conf.get( "skybox", "name" );

	skybox_sides = ( 'UP', 'DN', 'FT', 'BK', 'LF', 'RT' );

	skybox_vmt_template = """
	"sky"
	{
		"$basetexture" "skybox/%(name)s%(side)s"
		"$hdrbasetexture" "skybox/%(name)s%(side)s"
		"$nofog" "1"
		"$ignorez" "1"
	}
	"""[1:]


	for side in skybox_sides:
		bspbase = join( "materials", "skybox", "%s%s" % ( skyboxname, side ) );
		matbase = join( gamedir, bspbase );
		
		copy(
			join( materialsdir, "%s%s.vtf" % ( skyboxname, side ) ),
			join( matbase+".vtf" ),
			);
		
		# Generate VMT file
		vmt = open( matbase + ".vmt", 'wb' );
		vmt.write( skybox_vmt_template % { 'name': skyboxname, 'side': side } );
		vmt.close();
		
		bspzip_files.append( ( bspbase + ".vtf", matbase + ".vtf" ) );
		bspzip_files.append( ( bspbase + ".vmt", matbase + ".vmt" ) );
		
		cleanup_files.append( matbase + ".vmt" );
		cleanup_files.append( matbase + ".vtf" );



######## BSP ########

bspargs = ( vbsp, "-game", gamedir, join( mapsrcdir, mapname ) );

if showargs:
	print bspargs;

if confirm:
	print "Hit enter to start BSP."
	raw_input();

proc_bsp = Popen( bspargs );
proc_bsp.communicate();



######## VIS ########

visargs = [ vvis ];
if conf.getboolean( targetsec, "fastvis" ): visargs.append( "-fast" );
visargs += [ "-game", gamedir, join( mapsrcdir, mapname ) ];

if showargs:
	print visargs;

if confirm:
	print "Hit enter to start VIS."
	raw_input();

proc_vis = Popen( visargs );
proc_vis.communicate();



######## RAD ########

radargs = [ vrad ];
if conf.getboolean( targetsec, "fastrad" ): radargs.append( "-fast"  );
if conf.getboolean( targetsec, "hdr" ):     radargs.append( "-both"  );
if conf.getboolean( targetsec, "final" ):   radargs.append( "-final" );
radargs += [ "-game", gamedir, join( mapsrcdir, mapname ) ];

if showargs:
	print radargs;

if confirm:
	print "Hit enter to start RAD."
	raw_input();

proc_rad = Popen( radargs );
proc_rad.communicate();


# Overview preparation

overview_vmt_template = """
"UnlitGeneric"
{
	"$translucent" "1"
	"$basetexture" "overviews/%(name)s"
	"$vertexalpha" "1"
	"$no_fullbright" "1"
	"$ignorez" "1"
}
"""[1:]

overview_res_template = """
"%(name)s"
{
	"material" "overviews/%(name)s"
	"pos_x" "%(pos_x)d"
	"pos_y" "%(pos_y)d"
	"scale" "%(scale)f"
	"rotate" "%(rotate)d"
	"zoom" "%(zoom)f"
}
"""[1:]


if conf.has_section( "overview" ):
	for suffix in ( '', '_radar' ):
		bspbase = join( "materials", "overviews", mapname+suffix );
		matbase = join( materialsdir, mapname+suffix );
		
		# Generate VMT file
		vmt = open( matbase + ".vmt", 'wb' );
		vmt.write( overview_vmt_template % { 'name': mapname+suffix } );
		vmt.close();
		
		bspzip_files.append( ( bspbase + ".vtf", matbase + ".vtf" ) );
		bspzip_files.append( ( bspbase + ".vmt", matbase + ".vmt" ) );
		
		cleanup_files.append( matbase + ".vmt" );


	# Generate resource TXT file
	restxt = join( materialsdir, "radar_resource.txt" );
	vmt = open( restxt, 'wb' );
	vmt.write( overview_res_template % {
		'name':   mapname+'_radar',
		'pos_x':  conf.getint(   "overview", "pos_x"  ),
		'pos_y':  conf.getint(   "overview", "pos_y"  ),
		'scale':  conf.getfloat( "overview", "scale"  ),
		'rotate': conf.getint(   "overview", "rotate" ),
		'zoom':   conf.getfloat( "overview", "zoom"   ),
		} );
	vmt.close();

	bspzip_files.append( ( join( "resource", "overviews", mapfilename+".txt" ), restxt ) );
	cleanup_files.append( restxt );



if bspzip_files or conf.has_section( "bspzip" ):
	# BSPZIP file list preparation
	bspfileslist = join( materialsdir, "bspfileslist.txt" );
	cleanup_files.append( bspfileslist );
	filelist = open( bspfileslist, 'wb' );

	if conf.has_section( "bspzip" ):
		for matname, bsppath in conf.items( "bspzip" ):
			filelist.write( bsppath + "\r\n" );
			filelist.write( join( materialsdir, matname ) + "\r\n" );

	for bsppath, matpath in bspzip_files:
		filelist.write( bsppath + "\r\n" );
		filelist.write( matpath + "\r\n" );
		
	filelist.close()

	mapbsp = join( mapsrcdir, mapname + ".bsp" );
	packedbsp = join( mapsrcdir, mapname + "_packed.bsp" );
	
	if exists( packedbsp ):
		os.unlink( packedbsp );

	zipargs = ( bspzip, "-addlist", mapbsp, bspfileslist, packedbsp );
	
	if showargs:
		print zipargs;
		
	if confirm:
		print "Hit enter to start BSPZIP."
		raw_input();
	
	proc_zip = Popen( zipargs );
	proc_zip.communicate();

else:
	packedbsp = join( mapsrcdir, mapname + ".bsp" );


copy( packedbsp, join( gamedir, "maps", mapfilename+".bsp" ) );


for delfile in cleanup_files:
	os.unlink( delfile );


print 
print 
print "-" * ( 13 + len(mapfilename) )
print "Build successful."
print "Source file:", mapname
print "Target file:", mapfilename
print 

if confirm:
	print "Hit enter to exit."
	raw_input();

