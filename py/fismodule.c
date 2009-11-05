/**
 *  Python Module to run Fuzzy Calculations using fis.c from MATLAB.
 *
 *  Copyright © 2009, Michael "Svedrin" Ziegler <diese-addy@funzt-halt.net>
 */


#include <pthread.h>
#include <setjmp.h>
#include <stdarg.h>
#include <Python.h>

// Fix the uberly borked error handling in fis.c.
// fisError first calls printf, then exit.
// Replace printf with a function that raises an Exception in the Python layer,
// and replace exit with a longjmp to allow the original function call to
// return NULL.

// Define an output function to be used by fis.c. Will raise a RuntimeError exception in Python.
void print_py( const char* format, ... );

jmp_buf jumper;
pthread_mutex_t jumper_lock;

#define printf print_py
#define exit( num )   longjmp( jumper, 1 )

#include "fis.c"

#undef printf
#undef exit


/**
 *  The FIS object type.
 *
 *  These fields do not get exposed to the Python layer.
 */
typedef struct {
	PyObject_HEAD
	const char *fis_file;
	int         fis_row_n, fis_col_n;
	DOUBLE    **fisMatrix;
	FIS        *fis;
} fisObject;


/**
 *  Docstrings.
 */

#define MOD_DOCSTRING "Python Module that provides MATLAB's FIS engine.\n"\
	"\n"\
	"Copyright © 2009, Michael \"Svedrin\" Ziegler <diese-addy@funzt-halt.net>"

#define FIS_DOCSTRING ""\
	"This class completely handles the processing of the FIS file and Fuzzy calculations.\n"\
	"\n"\
	"Usage:\n"\
	">>> import fis\n"\
	">>> f = fis.FIS( '/home/svedrin/fh/wbs/pyrobo/test.fis' )\n"\
	">>> f.getInputs()\n"\
	"5\n"\
	">>> f.getOutputs()\n"\
	"2\n"\
	">>> f( 200, 600, 200, 0, 0 )\n"\
	"(1, 1)\n"\
	"\n"\
	"As you see, you need to pass the path to the FIS file to the constructor of\n"\
	"the FIS class. The FIS instance will then provide access to the FIS processor\n"\
	"created from that file, via the methods listed below. To evaluate the rules\n"\
	"for a set of inputs, simply call the FIS instance and pass the values for the\n"\
	"respective input variables in the arguments to that call. You will then\n"\
	"receive a tuple containing the values for the respective output variables.\n"


/**
 *  Constructor for new FIS objects.
 */
static PyObject* fis_new( PyTypeObject* type, PyObject* args ){
	fisObject* self;
	FILE* fp;
	
	self = (fisObject *) type->tp_alloc( type, 0 );
	
	if( self == NULL )
		return NULL;
	
	if( !PyArg_ParseTuple( args, "s", &self->fis_file ) )
		return NULL;
	
	// First of all, try to open the FIS file to see if it exists.
	if( ( fp = fopen( self->fis_file, "r" ) ) != NULL ){
		fclose(fp);
	}
	else{
		PyErr_SetFromErrnoWithFilename( PyExc_IOError, (char *)self->fis_file );
		return NULL;
	}
	
	// Catch exceptions
	pthread_mutex_lock( &jumper_lock );
	if( setjmp( jumper ) == 1 ){
		pthread_mutex_unlock( &jumper_lock );
		return NULL;
	}
	
	// Parse file into FIS Matrix
	self->fisMatrix = returnFismatrix( (char *)self->fis_file, &self->fis_row_n, &self->fis_col_n );
	
	// Create FIS node from the Matrix
	self->fis = (FIS *)fisCalloc( 1, sizeof(FIS) );
	fisBuildFisNode( self->fis, self->fisMatrix, self->fis_col_n, MF_POINT_N );
	
	pthread_mutex_unlock( &jumper_lock );
	
	return (PyObject *)self;
}

/**
 *  Destructor for FIS objects. Frees memory used by the Matrix and the Node.
 */
static void fis_dealloc( fisObject* self ){
	fisFreeMatrix( (void **)self->fisMatrix, self->fis_row_n );
	fisFreeFisNode( self->fis );
}

/**
 *  The FIS processing function. Takes input values as *args, runs the FIS calculation
 *  and returns the output values as a Tuple.
 */
