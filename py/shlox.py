# -*- coding: utf-8 -*-

""" Re-Implementation of Python's shlex.split(), because shlex can't cope
    with the input being Unicode.

    Copyright (C) 2009, Michael "Svedrin" Ziegler <diese-addy@funzt-halt.net>
"""

def shlox( line, escape='\\', comment='#', sep=(' ', '\t', '\r', '\n' ) ):
    ST_NORMAL, ST_ESCAPE, ST_SINGLE_QUOTED, ST_DOUBLE_QUOTED, ST_DOUBLE_ESCAPE = range(5)

    state = ST_NORMAL

    word  = ''
    empty = True

    for char in line:
        if   state == ST_NORMAL:
            if   char == escape:
                state = ST_ESCAPE
            elif char == '"':
                empty = False
                state = ST_DOUBLE_QUOTED
            elif char == "'":
                empty = False
                state = ST_SINGLE_QUOTED
            elif char == comment:
                if empty:
                    raise StopIteration
                else:
                    word += char
            elif char in sep:
                if not empty:
                    yield word
                    empty = True
                    word  = ''
            else:
                empty = False
                word += char

        elif state == ST_ESCAPE:
            word += char
            state = ST_NORMAL

        elif state == ST_SINGLE_QUOTED:
            if   char == "'":
                state = ST_NORMAL
            else:
                word += char

        elif state == ST_DOUBLE_QUOTED:
            if   char == escape:
                state = ST_DOUBLE_ESCAPE
            elif char == '"':
                state = ST_NORMAL
            else:
                word += char

        elif state == ST_DOUBLE_ESCAPE:
            if   char in ( escape, comment, '"', "'" ) + sep:
                word += char
            else:
                word += '\\' + char
            state = ST_DOUBLE_QUOTED

    if state != ST_NORMAL:
        raise ValueError( "Unclosed quote or \\ at end of line." )

    elif not empty:
        yield word
