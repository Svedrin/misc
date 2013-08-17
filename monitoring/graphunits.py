# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

# make "/" operator always use floats
from __future__ import division

import tokenize

from StringIO import StringIO

from graphbuilder import Symbol, Infix, Literal, Parser, LiteralNode, Source

# SYNTAX ELEMENTS

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

    def get_value(self, rrd):
        value = self.value.get_value(rrd)
        if not isinstance(value, LiteralNode):
            return value
        unit  = self.unit.get_value(self.parser.unitfac)
        return LiteralWithUnitNode(value, unit)


class RightBracket(Symbol):
    pass


class UnitLiteral(Symbol):
    def get_value(self, rrd):
        return self.parser.unitfac.get_source(self.value)

# GRAPH SEMANTICS

class LiteralWithUnitNode(LiteralNode):
    def __init__(self, value, unit):
        LiteralNode.__init__(self, value)
        self._unit  = unit
        self.unit   = unicode(unit)
        self._label = "%s [%s]" % (value.label, self.unit)

    varname    = property( lambda self: self._value.varname )

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

    def __mul__(self, other):
        return self._unit_mult(other, '*')

    def __div__(self, other):
        return self._unit_mult(other, '/')

    __truediv__ = __div__

    def __unicode__(self):
        return '/'.join(['*'.join(self.upper)] + self.lower)

class UnitFactory(object):
    def get_source(self, name):
        return Unit([name], [])


# PARSER

class UnitAwareParser(Parser):
    def __init__(self, token_gen):
        Parser.__init__(self, token_gen)
        self.symbol_table.update({
            '[': LeftBracket,
            ']': RightBracket,
            '%': UnitLiteral,
        })
        self.unitfac = UnitFactory()


def parse(source):
    src = StringIO(source).readline
    src = tokenize.generate_tokens(src)
    parser = UnitAwareParser(src)
    while True:
        yield parser.expression()


