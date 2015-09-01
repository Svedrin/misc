for rrdfile in *.rrd; do
	LANG=C rrdtool tune $rrdfile --alpha 0.0035 --beta 0.01 --gamma 0.0035 --failure-threshold 6 --window-length 12
done
