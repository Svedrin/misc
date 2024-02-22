# Fluxd #

This respository contains Fluxd, the data collector for [FluxMon](https://fluxmon.de), and a bunch of sensors.

### What's in it for me? ###

Once deployed on a host, Fluxd can be run either as a daemon or as a cron job set to run every 5 minutes.

When run for the first time, Fluxd will generate keys that you need to make known to Fluxmon using some magic mechanism that does not exist yet.

It will then detect everything it is able to get statistics on, update its configuration file (fluxd.conf in the working directory), check everything, and send updates to Fluxmon.

### Who do I talk to? ###

* If you'd like to get in touch, send me an [email](mailto:i.am@svedr.in) or talk to me (Svedrin) on the Freenode IRC network.
* I also regularly hang out at the Linux User Group or the [mag.lab](http://mag.lab.sh) in Fulda.
