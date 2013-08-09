# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

def wrapdiff(curr, last):
    """ Calculate curr - last.

        If curr < last, try to guess the boundary at which the value must have wrapped
        by trying the maximum values of 64, 32 and 16 bit signed and unsigned ints.
    """
    if curr >= last:
        return curr - last

    boundary = None
    for chkbound in (64, 63, 32, 31, 16, 15):
        if last > 2**chkbound:
            break
        boundary = chkbound
    if boundary is None:
        raise ArithmeticError("Couldn't determine boundary")
    return 2**boundary - last + curr


class ValueDict(dict):
    """ Dictionary that simplifies handling check result values a bit by
        implementing math methods that run over all keys at once.

        Supported operations are + - * / ** __abs__ and __neg__.

        Each operation takes either a simple value or a dictionary as its
        argument, and calculates the result either with the constant or
        the corresponding key from the given dictionary.

        Note that - uses the wrapdiff() function from this module, it does
        *not* just use standard Python "-".

        Operations do not modify the dictionary in any way, but instead
        return a new ValueDict.
    """

    def __add__(self, other):
        """ self[key] + other[key] for key in self. """
        if not isinstance(other, dict):
            return ValueDict([(key, self[key] + other) for key in self ])
        return ValueDict([(key, self[key] + other[key]) for key in self ])

    def __sub__(self, other):
        """ wrapdiff(self[key], other[key]) for key in self. """
        if not isinstance(other, dict):
            return ValueDict([(key, wrapdiff(self[key], other)) for key in self ])
        return ValueDict([(key, wrapdiff(self[key], other[key])) for key in self ])

    def __mul__(self, other):
        """ self[key] * other[key] for key in self. """
        if not isinstance(other, dict):
            return ValueDict([(key, self[key] * other) for key in self ])
        return ValueDict([(key, self[key] * other[key]) for key in self ])

    def __div__(self, other):
        """ self[key] / other[key] for key in self. """
        if not isinstance(other, dict):
            return ValueDict([(key, self[key] / other) for key in self ])
        return ValueDict([(key, self[key] / other[key]) for key in self ])

    def __pow__(self, other):
        """ self[key] ** other[key] for key in self. """
        if not isinstance(other, dict):
            return ValueDict([(key, self[key] ** other) for key in self ])
        return ValueDict([(key, self[key] ** other[key]) for key in self ])

    def __neg__(self):
        """ -self[key] for key in self. """
        return ValueDict([(key, -self[key]) for key in self ])

    def __abs__(self):
        """ abs(self[key]) for key in self. """
        return ValueDict([(key, abs(self[key])) for key in self ])

