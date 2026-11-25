# COMPOSE-DEPLOY(1)

## NAME

**compose-deploy** – deployt eine docker-compose-Config mit festen IP-Adressen in ein gemeinsames Docker-Netz

## ÜBERSICHT

```
compose-deploy [-p PROJEKT] [--project-dir DIR] [-n] [-y] [--pull] [DATEI | -]
```

## BESCHREIBUNG

`compose-deploy` nimmt eine ganz normale `docker-compose.yml` (zum Beispiel aus der
Doku eines Projekts) und passt sie an deine Umgebung an, bevor sie deployt wird:

- Alle Container landen in **einem** vorhandenen Docker-Netz (`DEPLOY_NETWORK`), jeder
  mit einer **festen IP-Adresse**.
- Die IPs werden in **10er-Blöcken** vergeben: Alle Container einer Applikation liegen
  nach Möglichkeit im selben Block, z. B. `.30`–`.39`. Jede neue Applikation bekommt
  einen eigenen, noch freien Block.
- Wird eine Applikation erneut deployt (Update, Config-Änderung), bekommen die
  Container **dieselben IPs** wie vorher.
- Der Hostname jedes Containers wird `<HOSTNAME>-<service>`, z. B. `docker01-db`.
- In Umgebungsvariablen kannst du `<IP:service>` schreiben. Das wird durch die IP
  ersetzt, die der Service bekommt.
- Portfreigaben (`ports:`) und alle Netzwerk-Angaben aus der Datei werden entfernt.
- Das Logging wird auf `max-size: 10m` und `max-file: 3` begrenzt.

Bevor etwas passiert, zeigt das Script eine Zusammenfassung und die fertige Config so,
wie `docker compose` sie sieht. Erst nach deiner Bestätigung wird deployt.

