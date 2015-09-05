# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

# make "/" operator always use floats
from __future__ import division

import tokenize

from StringIO import StringIO

# SYNTAX ELEMENTS

class Symbol(object):
    lbp = 0
    rbp = 0

    def __init__(self, parser, id_, value):
        # Set defaults for left/right binding power
        self.parser = parser
        self.id = id_
        self.value = value

    def nud(self):
        """ Null Denotation """
        return self

    def led(self, left):
        """ Left Denotation """
        return self

    def get_value(self, args, null=False):
        raise NotImplementedError("get_value")

class Name(Symbol):
    def get_value(self, args, null=False):
        args.append(self.value)
        # http://timothychenallen.blogspot.de/2006/03/sql-calculating-geometric-mean-geomean.html
        # sucks when the data is <= 0
        #return "(exp(avg(ln(cm.value)) filter (where sv.name = %s)))"
        if null:
            return "(avg(CASE WHEN cm.value = 0 THEN NULL ELSE cm.value END) filter (where sv.name = %s))"
        return "(avg(cm.value) filter (where sv.name = %s))"

    def get_unit(self, namespace):
        return namespace.get_unit(self.value)

class EndMarker(Symbol):
    pass

class Literal(Symbol):
    def get_value(self, args, null=False):
        args.append(self.value)
        return "%s"

    def get_unit(self, namespace):
        return namespace.get_unit(self.value)

class Infix(Symbol):
    def led(self, left):
        self.first = left
        self.second = self.parser.expression(self.rbp)
        return self

class Prefix(Symbol):
    lbp =  0
    rbp = 70

    def nud(self):
        self.first = self.parser.expression(self.rbp)
        return self

class OpPlus(Infix):
    lbp = 50
    rbp = 50

    def get_value(self, args, null=False):
        return "(%s + %s)" % (self.first.get_value(args), self.second.get_value(args))

    def get_unit(self, namespace):
        return self.first.get_unit(namespace) + self.second.get_unit(namespace)

class OpMinus(Infix):
    lbp = 50
    rbp = 50

    def nud(self):
        self.first = self.parser.expression(Prefix.rbp)
        self.second = None
        return self

    def get_value(self, args, null=False):
        if self.second is None:
            return "(- %s)" % (self.first.get_value(args))
        return "(%s - %s)" % (self.first.get_value(args), self.second.get_value(args))

    def get_unit(self, namespace):
        return self.first.get_unit(namespace) - self.second.get_unit(namespace)

class OpMult(Infix):
    lbp = 60
    rbp = 60

    def get_value(self, args, null=False):
        return "(%s * %s)" % (self.first.get_value(args), self.second.get_value(args))

    def get_unit(self, namespace):
        return self.first.get_unit(namespace) * self.second.get_unit(namespace)

class OpDiv(Infix):
    lbp = 60
    rbp = 60

    def get_value(self, args, null=False):
        return "(%s / %s)" % (self.first.get_value(args), self.second.get_value(args, null=True))

    def get_unit(self, namespace):
        return self.first.get_unit(namespace) / self.second.get_unit(namespace)

class LeftParen(Prefix):
    def nud(self):
        exp = self.parser.expression(0)
        if self.parser.token.id != ')':
            raise ValueError("Missing )")
        self.parser.advance() # skip the )
        return exp

class RightParen(Symbol):
    pass


class LeftBracket(Infix):
    lbp = 65
    rbp = 65

    def led(self, left):
        self.value = left
        self.unit  = self.parser.expression(0)
        if self.parser.token.id != ']':
            raise ValueError("Missing ]")
        self.parser.advance() # skip the ]
        return self

    def get_value(self, args, null=False):
        return self.value.get_value(args, null)

    def get_unit(self, namespace):
        return self.unit.get_unit(LiteralNamespace())

class RightBracket(Symbol):
    pass


class LiteralNamespace(object):
    def get_unit(self, name):
        return Unit([name], [])

class SensorNamespace(object):
    def __init__(self, sensor):
        self.sensor = sensor

    def get_unit(self, name):
        unitstr = self.sensor.sensorvariable_set.get(name=name).unit
        return list(parse(unitstr))[0].get_unit(LiteralNamespace())

