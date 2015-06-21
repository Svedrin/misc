<?php

// Script to be used by aastra and snom phones to display the callee's name for outgoing calls.
//
// Requires a contacts directory created by zsync. See also:
// https://bitbucket.org/Svedrin/misc/src/tip/py/zsync.py
//
// aastra URI: outgoing = http://hive.local.lan/getrpid.php?cid=$$REMOTENUMBER$$
// snom URI:   outgoing = http://hive.local.lan/getrpid.php?cid=$remote&

error_reporting(E_ALL);

$CONTACTS_JSON = "/var/lib/asterisk/.zsync/contacts.json";
$REDIAL_JSON   = "/var/lib/asterisk/.zsync/redial.json";

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
    global $CONTACTS_JSON;

    $contacts = json_decode(file_get_contents($CONTACTS_JSON), true);
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

function name_to_numbers($name){
    /* Keys on the phone:

         1      2       3
               abc     def

         4      5       6
        ghi    jkl     mno

         7      8       9
        pqrs   tuv    wxyz

    */
    $numberkeys = [
        "a" => "2", "ä" => "2", "b" => "2", "c" => "2",
        "d" => "3", "e" => "3", "f" => "3",
        "g" => "4", "h" => "4", "i" => "4",
        "j" => "5", "k" => "5", "l" => "5",
        "m" => "6", "n" => "6", "o" => "6", "ö" => "6",
        "p" => "7", "q" => "7", "r" => "7", "s" => "7", "ß" => "7",
        "t" => "8", "u" => "8", "ü" => "8", "v" => "8",
        "w" => "9", "x" => "9", "y" => "9", "z" => "9"
    ];
    $out = "";
    for($i = 0; $i < mb_strlen($name); $i++){
        $idx = mb_strtolower(mb_substr($name, $i, 1));
        if( isset($numberkeys[$idx]) )
            $out.= $numberkeys[$idx];
    }
    return $out;
}

$output = '<?xml version="1.0" encoding="UTF-8"?>';

if( !isset($_GET["action"]) )
    $_GET["action"] = "default";

switch($_GET["action"]){
    case 'exit':
        $output.= '<exit />';
        break;

    case 'redial':
        $redial = json_decode(file_get_contents($REDIAL_JSON), true);
        $output.= '<?xml-stylesheet version="1.0" href="SnomIPPhoneDirectory.xsl" type="text/xsl" ?>';
        $output.= '<SnomIPPhoneDirectory speedselect="select">';
        $output.= '  <Title>Redial</Title>';
        $output.= '  <Prompt>Dial</Prompt>';

        foreach($redial as $redialinfo){
            $dt = date("d.M H:i:s", $redialinfo["time"]);
            $output.= '  <DirectoryEntry>';
            $output.= "    <Name>{$redialinfo["text"]} ($dt)</Name>";
            $output.= "    <Telephone>{$redialinfo["number"]}</Telephone>";
            $output.= '  </DirectoryEntry>';
        }
        $output.= '</SnomIPPhoneDirectory>';
        break;

    case 'directory':
        $contacts = json_decode(file_get_contents($CONTACTS_JSON), true);

        if(!isset($_GET["number"])){
            $output.= '<SnomIPPhoneInput>';
            $output.= '    <Title>Directory</Title>';
            $output.= '    <Prompt>Search</Prompt>';
            $output.= '    <URL>http://'.$_SERVER["HTTP_HOST"].$_SERVER['SCRIPT_NAME'].'</URL>';
            $output.= '    <InputItem>';
            $output.= '        <DisplayName>Search for entry...</DisplayName>';
            $output.= '        <QueryStringParam>action=directory&amp;number</QueryStringParam>';
            $output.= '        <DefaultValue />';
            $output.= '        <InputFlags>n</InputFlags>';
            $output.= '    </InputItem>';
            $output.= '</SnomIPPhoneInput>';
            break;
        }


        $output.= '<?xml-stylesheet version="1.0" href="SnomIPPhoneDirectory.xsl" type="text/xsl" ?>';
        $output.= '<SnomIPPhoneDirectory speedselect="select">';
        $output.= '  <Title>Directory</Title>';
        $output.= '  <Prompt>Dial</Prompt>';

        foreach( $contacts as $contactinfo ){
            $known_numbers = [];
            foreach( ["cellular_telephone_number", "business2_telephone_number", "business_telephone_number", "home_telephone_number", "home2_telephone_number"] as $field ){
                if( isset($contactinfo["props"][$field]) && strlen($contactinfo["props"][$field])){
                    $number = unify_number($contactinfo["props"][$field]);

                    if( strlen($_GET["number"]) > 0 &&
                        strpos(name_to_numbers($contactinfo["props"]["fileas"]), $_GET["number"]) === FALSE &&
                        strpos($number, $_GET["number"]) === FALSE ){
                        continue;
                    }

                    if( in_array($number, $known_numbers) ){
                        continue;
                    }
                    $known_numbers[] = $number;


                    if( strpos($_SERVER["HTTP_USER_AGENT"], "snom300-SIP") !== FALSE ){
                        $splitname = explode(', ', $contactinfo["props"]["fileas"]);
                        $initial = substr($splitname[1], 0, 1);
                        $shortnum = substr($number, 3);
                        $contactname = "{$splitname[0]}, {$initial}. (0{$shortnum})";
                    }
                    else{
                        $contactname = "{$contactinfo["props"]["fileas"]} ({$number})";
                    }

                    $output.= '  <DirectoryEntry>';
                    $output.= '    <Name>'.$contactname.'</Name>';
                    $output.= '    <Telephone>'.str_replace('+', '00', $number).'</Telephone>';
                    $output.= '  </DirectoryEntry>';
                }
            }
        }
        $output.= '</SnomIPPhoneDirectory>';
        break;

    default:
        $callerid = htmlspecialchars(find_callerid($_GET["cid"]));

        $redial = json_decode(file_get_contents($REDIAL_JSON), true);
        if(count($redial) >= 50){
            array_pop($redial);
        }
        array_unshift($redial, [ "text" => $callerid, "number" => $_GET["cid"], "time" => time() ]);
        file_put_contents($REDIAL_JSON, json_encode($redial));

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