Das Script ändert deine Original-Datei **nie**. Es schreibt eine angepasste Kopie
(siehe [DATEIEN](#dateien)).

## VORAUSSETZUNGEN

- Linux-Host mit Docker und dem Compose-Plugin (`docker compose version` muss gehen)
- Python 3 mit PyYAML:
  ```bash
  apt install python3-yaml        # Debian/Ubuntu
  # oder: pip install pyyaml
  ```
- Ein **bereits angelegtes** Docker-Netz mit IPv4-Subnetz, typischerweise ein /24.
  Beispiel für ein macvlan-Netz direkt im LAN:
  ```bash
  docker network create -d macvlan \
    --subnet 192.168.50.0/24 --gateway 192.168.50.1 \
    -o parent=eth0 srv-net
  ```
  Ein normales Bridge-Netz geht genauso:
  ```bash
  docker network create --subnet 172.30.0.0/24 srv-net
  ```

## INSTALLATION

```bash
sudo install -m 755 compose-deploy.py /usr/local/bin/compose-deploy
```

Das Netz trägst du am besten fest in deine Shell-Config ein (`~/.bashrc`):

```bash
export DEPLOY_NETWORK=srv-net
export DEPLOY_HOSTNAME=docker01      # optional, siehe UMGEBUNGSVARIABLEN
```

## OPTIONEN

| Option | Bedeutung |
|---|---|
| `DATEI` | Pfad zur Compose-Datei. Fehlt er oder ist er `-`, liest das Script von der Standardeingabe: Config einfügen, mit **Strg-D** abschließen. |
| `-p`, `--project` *NAME* | Name der Applikation (Compose-Projektname). Fehlt er, nimmt das Script `name:` aus der Datei, dann `$COMPOSE_PROJECT_NAME`, dann den **Ordnernamen** der Datei. Beim Einfügen per Standardeingabe ist `-p` Pflicht (außer die Config enthält `name:`). |
| `--project-dir` *DIR* | Ordner, von dem aus relative Pfade (`./data`) und die `.env`-Datei gesucht werden. Standard: Ordner der Compose-Datei, beim Einfügen der aktuelle Ordner. |
| `-n`, `--dry-run` | Nur anzeigen, nichts deployen. |
| `-y`, `--yes` | Ohne Rückfrage deployen. |
| `--pull` | Images vor dem Start neu herunterladen (`--pull always`). Wichtig für Updates bei Tags wie `latest` oder `31-apache`. |
| `-h`, `--help` | Kurzhilfe. |

## UMGEBUNGSVARIABLEN

| Variable | Pflicht | Bedeutung |
|---|---|---|
| `DEPLOY_NETWORK` | ja | Name des Docker-Netzes, in das deployt wird. |
| `DEPLOY_HOSTNAME` | nein | Präfix für die Container-Hostnamen. Fehlt sie, nimmt das Script `$HOSTNAME` und sonst den Systemnamen (nur der Teil vor dem ersten Punkt). Hinweis: Bash exportiert `$HOSTNAME` oft nicht. Setz `DEPLOY_HOSTNAME`, wenn du sicher sein willst. |
| `DEPLOY_BLOCK_SIZE` | nein | Größe der IP-Blöcke, Standard `10`. |
| `DEPLOY_STATE_DIR` | nein | Ablageort der generierten Dateien, Standard `~/.local/state/compose-deploy`. |
| `COMPOSE_PROJECT_NAME` | nein | Wird als Projektname genommen, wenn weder `-p` noch `name:` gesetzt sind. |

## WAS MIT DER CONFIG PASSIERT

Für jeden Service:

| Angabe in der Original-Datei | Ergebnis |
|---|---|
| `ports:` | entfernt |
| `networks:`, `network_mode:` | entfernt, ersetzt durch `DEPLOY_NETWORK` mit fester `ipv4_address` |
| `hostname:` | überschrieben mit `<DEPLOY_HOSTNAME>-<service>` |
| `environment:` | `<IP:name>` wird durch die IP des Services `name` ersetzt (Listen- und Map-Schreibweise) |
| `logging:` | Driver `json-file` (Standard) oder `local`: `max-size: 10m`, `max-file: 3` werden gesetzt bzw. überschrieben. Andere Driver bleiben unverändert (Warnung). |
| `deploy.replicas` / `scale` > 1 | Abbruch, weil feste IPs dann nicht gehen |
| alles andere (`image`, `volumes`, `command`, `depends_on`, `container_name` …) | bleibt unverändert |

Außerdem: Das Netzwerk wird als `external` eingetragen (das Script legt es nicht an
und löscht es nie), die veraltete Angabe `version:` fällt weg, und `name:` wird auf den
Projektnamen gesetzt.

`${VARIABLE}`-Platzhalter bleiben in der generierten Datei stehen. Docker Compose
ersetzt sie beim Deploy aus der `.env`-Datei im Projektordner bzw. aus deiner Shell.

## IP-VERGABE

Beispiel mit Netz `192.168.50.0/24` und Blockgröße 10:

| Block | Adressen | Verwendung |
|---|---|---|
| 0 | .0 – .9 | **nie vergeben** (Gateway usw.) |
| 1 | .10 – .19 | erste Applikation |
| 2 | .20 – .29 | zweite Applikation |
| … | … | … |
| 25 | .250 – .254 | letzter (kleiner) Block |

Ablauf bei jedem Aufruf:

1. Das Script liest **alle** Container auf dem Host, auch gestoppte, und notiert, welche
   IPs im Netz belegt sind.
2. Für jeden Service sucht es einen **vorhandenen Container**: gleiches Compose-Projekt
   und gleicher Service-Name, oder gleicher `container_name`. Findet es einen, wird
   dessen IP wiederverwendet. Status: `ersetzt`.
3. Neue Services (Status `neu`) bekommen, in der Reihenfolge der Datei:
   1. freie IPs in dem Block, den die Applikation schon belegt;
   2. sonst den ersten **komplett freien** Block. Bei mehr als 10 Services werden mehrere
      freie Blöcke direkt hintereinander genommen;
   3. sonst irgendeine freie IP (mit Warnung).

Daraus folgt: **Der Projektname ist der Schlüssel.** Deployst du dieselbe Applikation
unter einem anderen Namen, gilt sie als neu und bekommt neue IPs.

## DATEIEN

`~/.local/state/compose-deploy/<projekt>/docker-compose.yml`
: Die generierte, angepasste Compose-Datei. Sie wird bei jedem Aufruf neu geschrieben.
  Mit ihr kannst du die Applikation auch direkt mit `docker compose` bedienen (siehe
  [Schritt 4](#4-betrieb-status-logs-shell)).

`<projektordner>/.env`
: Wird von Docker Compose gelesen. Hier gehören Passwörter hin.

---

## BEISPIEL: LIFECYCLE EINER NEXTCLOUD

Durchgespielt wird eine Nextcloud mit MariaDB und Redis, von der Installation über ein
Update bis zum Löschen. Annahmen: Netz `srv-net` mit `192.168.50.0/24`, Host heißt
`docker01`. Die Image-Versionen sind Beispiele, nimm die jeweils aktuellen.

### 1. Vorbereitung

Leg pro Applikation einen eigenen Ordner an. Der **Ordnername wird zum Projektnamen**:

```bash
mkdir -p ~/apps/nextcloud
cd ~/apps/nextcloud
```

Passwörter kommen in eine `.env` im selben Ordner:

```bash
cat > .env <<'EOF'
MYSQL_ROOT_PASSWORD=bitte-aendern-root
MYSQL_PASSWORD=bitte-aendern-nc
EOF
chmod 600 .env
```

Dann die `docker-compose.yml`. Beachte die `<IP:…>`-Platzhalter: Du musst die IPs
nicht kennen, das Script setzt sie ein.

```yaml
services:
  db:
    image: mariadb:11.4
    command: --transaction-isolation=READ-COMMITTED
    restart: unless-stopped
    volumes:
      - db:/var/lib/mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: nextcloud
      MYSQL_USER: nextcloud
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  app:
    image: nextcloud:31-apache
    restart: unless-stopped
    depends_on: [db, redis]
    ports:
      - "8080:80"            # wird vom Script entfernt, stört aber nicht
    volumes:
      - ./data:/var/www/html
    environment:
      MYSQL_HOST: "<IP:db>"
      MYSQL_DATABASE: nextcloud
      MYSQL_USER: nextcloud
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      REDIS_HOST: "<IP:redis>"
      NEXTCLOUD_TRUSTED_DOMAINS: "<IP:app> cloud.example.com"

volumes:
  db:
```

### 2. Erstes Deployment

Erst einmal nur anschauen:

```bash
compose-deploy docker-compose.yml -n
```

Ausgabe (gekürzt):

```
=== Projekt 'nextcloud' → Netz 'srv-net' (192.168.50.0/24) ===

SERVICE  IP               HOSTNAME         STATUS
db       192.168.50.30    docker01-db      neu
redis    192.168.50.31    docker01-redis   neu
app      192.168.50.32    docker01-app     neu

--- docker compose config (~/.local/state/compose-deploy/nextcloud/docker-compose.yml) ---
name: nextcloud
services:
  app:
    environment:
      MYSQL_HOST: 192.168.50.30
      REDIS_HOST: 192.168.50.31
      NEXTCLOUD_TRUSTED_DOMAINS: 192.168.50.32 cloud.example.com
      ...
```

Hier ist `.10`–`.29` schon von anderen Applikationen belegt, also bekommt die Nextcloud
den nächsten freien Block `.30`–`.39`.

> **Achtung:** Die `docker compose config`-Ausgabe zeigt die Werte aus der `.env`
> **im Klartext**, also auch die Passwörter. Pass beim Screensharing auf.

Sieht alles gut aus? Dann wirklich deployen:

```bash
compose-deploy docker-compose.yml
# ... gleiche Zusammenfassung ...
So deployen? [j/N] j
```

Danach ist die Nextcloud unter `http://192.168.50.32` erreichbar (bzw. über deinen
Reverse-Proxy, der auf diese IP zeigt). Beim ersten Aufruf legst du den Admin-Account an.

Die Container heißen nach Compose-Schema `nextcloud-db-1`, `nextcloud-redis-1` und
`nextcloud-app-1`.

### 3. Prüfen

```bash
docker ps --filter label=com.docker.compose.project=nextcloud
docker inspect -f '{{.Config.Hostname}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' nextcloud-app-1
```

### 4. Betrieb: Status, Logs, Shell

Für alles außer Deploy kannst du `docker compose` direkt mit der generierten Datei
nutzen. Das ist lang, also eine Shell-Funktion in die `~/.bashrc`:

```bash
cdc() {   # cdc <projekt> <compose-befehl...>
  local p="$1"; shift
  docker compose -p "$p" \
    -f ~/.local/state/compose-deploy/"$p"/docker-compose.yml \
    --project-directory ~/apps/"$p" "$@"
}
```

> **Wichtig:** `--project-directory` muss auf den **Original-Ordner** zeigen. Sonst
> findet Compose die `.env` nicht, die Passwörter sind leer, und relative Pfade wie
> `./data` zeigen ins Leere.

Damit:

```bash
cdc nextcloud ps
cdc nextcloud logs -f app
cdc nextcloud restart app
cdc nextcloud exec -u www-data app php occ status
cdc nextcloud stop          # alles anhalten (IPs bleiben reserviert)
cdc nextcloud start
```

Gestoppte Container behalten ihre IP-Zuordnung. Das Script vergibt sie nicht an
andere Applikationen.

### 5. Update der Nextcloud

**a) Backup.** Vor jedem Update:

```bash
cdc nextcloud exec -u www-data app php occ maintenance:mode --on
cdc nextcloud exec db sh -c 'mariadb-dump -u root -p"$MYSQL_ROOT_PASSWORD" nextcloud' > ~/backup/nc-$(date +%F).sql
tar czf ~/backup/nc-data-$(date +%F).tgz -C ~/apps/nextcloud data
cdc nextcloud exec -u www-data app php occ maintenance:mode --off
```

**b) Neue Version eintragen.** In `~/apps/nextcloud/docker-compose.yml`:

```yaml
    image: nextcloud:32-apache      # vorher 31-apache
```

> Nextcloud lässt sich nur **eine Hauptversion pro Schritt** aktualisieren (31 → 32 →
> 33). Mehrere Versionen überspringen geht nicht.

**c) Erneut deployen**, mit `--pull`, damit die neuen Images geladen werden:

```bash
cd ~/apps/nextcloud
compose-deploy docker-compose.yml --pull
```

```
SERVICE  IP               HOSTNAME         STATUS
db       192.168.50.30    docker01-db      ersetzt (nextcloud-db-1, running)
redis    192.168.50.31    docker01-redis   ersetzt (nextcloud-redis-1, running)
app      192.168.50.32    docker01-app     ersetzt (nextcloud-app-1, running)
```

Alle Container behalten ihre IPs. Das Script erstellt **alle** Container der Applikation
neu (`--force-recreate`), auch DB und Redis. Die Daten bleiben erhalten, weil sie in
Volumes liegen. Die Nextcloud führt ihr internes Upgrade beim Start selbst aus.
Verfolgen kannst du das mit:

```bash
cdc nextcloud logs -f app
```

**Gleiche Version, nur neues Image** (z. B. Sicherheitsupdate bei gleichem Tag): Datei
nicht ändern, einfach `compose-deploy docker-compose.yml --pull`.

**Nur einen einzelnen Service neu starten**, ohne die anderen anzufassen:

```bash
cdc nextcloud pull app
cdc nextcloud up -d app
```

Das funktioniert, solange du die `docker-compose.yml` seit dem letzten
`compose-deploy` nicht verändert hast. Sonst erst `compose-deploy` laufen lassen.

### 6. Config ändern, Service hinzufügen oder entfernen

- **Config ändern** (Umgebungsvariable, Volume …): Datei bearbeiten,
  `compose-deploy docker-compose.yml`. Alles behält seine IP.
- **Service hinzufügen**, z. B. einen `cron`-Container: In der Datei ergänzen und neu
  deployen. Der neue Service bekommt die nächste freie IP im Block, hier `.33`.
- **Service entfernen**: Wenn du ihn aus der Datei löschst, lässt `compose-deploy` den
  alten Container **stehen** (er belegt weiter seine IP). Weg bekommst du ihn so:
  ```bash
  cdc nextcloud up -d --remove-orphans
  ```

### 7. Alles wieder aufräumen

**a) Container und Compose-Ressourcen entfernen:**

