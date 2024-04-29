# -*- coding: utf-8 -*-
#
# Demo-Implementierung von RSA.
# Zum Einsatz in der echten Welt nicht empfohlen. :)
#
# <http://de.wikipedia.org/wiki/RSA-Kryptosystem#Verfahren>

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
		d = int(d)
		
		janein = input( "e = %d, d = %d -- dieses Schlüsselpaar benutzen? [jN] " % ( e, d ) )
		
		if janein == 'j':
			pubkey, privkey = e, d
			break
else:
	raise ValueError("Exhausted all possible key pairs, you need to choose one")

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




