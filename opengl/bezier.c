#include <stdio.h>
#include <stdlib.h>
#include <GL/glut.h>
#include <time.h>

int g_window;

GLint breite = 1024,
      hoehe  = 768;
int g_points[100][2];
int g_pointsCount = 0;

void init(){
	glClearColor( 1.0, 1.0, 1.0, 1.0 );	/* Hintergrundfarbe auf "weiss" setzen */
	glClear( GL_COLOR_BUFFER_BIT ); 	/* Ansprechen des entsprechenden Puffers */
	glColor3f( 0.0, 0.0, 0.0 ); 		/* Vordergrundfarbe "schwarz" */
	
	glShadeModel( GL_ALPHA );
	}

/*
 * Draw a single Pixel
 */

void putpixel( GLint x, GLint y ){
	glBegin( GL_POINTS );
	glVertex2i( x, y );
	glEnd();
	}


/**
 * Bezier calculation functions
 */

void getpoint( int buffer[], int depth, int index, double factor, int drawLine = 0 ){
	// Recursion end: i = 0. simply return the value from the array.
	if( depth == 0 ){
		buffer[0] = g_points[index][0];
		buffer[1] = g_points[index][1];
		return;
		}
	
	// Get the points in the next higher level that define the line
	int start[2], end[2];
	getpoint( start, depth-1, index,   factor, drawLine );
	getpoint( end,   depth-1, index+1, factor, drawLine );
	
	if( drawLine ){
		glBegin( GL_LINES );
		glVertex2i( start[0], start[1] );
		glVertex2i(   end[0],   end[1] );
		glEnd();
		}
	
	// calculate the point we're looking for
	int dx = end[0] - start[0];
	int dy = end[1] - start[1];
	buffer[0] = start[0] + factor * dx;
	buffer[1] = start[1] + factor * dy;
	}

void drawbezier(){
	time_t start, end;
	int point[2];
	
	start = time(NULL);
	fflush(stdout);
	
	glBegin( GL_LINE_STRIP );
	//glBegin( GL_POINTS );
	glColor3f( 1.0, 0.0, 0.0 );
	for( double percent = 0.0; percent <= 100.0; percent++ ){
		getpoint( point, g_pointsCount - 1, 0, percent/100.0 );
		
		if( (int)percent % 10 == 0 ){
			printf( "%d%%... ", (int)percent );
			fflush(stdout);
			}
		
		glVertex2i( point[0], point[1] );
		}
	end = time(NULL);
	printf( "done (%ld sec).\n", end - start );
	glEnd();
	
	//glColor3f( 0.0, 0.0, 0.0 );
	//getpoint( point, g_pointsCount - 1, 0, 0.5, 1 );
	}

void display(){
	init();
	glMatrixMode( GL_PROJECTION );
	glLoadIdentity();
	glOrtho( 0, breite, 0, hoehe, -1, 1 );
	
	glColor3f( 0.0, 0.0, 0.0 );
	
	glBegin( GL_LINE_STRIP );
	for( int pIdx = 0; pIdx < g_pointsCount; pIdx++ ){
		glVertex2i( g_points[pIdx][0], g_points[pIdx][1] );
		}
	glEnd();
	
	if( g_pointsCount > 0 )
		drawbezier();
	
	glFlush();
	}

void mouseFunc( int button, int state, int xcoord, int ycoord ){
	if( state )
		return;
	//printf( "Mouse at (%d,%d)\n", xcoord, hoehe - ycoord );
	g_points[g_pointsCount][0] = xcoord;
	g_points[g_pointsCount][1] = hoehe - ycoord;
	g_pointsCount++;
	glutPostRedisplay();
	}


int main( int argc, char **argv ){
	glutInit( &argc, argv );
	glutInitDisplayMode( GLUT_RGB );
	
	g_window = glutCreateWindow( "bezierkurve" );
	glutReshapeWindow( breite, hoehe );
	
	glutDisplayFunc( display );
	glutMouseFunc( mouseFunc );
	
	glutMainLoop();
	
	return 0;
	}



