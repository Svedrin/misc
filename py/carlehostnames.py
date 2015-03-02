import random

def mkname():
    cons = 'bcdfghjklmnpqrstvwxyz'
    vows = 'aeiou'
    return ''.join([
        random.choice(cons),
        random.choice(cons),
        random.choice(vows),
        'k',
        random.choice(cons),
        random.choice(vows),
        random.choice(cons),
        random.choice(cons),
    ])

if __name__ == '__main__':
    print mkname()
