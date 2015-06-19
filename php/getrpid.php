<?php

// Script to be used by aastra and snom phones to display the callee's name for outgoing calls.
//
// Requires a contacts directory created by zsync. See also:
// https://bitbucket.org/Svedrin/misc/src/tip/py/zsync.py
//
// aastra URI: outgoing = http://hive.local.lan/getrpid.php?cid=$$REMOTENUMBER$$
// snom URI:   outgoing = http://hive.local.lan/getrpid.php?cid=$remote&

error_reporting(E_ALL);

function unify_number($number){
    $number = str_replace([" ", "-"], "", $number); // Android likes to put those in
    if( strpos($number, "00") === 0 )
        return "+".substr($number, 2);
    if( strpos($number, "0") === 0 )
        return "+49".substr($number, 1);
    if( strpos($number, "+") === 0 ){
        return $number;
    }
    return "+496659".$number;
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

$output = '<?xml version="1.0" encoding="UTF-8"?>';

switch($_GET["action"]){
    case 'exit':
        $output.= '<exit />';
        break;

    case 'directory':
        $contacts = json_decode(file_get_contents("/var/lib/asterisk/.zsync/contacts.json"), true);

        $output.= '<SnomIPPhoneDirectory speedselect="select">';
        $output.= '  <Title>Directory</Title>';
        $output.= '  <Prompt>Dial</Prompt>';

        foreach( $contacts as $contactinfo ){
            foreach( ["cellular_telephone_number", "business2_telephone_number", "business_telephone_number", "home_telephone_number", "home2_telephone_number"] as $field ){
                if( isset($contactinfo["props"][$field])){
                    $number = unify_number($contactinfo["props"][$field]);
                    $shortnum = substr($number, 3, 5);

                    if( strpos($_SERVER["HTTP_USER_AGENT"], "snom300-SIP") !== FALSE ){
                        $splitname = explode(', ', $contactinfo["props"]["fileas"]);
                        $initial = substr($splitname[1], 0, 1);
                        $contactname = "{$splitname[0]}, {$initial}. (0{$shortnum}…)";
                    }
                    else{
                        $contactname = "{$contactinfo["props"]["fileas"]} ({$number})";
                    }

                    $output.= '  <DirectoryEntry>';
                    $output.= '    <Name>'.$contactname.'</Name>';
                    $output.= '    <Telephone>'.$number.'</Telephone>';
                    $output.= '  </DirectoryEntry>';
                }
            }
        }
        $output.= '</SnomIPPhoneDirectory>';
        break;

    default:
        $callerid = htmlspecialchars(find_callerid($_GET["cid"]));

        if( strpos($_SERVER["HTTP_USER_AGENT"], "snom300-SIP") !== FALSE ){
            if( mb_strlen($callerid) > 14 && strpos($callerid, ',') !== FALSE ){
                $callerid = implode(",<br/>", explode(', ', $callerid));
            }
        }

        $output.= "<SnomIPPhoneText>";
        $output.= "<Text>{$callerid}</Text>";
        $output.= '<fetch mil="5000">http://'.$_SERVER["HTTP_HOST"].$_SERVER['SCRIPT_NAME'].'?action=exit</fetch>';
        $output.= "</SnomIPPhoneText>";
        break;
}


header("Content-Type: text/xml");
header("Content-Length: ".strlen($output));
echo $output;

// kate: space-indent on; indent-width 4; replace-tabs on;
