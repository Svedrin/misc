import random

def mkname():
    hard = 'bdgkpqtx'
    soft = 'cfhjlmnrsvwyz'
    vows = 'aeiou'
    return ''.join([
        random.choice(hard),
        random.choice(soft),
        random.choice(vows),
        'k',
        random.choice(soft),
        random.choice(vows),
        random.choice(hard + soft),
        random.choice(soft),
    ])

if __name__ == '__main__':
    print(mkname())
