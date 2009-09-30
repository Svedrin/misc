# -*- coding: utf-8 -*-

"""
    A simple Bezier rendering program.

    Copyright (C) 2009, Michael "Svedrin" Ziegler <diese-addy@funzt-halt.net>
"""

import sys

from time		import time

from OpenGL.GL		import *
from OpenGL.GLUT	import *


class Bezier( object ):
	def __init__( self, width=1024, height=768, debug=False, progress=True ):
		""" Save settings and init the window """
		self.width    = width;
		self.height   = height;
		self.debug    = debug;
		self.progress = progress;
		
		self.points = [];
		
		glutInit( sys.argv );
		glutInitDisplayMode( GLUT_RGB );
		
		self.window = glutCreateWindow( "bezierkurve" );
		glutReshapeWindow( width, height );
		
		glutDisplayFunc( self.display   );
		glutMouseFunc(   self.mouseFunc );
	
	
	def getpoint( self, depth, index, factor, drawLine=False ):
		""" Recursively calculate the position of one vertex. """
		# Recursion end: i = 0. simply return the value from the array.
		if depth == 0:
			return self.points[index];
		
		# Get the points in the next higher level that define the line
		start = self.getpoint( depth-1, index,   factor, drawLine );
		end   = self.getpoint( depth-1, index+1, factor, drawLine );
		
		if drawLine:
			glBegin( GL_LINES );
			glVertex2i( *start );
			glVertex2i( *end   );
			glEnd();
		
		# calculate the point we're looking for
		dx = end[0] - start[0];
		dy = end[1] - start[1];
		
		px = start[0] + factor * dx;
		py = start[1] + factor * dy;
		
		return int(px), int(py);
	
	
	def drawbezier( self ):
		""" Re-render the bezier. """
		if self.progress:
			start = time();
		
		glColor3f( 1.0, 0.0, 0.0 );
		
		glBegin( GL_LINE_STRIP );
		
		for percent in range(101):
			point = self.getpoint( len(self.points) - 1, 0, percent/100.0 );
			
			if self.progress and percent < 100 and percent % 10 == 0 :
				sys.stdout.write( "%d%%... " % int(percent) );
				sys.stdout.flush();
			
			glVertex2i( *point );
		
		glEnd();
		
		if self.progress:
			end = time();
			sys.stdout.write( "done (%f.5 sec).\n" % ( end - start ) );
			sys.stdout.flush();
		
		if self.debug:
			glColor3f( 0.0, 0.0, 0.0 );
			self.getpoint( len(self.points) - 1, 0, 0.5, True );
	
	
	def display( self ):
		""" Display function hooked into GLUT. """
		glClearColor( 1.0, 1.0, 1.0, 1.0 );
		glClear( GL_COLOR_BUFFER_BIT );
		glColor3f( 0.0, 0.0, 0.0 );
		
		glMatrixMode( GL_PROJECTION );
		glLoadIdentity();
		glOrtho( 0, self.width, 0, self.height, -1, 1 );
		
		glColor3f( 0.0, 0.0, 0.0 );
		
		glBegin( GL_LINE_STRIP );
		for pnt in self.points:
			glVertex2i( *pnt );
		glEnd();
		
		if self.points:
			self.drawbezier();
		
		glFlush();
	
	
	def mouseFunc( self, button, state, xcoord, ycoord ):
		""" Mouse callback hooked into GLUT that adds another vertex to the controlling polygon. """
		if state:
			return;
		self.points.append( ( xcoord, self.height - ycoord ) );
		glutPostRedisplay();


if __name__ == '__main__':
	from optparse import OptionParser
	
	op = OptionParser();
	
	op.add_option( '-d', '--debug',    dest="debug",    default=False,  action="store_true",
		help='Draw a Debug line after rendering the Bezier that demonstrates the calculation'
		);
	
	op.add_option( '-p', '--progress', dest="progress", default=False,  action="store_true",
		help='Show the progress when redrawing in the console in 10% steps.'
		);
	
	op.add_option( '-x', '--width',    dest="width",    default=1024,   action="store", type="int",
		help='Set the initial width of the window.'
		);
	
	op.add_option( '-y', '--height',   dest="height",   default=768,    action="store", type="int",
		help='Set the initial height of the window.'
		);
	
	options, args = op.parse_args();
	
	bz = Bezier( **(options.__dict__) );
	glutMainLoop();

