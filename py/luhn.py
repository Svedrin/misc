# See https://en.wikipedia.org/wiki/Luhn_algorithm

def luhn_sign(number):
    """ Return the number with a check digit attached. """
    res = 0
    for idx, num in enumerate(reversed(str(number))):
        num = int(num)
        if idx % 2 == 0:
            num *= 2
        if num > 9:
            num -= 9
        res += num
    return str(number) + str(10 - (res % 10))


def luhn_verify(number):
    """ Verfiy a Luhn-signed number. """
    number = str(number)
    check_digit = number[-1]
    signed = luhn_sign(number[:-1])
    return signed[-1] == check_digit


if __name__ == '__main__':
    assert luhn_sign("629925") == '6299259'
    assert luhn_verify("6299259")

    assert luhn_verify('65607053')
    assert luhn_verify('51499812')
    assert luhn_verify('40283996')
    assert luhn_verify('11955283')
    assert luhn_verify('45501392')
    assert luhn_verify('78441359')
    assert luhn_verify('80840952')
    assert luhn_verify('12208948')
    assert luhn_verify('43500818')

    assert not luhn_verify('65607057')
    assert not luhn_verify('51599812')
    assert not luhn_verify('48382996')
    assert not luhn_verify('21925583')
    assert not luhn_verify('4501392')
    assert not luhn_verify('784441359')
    assert not luhn_verify('80840953')
    assert not luhn_verify('1220898')
    assert not luhn_verify('435000818')
