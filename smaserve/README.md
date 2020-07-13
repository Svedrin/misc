# Building

You'll need SBFspot: https://github.com/SBFspot/SBFspot/

```
git clone git@github.com:SBFspot/SBFspot.git sbfspot
cd sbfspot/SBFspot
make nosql
mkdir -p /usr/local/share/smaserve
cp nosql/bin/SBFspot /usr/local/share/smaserve/SBFspot
```

# Config

You need to have [`SBFspot.cfg`](https://github.com/SBFspot/SBFspot/blob/master/SBFspot/SBFspot.cfg) and the Taglists available.

If you use the original `SBFspot.cfg` from their repo, be sure to disable Bluetooth (unless you want to use it). The config from my
repo has it disabled already.

Also, from within the [`SBFspot` subdir of the original repo](https://github.com/SBFspot/SBFspot/tree/master/SBFspot),
`cp TagList*.txt /usr/local/share/smaserve/`.

# Run it

If `run_test.sh` produces some output that looks legit:

```
cp smaserve.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable smaserve
systemctl start smaserve
```

Test using: `curl http://0.0.0.0:9500/metrics`

If it works, add it to Prometheus and you're golden \o/