# UNIT SEMANTICS

def unit_mult(upper, lower, currop, currunit):
    """ `upper' and `lower' are lists of the units above and below the fraction line.

        Multiply or divide this fraction by the `currunit', depending on the value
        of `currop'. Before adding a unit to one of the lists, check if it cancels
        out with one on the other.
    """
    if currop == "*":
        if currunit in lower:
            lower.remove(currunit)
        else:
            upper.append(currunit)
    elif currop == "/":
        if currunit in upper:
            upper.remove(currunit)
        else:
            lower.append(currunit)
    else:
        raise ArithmeticError(currop)

class Unit(object):
    def __init__(self, upper, lower):
        self.upper = upper
        self.lower = lower

    def _unit_mult(self, other, currop):
        # create a new Unit instance with its own copies of upper/lower
        res = Unit(self.upper + [], self.lower + [])
        # multiply its upper part with our units
        for subunit in other.upper:
            unit_mult(res.upper, res.lower, currop, subunit)
        # multiply its lower part with our inverse
        for subunit in other.lower:
            unit_mult(res.lower, res.upper, currop, subunit)
        return res

    def __eq__(self, other):
        def _listcmp(lft, rgt):
            lftcopy = lft + []
            try:
                for r in rgt:
                    lftcopy.remove(r)
            except ValueError:
                return False # rgt has elements that lft doesn't have
            if lftcopy:
                return False # lft has elements that rgt doesn't have
            return True      # lists have the same elements
        return _listcmp(self.upper, other.upper) and _listcmp(self.lower, other.lower)

    def __add__(self, other):
        if self == other:
            return self
        raise TypeError("Cannot add units that are not equivalent")

    def __sub__(self, other):
        if self == other:
            return self
        raise TypeError("Cannot substract units that are not equivalent")

    def __neg__(self):
        return self

    def __mul__(self, other):
        return self._unit_mult(other, '*')

    def __div__(self, other):
        return self._unit_mult(other, '/')

    __truediv__ = __div__

    def __unicode__(self):
        return '/'.join(['*'.join(self.upper)] + self.lower)

    __str__ = __unicode__


# PARSER

class Parser(object):
    # http://effbot.org/zone/simple-iterator-parser.htm
    # http://javascript.crockford.com/tdop/tdop.html
    # http://effbot.org/zone/simple-top-down-parsing.htm

    def __init__(self, token_gen):
        self.symbol_table = {
            '(literal)': Literal,
            '(name)':    Name,
            '(end)':     EndMarker,
            '+':         OpPlus,
            '-':         OpMinus,
            '*':         OpMult,
            '/':         OpDiv,
            '(':         LeftParen,
            ')':         RightParen,
            '[':         LeftBracket,
            ']':         RightBracket,
            '%':         Literal,
            }
        self.token = None
        self.token_gen = token_gen
        self.advance()

    def advance(self):
        tokentype, tokenvalue, _, _, _ = self.token_gen.next()
        if tokentype == tokenize.NAME:
            # get variable or something
            symbol = '(name)'
        elif tokentype == tokenize.OP:
            if tokenvalue not in self.symbol_table:
                raise ValueError("Operator '%s' is not defined." % tokenvalue)
            symbol = tokenvalue
        elif tokentype == tokenize.NUMBER:
            try:
                tokenvalue = int(tokenvalue, 0)
            except ValueError:
                tokenvalue = float(tokenvalue)
            symbol = '(literal)'
        elif tokentype == tokenize.ENDMARKER:
            symbol = '(end)'
        else:
            raise ValueError("Unexpected token.")
        SymClass = self.symbol_table[symbol]
        #print "Making a %s(%s, %s)." % (SymClass.__name__, symbol, tokenvalue)
        self.token = SymClass(self, symbol, tokenvalue)
        return self.token

    def expression(self, rbp=0):
        t = self.token
        self.advance()
        left = t.nud()
        while rbp < self.token.lbp:
            t = self.token
            self.advance()
            left = t.led(left)
        return left

def parse(source):
    src = StringIO(source).readline
    src = tokenize.generate_tokens(src)
    parser = Parser(src)
    while True:
        yield parser.expression()


