# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

class Colors:
    gray    = 30
    red     = 31
    green   = 32
    yellow  = 33
    blue    = 34
    magenta = 35
    cyan    = 36
    white   = 37
    crimson = 38

    class Highlighted:
        red     = 41
        green   = 42
        brown   = 43
        blue    = 44
        magenta = 45
        cyan    = 46
        gray    = 47
        crimson = 48

def colorprint(color, text):
    print "\033[1;%dm%s\033[1;m" % (color, text)