```bash
cdc nextcloud down --remove-orphans
```

Danach sind die Container weg und ihre IPs (`.30`–`.39`) wieder frei. Das Netz
`srv-net` bleibt bestehen, da es als `external` eingetragen ist.

**b) Daten löschen** (unwiderruflich, vorher sicher sein!):

```bash
docker volume ls --filter label=com.docker.compose.project=nextcloud   # anschauen
cdc nextcloud down -v                                                  # benannte Volumes (hier: db) löschen
sudo rm -rf ~/apps/nextcloud/data                                      # Bind-Mount-Daten
```

`down -v` und `rm -rf` lassen sich auch in einem Schritt mit a) erledigen. Es gibt
keine Rückfrage.

**c) Images entfernen** (optional):

```bash
cdc nextcloud down --rmi all
```

**d) Reste löschen:**

```bash
rm -rf ~/.local/state/compose-deploy/nextcloud
rm -rf ~/apps/nextcloud
```

Reihenfolge beachten: Erst `cdc … down`, dann die Dateien löschen, denn `cdc` braucht
die generierte Datei.

Prüfen, dass nichts übrig ist:

```bash
docker ps -a --filter label=com.docker.compose.project=nextcloud
docker volume ls --filter label=com.docker.compose.project=nextcloud
```

