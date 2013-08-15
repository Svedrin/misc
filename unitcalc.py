#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;


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


if __name__ == '__main__':
    def calcnprint(inp):
        print "%-30s → %s" % (inp, calc_unit(inp))
    calcnprint("[sct/s] * [B/sct] / [IO/s]")
    calcnprint("IO/s * s/IO * %")
    calcnprint("B/s / [Pkt/s]")
    calcnprint("l/h / [100km/h]")
    calcnprint("B / [B/sct]")
    calcnprint("[[b] / [b/B]] / [B/sct]")
