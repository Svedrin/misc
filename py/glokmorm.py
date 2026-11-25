#!/usr/bin/env python3
"""Glokmorm-Generator: Unsinnsnamen aus Lautbausteinen.

Aufbau eines Namens:
  1. Silbe:        Anlaut + Vokal + Auslaut           (gl + o + k)
  weitere Silben:  Innen-Anlaut + Vokal + Auslaut     (m + o + rm)
  dazwischen:      ab und zu eine Füllsilbe           (klor + on + bumble)
  letzte Silbe:    evtl. -le-Endung statt Auslaut     (b + u + mble)

Beispiele:
  ./glokmorm.py                  # 10 Namen, mittlere Länge
  ./glokmorm.py -n 30 -l lang    # 30 lange Namen
  ./glokmorm.py -p gl --color    # nur Namen mit "gl", Bausteine farbig
  ./glokmorm.py --le 80 --fill 0 # viele -le-Endungen, keine Füllsilben
  ./glokmorm.py --dump > b.json  # Bausteine exportieren, bearbeiten ...
  ./glokmorm.py -b b.json        # ... und eigene Bausteine nutzen

Bausteine: leerzeichen-getrennt, "rm*3" = dreifache Häufigkeit.
"""
import argparse
import json
import random
import re
import sys

DEFAULTS = {
    "anf":   "gl*3 kl*3 fl*2 bl*2 gr*2 kr*2 sn*2 kn*2 sm sk sp pl fr br dr tr sh "
             "f*2 b*2 g*2 k*2 m*2 z w h d p t v j",
    "an":    "b*3 m*3 n g*2 k*2 d f p t z w gl kl bl sn kn gr pl sh",
    "vok":   "u*6 o*6 a*2 i*2 e oo ou",
    "aus":   "mp*2 nk*3 ng*2 rm*3 rk*2 rn rb rg lk lm lb mb nd ck*2 k*2 m*2 n*2 "
             "b g p t x sh ft st zz rp lp",
    "mitte": "on*3 um*2 om ob ag ig im un ar or",
    "ende":  "mble*3 ckle*3 nkle ggle mple ngle zzle ffle bble ddle",
}

# ANSI-Farben je Bausteintyp: Anlaut, Vokal, Auslaut, Füllsilbe, Endung
COLORS = {"o": "\033[41;97m", "v": "\033[46;30m", "c": "\033[44;97m",
          "m": "\033[43;30m", "e": "\033[45;97m"}
RESET = "\033[0m"


def parse(spec):
    """'gl*3 kl' -> ['gl', 'gl', 'gl', 'kl']"""
    out = []
    for tok in spec.split():
        m = re.fullmatch(r"([a-zäöüß]+)(?:\*(\d+))?", tok, re.I)
        if m:
            out += [m.group(1).lower()] * min(int(m.group(2) or 1), 20)
    return out


class Generator:
    def __init__(self, lists, length="mittel", le=35, fill=30, prefix="", rng=None):
        self.p = {}
        for k, default in DEFAULTS.items():
            self.p[k] = parse(lists.get(k, default)) or parse(default)
        self.length, self.le, self.fill = length, le, fill
        self.prefix = prefix.lower()
        self.rng = rng or random.Random()

    def _pick(self, key):
        return self.rng.choice(self.p[key])

    def make(self):
        r = self.rng
        n = {"kurz": 2, "mittel": r.randint(2, 3), "lang": r.randint(3, 4)}[self.length]
        parts = [(self._pick("anf"), "o"), (self._pick("vok"), "v"), (self._pick("aus"), "c")]
        for i in range(1, n):
            last = i == n - 1
            if not last and r.random() * 100 < self.fill:
                parts.append((self._pick("mitte"), "m"))
                continue
            parts += [(self._pick("an"), "o"), (self._pick("vok"), "v")]
            if last and r.random() * 100 < self.le:
                parts.append((self._pick("ende"), "e"))
            else:
                parts.append((self._pick("aus"), "c"))
        return parts

    def ok(self, w):
        if re.search(r"(.)\1\1", w):            # kein Dreifachbuchstabe
            return False
        if re.search(r"[^aeiouy]{5,}", w):      # max. 4 Konsonanten am Stück
            return False
        if re.search(r"[aeiou]{3,}", w):        # max. 2 Vokale am Stück
            return False
        if re.search(r"ck[kgc]|[kg]ck|xx|hh|jj|vv|ww", w):
            return False
        return len(w) <= (17 if self.length == "lang" else 13)

    def generate(self, tries=4000):
        for _ in range(tries):
            parts = self.make()
            w = "".join(p for p, _ in parts)
            if self.ok(w) and w.startswith(self.prefix):
                return parts
        return None


def main():
    ap = argparse.ArgumentParser(description="Unsinnsnamen wie 'glokmorm' generieren.",
                                 epilog=__doc__.split("Beispiele:")[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", "--anzahl", type=int, default=10, help="Anzahl Namen (Standard: 10)")
    ap.add_argument("-l", "--laenge", choices=["kurz", "mittel", "lang"], default="mittel")
    ap.add_argument("-p", "--prefix", default="", help="Namen müssen so beginnen, z. B. 'gl'")
    ap.add_argument("--le", type=int, default=35, metavar="PROZENT",
                    help="Anteil -le-Endungen (Standard: 35)")
    ap.add_argument("--fill", type=int, default=30, metavar="PROZENT",
                    help="Anteil Füllsilben (Standard: 30)")
    ap.add_argument("-b", "--bausteine", metavar="DATEI", help="JSON-Datei mit eigenen Bausteinen")
    ap.add_argument("--dump", action="store_true", help="Standard-Bausteine als JSON ausgeben")
    ap.add_argument("--color", action="store_true", help="Bausteine farbig anzeigen")
    ap.add_argument("--capitalize", action="store_true", help="ersten Buchstaben groß")
    ap.add_argument("--seed", type=int, help="Zufalls-Seed für reproduzierbare Ergebnisse")
    a = ap.parse_args()

    if a.dump:
        print(json.dumps(DEFAULTS, indent=2, ensure_ascii=False))
        return

    lists = {}
    if a.bausteine:
        with open(a.bausteine, encoding="utf-8") as f:
            lists = json.load(f)

    g = Generator(lists, a.laenge, a.le, a.fill, a.prefix, random.Random(a.seed))
    for _ in range(a.anzahl):
        parts = g.generate()
        if parts is None:
            sys.exit(f"Mit dem Anfang '{a.prefix}' klappt's nicht. Anderen probieren?")
        if a.capitalize:
            parts[0] = (parts[0][0].capitalize(), parts[0][1])
        if a.color:
            print("".join(f"{COLORS[t]}{p}{RESET}" for p, t in parts))
        else:
            print("".join(p for p, _ in parts))


if __name__ == "__main__":
    main()
