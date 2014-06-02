<?php

// Script to be used by aastra and snom phones to display the callee's name for outgoing calls.
//
// Requires a contacts directory created by zsync. See also:
// https://bitbucket.org/Svedrin/misc/src/tip/py/zsync.py
//
// aastra URI: outgoing = http://hive.local.lan/getrpid.php?phone=aastra&cid=$$REMOTENUMBER$$
// snom URI:   outgoing = http://hive.local.lan/getrpid.php?phone=snom&cid=$remote&

error_reporting(E_ALL);

function unify_number($number){
    if( strpos($number, "00") === 0 )
        return "+".substr($number, 2);
    if( strpos($number, "0") === 0 )
        return "+49".substr($number, 1);
    return $number;
}

function find_callerid($number){
    $contacts = json_decode(file_get_contents("/var/lib/asterisk/.zsync/contacts.json"), true);
    $target_number = unify_number($number);

    foreach( $contacts as $contactinfo ){
        foreach( ["cellular_telephone_number", "business2_telephone_number", "business_telephone_number", "home_telephone_number", "home2_telephone_number"] as $field ){
            if( isset($contactinfo["props"][$field]) && unify_number($contactinfo["props"][$field]) === $target_number ){
                return $contactinfo["props"]["fileas"];
            }
        }
    }

    return $number;
}

function format_aastra($callerid){
    $output = "<AastraIPPhoneFormattedTextScreen Timeout=\"5\">\n";
    $output.= "<Line>{$callerid}</Line>\n";
    $output.= "</AastraIPPhoneFormattedTextScreen>\n";
    return $output;
}

function format_snom($callerid){
    $output = "<SnomIPPhoneText>\n";
    $output.= "<Text>{$callerid}</Text>\n";
    $output.= "</SnomIPPhoneText>\n";
    return $output;
}

// error_log("Looking up callerid for {$_GET["cid"]}");
$callerid = htmlspecialchars(find_callerid($_GET["cid"]));

if( $_GET["phone"] == "aastra" ){
    $output = format_aastra($callerid);
}
else{
    $output = format_snom($callerid);
}

header("Content-Type: text/xml");
header("Content-Length: ".strlen($output));
echo $output;