static PyObject* fis_process( fisObject* self, PyObject* args ){
	DOUBLE     *input,  *output;
	PyObject   *result, *currItem;
	Py_ssize_t argc, argIdx, resIdx;
	
	
	// Sanity checks
	if( !PyTuple_Check( args ) ){
		PyErr_SetString( PyExc_TypeError, "Args is not a tuple." );
		return NULL;
	}
	
	argc = PyTuple_Size( args );
	
	if( argc != self->fis->in_n ){
		PyErr_SetString( PyExc_IndexError, "You need to provide as many arguments as there are input variables." );
		return NULL;
	}
	
	// Build input vector
	input = (DOUBLE *) fisCalloc( self->fis->in_n, sizeof(DOUBLE) );
	if( input == NULL )
		return NULL;
	
	for( argIdx = 0; argIdx < argc; argIdx++ ){
		currItem = PyTuple_GetItem( args, argIdx );
		
		if( PyFloat_Check( currItem ) )
			input[argIdx] = (DOUBLE) PyFloat_AsDouble( currItem );
		else if( PyInt_Check( currItem ) )
			input[argIdx] = (DOUBLE) PyInt_AsLong( currItem );
		else{
			PyErr_SetString( PyExc_TypeError, "Args must be of type int or float." );
			free(input);
			return NULL;
		}
	}
	
	// Build output vector
	output = (DOUBLE *) fisCalloc( self->fis->out_n, sizeof(DOUBLE) );
	if( output == NULL ){
		free(input);
		return NULL;
	}
	
	// Catch exceptions
	pthread_mutex_lock( &jumper_lock );
	if( setjmp( jumper ) == 1 ){
		pthread_mutex_unlock( &jumper_lock );
		free(input);
		free(output);
		return NULL;
	}
	
	// Run the calculation
	getFisOutput( input, self->fis, output );
	
	pthread_mutex_unlock( &jumper_lock );
	
	free(input);
	
	// Convert the output vector to a Python tuple
	result = PyTuple_New( (Py_ssize_t)self->fis->out_n );
	if( result == NULL ){
		free(output);
		return NULL;
	}
	
	for( resIdx = 0; resIdx < self->fis->out_n; resIdx++ ){
		PyTuple_SetItem( result, resIdx, PyFloat_FromDouble( output[resIdx] ) );
	}
	
	free(output);
	
	return (PyObject *)result;
}

/**
 *  Get the FIS matrix as a (2dim) Python Tuple.
 */
static PyObject* fis_getMatrix( fisObject* self ){
	int mtxRowIdx, mtxColIdx;
	PyObject *result, *resultRow;
	
	result = PyTuple_New( (Py_ssize_t)self->fis_row_n );
	if( result == NULL )
		return NULL;
	
	for( mtxRowIdx = 0; mtxRowIdx < self->fis_row_n; mtxRowIdx++ ){
		resultRow = PyTuple_New( (Py_ssize_t)self->fis_col_n );
		if( resultRow == NULL )
			return NULL;
		
		for( mtxColIdx = 0; mtxColIdx < self->fis_col_n; mtxColIdx++ ){
			PyTuple_SetItem(
				resultRow, (Py_ssize_t)mtxColIdx,
				PyFloat_FromDouble( self->fisMatrix[mtxRowIdx][mtxColIdx] )
				);
		}
		
		PyTuple_SetItem( result, (Py_ssize_t)mtxRowIdx, resultRow );
	}
	
	return (PyObject *)result;
}

/**
 *  Get the file path used to open the FIS file.
 */
static PyObject* fis_getPath( fisObject* self ){
	return Py_BuildValue( "s", self->fis_file );
}

/**
 *  Macros to easily create getters for FIS fields.
 */

#define FIS_FIELD_GETTER_IMPL( PythonName, FisName, TypeStr )      \
static PyObject* fis_get##PythonName ( fisObject* self ){          \
	return Py_BuildValue( TypeStr, self->fis-> FisName );      \
}

