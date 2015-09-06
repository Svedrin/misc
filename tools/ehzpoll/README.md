EHZpoll
=======

Utility using libSML to query a German electricity meter, formally called
"Elektronischer Haushaltszähler" (EHZ).

To build, git clone https://github.com/dailab/libsml.git, put the files
into the examples/ dir, and run make. This should produce an ehzpoll binary
which can then be used by the FluxMon ehz sensor to provide readings.