---

## FEHLERBEHEBUNG

**`DEPLOY_NETWORK ist nicht gesetzt`**
: `export DEPLOY_NETWORK=srv-net` setzen.

**`Netzwerk '…' nicht gefunden`**
: Netz mit `docker network create …` anlegen (siehe [VORAUSSETZUNGEN](#voraussetzungen)).

**`Bei Paste/stdin bitte Projektnamen mit -p angeben`**
: Beim Einfügen gibt es keinen Ordnernamen. `-p name` mitgeben.

**`<IP:x> – Service 'x' gibt es nicht`**
: Tippfehler im Platzhalter. `x` muss exakt ein Service-Name aus derselben Datei sein.

**Warnung `<IP:...> außerhalb von environment wird nicht ersetzt`**
: Platzhalter funktionieren nur unter `environment:`, nicht in `labels:`, `command:` oder
  in `.env`/`env_file`-Dateien.

**Warnung `Projekt-Block … reicht nicht – weiche zusätzlich auf Block … aus`**
: Der 10er-Block der Applikation ist voll. Die neuen Services liegen in einem anderen
  Block. Funktioniert, ist aber weniger übersichtlich.

**`docker compose config schlägt fehl`**
: Die Config ist ungültig. Die Fehlermeldung kommt direkt von Docker Compose. Oft
  fehlt eine Variable in der `.env` oder ein relativer Pfad stimmt nicht (`--project-dir`
  prüfen).

**`Dieser Container … werden vorher entfernt`** in der Zusammenfassung
: Es gibt bereits einen Container mit demselben `container_name`, der nicht zu diesem
  Compose-Projekt gehört (z. B. per `docker run` angelegt). Er wird nach deiner
  Bestätigung mit `docker rm -f` gelöscht und neu erstellt, mit seiner bisherigen IP.

**Applikation hat plötzlich andere IPs**
: Du hast sie unter einem anderen Projektnamen deployt (anderer Ordnername, anderes
  `-p` oder anderes `name:`). Mit dem alten Namen erneut deployen, und die Container mit
  dem falschen Namen per `docker compose -p falscher-name … down` entfernen.

**Host erreicht die Container nicht (macvlan)**
: Bei macvlan kann der Docker-Host selbst die Container-IPs nicht erreichen. Andere
  Rechner im LAN schon. Das ist eine Eigenschaft von macvlan, kein Fehler des Scripts.

## EINSCHRÄNKUNGEN

- Nur IPv4.
- Keine `replicas`/`scale` > 1.
- Container von Services, die aus der Datei entfernt wurden, bleiben stehen (siehe
  [Schritt 6](#6-config-ändern-service-hinzufügen-oder-entfernen)).
- Ein Deploy erstellt immer **alle** Container der Applikation neu.
- Das Script hat keinen eigenen Befehl zum Entfernen. Dafür gibt es
  `docker compose … down` (siehe [Schritt 7](#7-alles-wieder-aufräumen)).

## RÜCKGABEWERT

| Wert | Bedeutung |
|---|---|
| `0` | Erfolgreich deployt, Dry-Run beendet oder bei der Rückfrage abgebrochen |
| `1` | Fehler vor dem Deploy (Netz fehlt, ungültige Config, keine freien IPs …) |
| sonst | Rückgabewert von `docker compose up` |