#define FIS_FIELD_GETTER_DEF(  PythonName, DocString ) \
	{ "get" #PythonName, (PyCFunction)fis_get##PythonName, METH_NOARGS, DocString },


FIS_FIELD_GETTER_IMPL( Inputs,		in_n,		"i" )
FIS_FIELD_GETTER_IMPL( Outputs, 	out_n,		"i" )
FIS_FIELD_GETTER_IMPL( Rules,		rule_n, 	"i" )
FIS_FIELD_GETTER_IMPL( Name,		name,		"s" )
FIS_FIELD_GETTER_IMPL( Type,		type,		"s" )
FIS_FIELD_GETTER_IMPL( AndMethod,	andMethod,	"s" )
FIS_FIELD_GETTER_IMPL( OrMethod,	orMethod,	"s" )
FIS_FIELD_GETTER_IMPL( ImpMethod,	impMethod,	"s" )
FIS_FIELD_GETTER_IMPL( AggMethod,	aggMethod,	"s" )
FIS_FIELD_GETTER_IMPL( DefuzzMethod,	defuzzMethod,	"s" )



/**
 *  FIS Object definitions.
 */
static PyMethodDef fisObject_Methods[] = {
	FIS_FIELD_GETTER_DEF( Matrix,		"Return the FIS matrix as a 2-dimensional Tuple." )
	FIS_FIELD_GETTER_DEF( Path,		"Return the file path used to open the FIS file." )
	FIS_FIELD_GETTER_DEF( Inputs,		"Return the number of input variables." )
	FIS_FIELD_GETTER_DEF( Outputs,		"Return the number of output variables." )
	FIS_FIELD_GETTER_DEF( Rules,		"Return the number of rules." )
	FIS_FIELD_GETTER_DEF( Name,		NULL )
	FIS_FIELD_GETTER_DEF( Type,		NULL )
	FIS_FIELD_GETTER_DEF( AndMethod,	NULL )
	FIS_FIELD_GETTER_DEF( OrMethod, 	NULL )
	FIS_FIELD_GETTER_DEF( ImpMethod,	NULL )
	FIS_FIELD_GETTER_DEF( AggMethod,	NULL )
	FIS_FIELD_GETTER_DEF( DefuzzMethod,	NULL )
	{ NULL, NULL, 0, NULL }
};

static PyTypeObject fisType = {
	PyObject_HEAD_INIT(NULL)
	0,                         /*ob_size*/
	"fis.FIS",                 /*tp_name*/
	sizeof( fisObject ),       /*tp_basicsize*/
	0,                         /*tp_itemsize*/
	(destructor)fis_dealloc,   /*tp_dealloc*/
	0,                         /*tp_print*/
	0,                         /*tp_getattr*/
	0,                         /*tp_setattr*/
	0,                         /*tp_compare*/
	0,                         /*tp_repr*/
	0,                         /*tp_as_number*/
	0,                         /*tp_as_sequence*/
	0,                         /*tp_as_mapping*/
	0,                         /*tp_hash */
	(ternaryfunc)fis_process,  /*tp_call*/
	0,                         /*tp_str*/
	0,                         /*tp_getattro*/
	0,                         /*tp_setattro*/
	0,                         /*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT,        /*tp_flags*/
	FIS_DOCSTRING,             /* tp_doc */
	0,                         /* tp_traverse */
	0,                         /* tp_clear */
	0,                         /* tp_richcompare */
	0,                         /* tp_weaklistoffset */
	0,                         /* tp_iter */
	0,                         /* tp_iternext */
	fisObject_Methods,         /* tp_methods */
	0,                         /* tp_members */
	0,                         /* tp_getset */
	0,                         /* tp_base */
	0,                         /* tp_dict */
	0,                         /* tp_descr_get */
	0,                         /* tp_descr_set */
	0,                         /* tp_dictoffset */
	0,                         /* tp_init */
	0,                         /* tp_alloc */
	(newfunc)fis_new,          /* tp_new */
};

/**
 *  Module initialization.
 */
PyMODINIT_FUNC initfis(void){
	PyObject* module;
	
	if( PyType_Ready( &fisType ) < 0 ){
		return;
	}
	
	pthread_mutex_init( &jumper_lock, NULL );
	
	module = Py_InitModule3( "fis", NULL, MOD_DOCSTRING );
	
	Py_INCREF( &fisType );
	PyModule_AddObject( module, "FIS", (PyObject *)&fisType );
}


/**
 *  Printf replacement function to be used by the functions in fis.c.
 *  Will raise a RuntimeError exception in the Python layer when called.
 *  Kinda ripped from <man sprintf>.
 */
void print_py( const char* format, ... ){
	va_list args;
	
	/* Guess we need no more than 100 bytes. */
	int written, size = 100;
	char *result;
	
	if ((result = malloc (size)) == NULL){
		PyErr_SetString( PyExc_MemoryError, "Out of memory." );
		return;
	}
	
	while (1) {
		/* Try to print in the allocated space. */
		va_start( args, format );
		written = vsnprintf( result, size, format, args );
		va_end( args );
		
		/* If that worked, return the string. */
		if( written > -1 && written < size ){
			PyErr_SetString( PyExc_RuntimeError, result );
			return;
		}
		
		/* Else try again with more space. */
		if( written > -1 )          /* glibc 2.1 */
			size = written+1;   /* precisely what is needed */
		else                        /* glibc 2.0 */
			size *= 2;          /* twice the old size */
		
		if ((result = realloc (result, size)) == NULL){
			PyErr_SetString( PyExc_MemoryError, "Out of memory." );
			return;
		}
	}
}
