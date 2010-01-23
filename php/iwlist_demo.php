<?php

include( 'iwlist-parser.class.php' );

$p = new iwlist_parser();

print_r( $p->parseScanAll() );

