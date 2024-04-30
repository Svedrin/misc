# -*- coding: utf-8 -*-
#
# Demo-Implementierung von RSA.
# Zum Einsatz in der echten Welt nicht empfohlen. :)
#
# <http://de.wikipedia.org/wiki/RSA-Kryptosystem#Verfahren>

print("Wir brauchen zwei Primzahlen p und q. 13 und 89 funktionieren beispielsweise.")
print("Primzahlen bis 100: 2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97.")
print()

p = int( input( "p: " ) )
q = int( input( "q: " ) )

n     = p * q
phi_n = (p - 1) * (q - 1)

print("RSA-Modul: N = %d - φ(N) = %d" % ( n, phi_n ))

print("Suche mögliche Schlüsselpaare:")


keypairs = []

for e in range( 1, (phi_n + 1), 2 ):
    d = (phi_n + 1.0)/e
    if d == int(d):
        # konvertiere float nach int. Wichtig weil float in der Größe der Zahlen
        # limitiert ist, int in Python aber nicht. Wenn wir die Zahlen als float
        # belassen würden, führt dies zu Overflows bei den Potenzierungen.
        d = int(d)

        janein = input( "e = %d, d = %d -- dieses Schlüsselpaar benutzen? [jN] " % ( e, d ) )

        if janein == 'j':
            pubkey, privkey = e, d
            break
else:
    raise ValueError("Alle Möglichkeiten erschöpft")

print()
print("Öffentlicher Schlüssel = (%d,%d)" % ( pubkey,  n ))
print("Geheimer Schlüssel     = (%d,%d)" % ( privkey, n ))
print()

while(True):
    msg = input( "Nachricht:     " )
    if not msg:
        break

    ciph = [ ((ord(char) ** pubkey) % n) for char in msg ]

    print("Verschlüsselt:", ciph)

    deciph = ""
    for char in ciph:
        deciph += chr((char ** privkey) % n)

    print("Entschlüsselt:", deciph)
    print()
    print()




