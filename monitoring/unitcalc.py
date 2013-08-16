#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import re

def calc_unit(inp):
    """ Calculate the unit in which a calculation will result.

        The input is a string such as "sct/s * B/sct / [IO/s]", which
        corresponds to a formula that multiplies a value in "sectors per second"
        with one in "Bytes per sector" and divides by one in "IOs per second".
        The result will be in "Bytes per IO", so this function will return
        "B / IO".
    """

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

    def process_units(_inp):
        """ Parse an iterator that yields a unit expression. """
        upper = []
        lower = []

        currop   = "*"
        currunit = ""

        for char in _inp:
            if char == " ":
                # ignore whitespace
                continue

            if char not in ("[", "*", "/", "]"):
                # everything that's not an operator must be part of a unit
                currunit += char
                continue

            # we found an operator, so the last unit has been completely parsed.
            # if it's the [ operator, currunit is empty and we will get the actual unit by
            # parsing the following sub-expression and multiplying/dividing by its result.
            # if char isn't the [ operator and currunit is a valid unit, multiply/divide by
            # it. (currunit will be empty both before *and* after an [] operation.)
            if char == "[":
                # parse a sub-expression
                subupper, sublower = process_units(_inp)
                # multiply its upper part with our units
                for subunit in subupper:
                    unit_mult(upper, lower, currop, subunit)
                # multiply its lower part with our inverse
                for subunit in sublower:
                    unit_mult(lower, upper, currop, subunit)

            elif currunit:
                # plain unit
                unit_mult(upper, lower, currop, currunit)
                currunit = ""

            if char == "]":
                # we reached the end of the current expression
                break

            # apparently we just found a * or / operator, switch currop.
            currop = char

        return upper, lower

    upper, lower = process_units(iter(inp + "]"))
    return ' / '.join([' * '.join(upper)] + lower)


def sub_units(inp, units):
    """ Parse a formula, substituting variable names with their respective units and
        stripping out numbers.

        The result can be passed to calc_unit in order to get the resulting unit.
    """

    def process_str(_inp):
        currvar = ""
        out = ""
        in_unit = False
        for char in _inp:
            if char == ' ':
                continue

            if char == '[':
                in_unit = True

            if in_unit:
                # keep units in [] as they are
                out += char

            elif 'a' <= char.lower() <= 'z' or char == '_':
                # a-z_ denotes a variable name
                currvar += char

            else:
                # anything else means we have read a complete variable name. check if
                # that is the case (we might have just returned from a ] as well), and if
                # so, replace the variable with its unit
                if currvar:
                    out += "[%s]" % units[currvar]
                    currvar = ""
                # keep operators
                if char in ('+', '-', '*', '/', '(', ')'):
                    out += char

            if char == ']':
                in_unit = False

        return out

    return process_str(iter(inp + "\n"))


if __name__ == '__main__':
    def calcnprint(inp):
        print "%-30s → %s" % (inp, calc_unit(inp))
    calcnprint("[sct/s] * [B/sct] / [IO/s]")
    calcnprint("IO/s * s/IO * %")
    calcnprint("B/s / [Pkt/s]")
    calcnprint("l/h / [100km/h]")
    calcnprint("B / [B/sct]")
    calcnprint("[[b] / [b/B]] / [B/sct]")


    units = {
        "wr_sectors": "sct/s",
        "wr_ios": "IO/s"
    }
    inp = "wr_sectors * 512[B/sct] / wr_ios * 4096[B/IO] * 100[%]"
    calcnprint(sub_units(inp, units))

    print re.sub("\[[\w/*+%-]+\]", "", inp)

