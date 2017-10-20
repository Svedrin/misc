# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

""" Copy-on-Write (COW) Dictionary """


class CowDict(object):
    """ Copy-on-Write (COW) Dictionary """

    def __init__(self, data):
        self.data = data

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, item, value):
        new_data = self.data.copy()
        new_data[item] = value
        self.data = new_data

    def __len__(self):
        return len(self.data)

    def __contains__(self, item):
        return item in self.data

    def __str__(self):
        return str(self.data)

    def clear(self):
        self.data = {}

    def copy(self):
        """ Return a new CowDict with an actual copy of our data.
            (This kinda defeats the purpose of this class. Use clone instead.)
        """
        return CowDict(self.data.copy())

    def clone(self):
        """ Return a new CowDict that copies data only when written to. """
        return CowDict(self.data)

    def items(self):
        return self.data.items()

    def iteritems(self):
        return self.data.iteritems()

    def iterkeys(self):
        return self.data.iterkeys()

    def itervalues(self):
        return self.data.itervalues()

    def keys(self):
        return self.data.keys()

    def pop(self, *args):
        new_data = self.data.copy()
        value = new_data.pop(*args)
        self.data = new_data
        return value

    def popitem(self):
        new_data = self.data.copy()
        value = new_data.popitem()
        self.data = new_data
        return value

    def setdefault(self, item, default=None):
        new_data = self.data.copy()
        value = new_data.setdefault(item, default)
        self.data = new_data
        return value

    def update(self, update_dict):
        new_data = self.data.copy()
        new_data.update(update_dict)
        self.data = new_data
        return self

    def values(self):
        return self.data.values()

    def viewitems(self):
        return self.data.viewitems()

    def viewkeys(self):
        return self.data.viewkeys()

    def viewvalues(self):
        return self.data.viewvalues()




if __name__ == '__main__':
    # Some calculation functions.
    # Note that those do *not* return a *new* dict, but they instead *update* the one they get.

    def calc_min_max(inputdata):
        return inputdata.update({
            "min": min(inputdata["data"]),
            "max": max(inputdata["data"]),
        })

    def calc_sum_len(inputdata):
        return inputdata.update({
            "sum": sum(inputdata["data"]),
            "len": len(inputdata["data"]),
        })

    def calc_avg(inputdata):
        inputdata["avg"] = inputdata["sum"] / float(inputdata["len"])
        return inputdata


    # Now do some calculations.
    maths = CowDict({
        "data": range(10)
    })

    print "Orig:          ", maths
    print

    # Passing a .clone() to each of the calculations ensures that none of them
    # will modify the original "maths" dict.
    # While reading, nothing is copied; only when the calculcation tries to
    # *modify* the dict, a copy is created.

    print "Min/Max:       ", calc_min_max(maths.clone())
    print
    print "Orig:          ", maths
    print
    sum_len = calc_sum_len(maths.clone())
    print "Sum/Len:       ", sum_len
    print
    print "Orig:          ", maths
    print
    print "Avg:           ", calc_avg(sum_len.clone())
    print "Sum/Len:       ", sum_len
    print

    # Now let's see what happens when we forget to .clone().
    # Spoiler: avg will leak into sum_len, because we're not creating a new CowDict.
    #          instead, calc_avg() *updates* the one it gets.
    # The point of CowDict is *not* that this doesn't ever happen (then it would
    # be an ImmutableDict), but that clones are cheap, so you can have LOTS of them.

    print "Avg w/o clone: ", calc_avg(sum_len)
    print "Sum/Len:       ", sum_len
    print
    print "Orig:          ", maths
