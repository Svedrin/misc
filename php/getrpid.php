<?php

// Script to be used by aastra and snom phones to display the callee's name for outgoing calls;
// to implement a searchable Phone directory, and to implement a central redial list.
//
// Reads contacts from Nextcloud.
//
// Can also be used from Asterisk's Dial plan to set CALLERID(name), like so (AEL syntax):
//
//   Set(ENV(ASTERISK_CALLERID_NUM)=${CALLERID(num)});
//   Set(CALLERID(name)=${SHELL(php7.0 /somewhere/getrpid.php)});
//
// Phone settings:
//
// aastra URI: outgoing = http://hive.local.lan/getrpid.php?cid=$$REMOTENUMBER$$
// snom URI:   outgoing = http://hive.local.lan/getrpid.php?cid=$remote&

error_reporting(E_ALL);

define("NEXTCLOUD_DB", "/var/lib/nextcloud/owncloud.db");
define("REDIAL_JSON",  "/var/lib/asterisk/redial.json");


/**
 * Convert a phone number to international format and strip out separators.
 */
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


/**
 * Translate a name (string) to the numbers one would type on the keypad of a
 * desk phone to enter that name. (i.e. hello = 43556.)
 */
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

/**
 * Compare two phone book entries for sorting.
 * Order: last name, first name, number.
 */
function cmp_entries($a, $b){
    $a_nameparts = explode(" ", $a["name"], 2);
    $b_nameparts = explode(" ", $b["name"], 2);
    $result = 0;
    if( isset($a_nameparts[1]) && isset($b_nameparts[1]) ){
        $result = strcmp($a_nameparts[1], $b_nameparts[1]);
    }
    if( $result === 0 ) {
        $result = strcmp($a_nameparts[0], $b_nameparts[0]);
    }
    if( $result === 0 ) {
        $result = strcmp($a["number"], $b["number"]);
    }
    return $result;
}

/**
 * Find phone book entries matching a given name or number.
 */
function find_entries_matching($search){
    $nextcloud_db = new SQLite3(NEXTCLOUD_DB, SQLITE3_OPEN_READONLY);

    // CREATE TABLE oc_cards (
    //     id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    //     carddata BLOB DEFAULT NULL,
    //     uri VARCHAR(255) DEFAULT NULL COLLATE BINARY,
    //     lastmodified BIGINT UNSIGNED DEFAULT NULL,
    //     etag VARCHAR(32) DEFAULT NULL COLLATE BINARY,
    //     size BIGINT UNSIGNED NOT NULL,
    //     addressbookid BIGINT DEFAULT 0 NOT NULL
    // );
    $result = $nextcloud_db->query("SELECT carddata from oc_cards");

    $entries = [];
    while($record = $result->fetchArray(SQLITE3_ASSOC)){
        $entry_lines = explode("\n", $record["carddata"]);
        $contact_name    = "";
        $contact_numbers = [];
        // VCard data is in KEY:Value\n format
        // We're interested in "FN" and ("TEL" or "TEL;*") keys
        // FN   -> $contact_name
        // TEL* -> $contact_numbers
        foreach( $entry_lines as $line ){
            $key_value = explode(":", $line, 2);
            if( $key_value[0] === "FN" ){
                if( strlen($key_value[1]) > 0 )
                    $contact_name = trim($key_value[1]);
            }
            else if( $key_value[0] === "TEL" || strpos($key_value[0], "TEL;") === 0 ){
                if( strlen($key_value[1]) > 0 ){
                    $new_number = unify_number(trim($key_value[1]));
                    if( !in_array($new_number, $contact_numbers) ){
                        $contact_numbers[] = $new_number;
                    }
                }
            }
        }

        // Fetch all contacts (that match) into an array of [name => "John", number => 1234] entries.
        // If a person has multiple phone numbers, they appear multiple times in $entries.
        foreach( $contact_numbers as $number ){
            // If we're searching for something and this entry does *not* match, skip it
            if( strlen($search) > 0 &&
                strpos($contact_name, $search) === FALSE &&
                strpos(name_to_numbers($contact_name), $search) === FALSE &&
                strpos($number, $search) === FALSE &&
                strpos($number, unify_number($search)) === FALSE ){
                continue;
            }

            $entries[] = [
                'name'   => $contact_name,
                'number' => $number
            ];
        }
    }
    uasort($entries, "cmp_entries");
    return $entries;
}

/**
 * Look up a phone number in our directory and try to turn it into a "Name (Number)" string.
 */
function find_callerid($number){
    $number = unify_number($number);
    foreach( find_entries_matching($number) as $entry ){
        return "{$entry["name"]} ({$entry["number"]})";
    }

    return $number;
}


/**
 * Check if we're being called from Asterisk itself. If so, only print the callerid to stdout.
 */
if( getenv("ASTERISK_CALLERID_NUM") ){
    die(find_callerid(getenv("ASTERISK_CALLERID_NUM")));
}


/**
 * Assume we're in web mode, and talking to a desk phone.
 */
$output = '<?xml version="1.0" encoding="UTF-8"?>';

if( !isset($_GET["action"]) )
    $_GET["action"] = "default";

switch($_GET["action"]){
    case 'exit':
        // Make the phone exit a menu we previously displayed.
        $output.= '<exit />';
        break;

    case 'redial':
        // User has hit the "redial" button. Read Redial entries and format them as Snom XML
        // to be displayed by the phone.
        $redial = json_decode(file_get_contents(REDIAL_JSON), true);
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
        // User has hit the "directory" button. Display a "Search for:" prompt where they can
        // enter a search term.
        if(!isset($_GET["number"])){
            $output.= '<SnomIPPhoneInput>';
            $output.= '    <Title>Directory</Title>';
            $output.= '    <Prompt>Search</Prompt>';
            $output.= '    <URL>http://'.$_SERVER["HTTP_HOST"].$_SERVER['SCRIPT_NAME'].'</URL>';
            $output.= '    <InputItem>';
            $output.= '        <DisplayName>Search for:</DisplayName>';
            $output.= '        <QueryStringParam>action=directory&amp;number</QueryStringParam>';
            $output.= '        <DefaultValue />';
            $output.= '        <InputFlags>n</InputFlags>';
            $output.= '    </InputItem>';
            $output.= '</SnomIPPhoneInput>';
            break;
        }

        // User has entered a search term. Present entries from our phone book that match.
        $entries = [];
        foreach( find_entries_matching($_GET["number"]) as $entry ){
            if( strpos($_SERVER["HTTP_USER_AGENT"], "snom300-SIP") !== FALSE ){
                // The snom300 phone has a way smaller display, let's not overwhelm it
                $splitname = explode(', ', $entry["name"]);
                $initial = substr($splitname[1], 0, 1);
                $shortnum = substr($entry['number'], 3);
                $entry_contact_name = "{$splitname[0]}, {$initial}. (0{$shortnum})";
            }
            else{
                $entry_contact_name = "{$entry["name"]} ({$entry['number']})";
            }

            array_push($entries,
                '  <DirectoryEntry>'.
                '    <Name>'.$entry_contact_name.'</Name>'.
                '    <Telephone>'.str_replace('+', '00', $entry['number']).'</Telephone>'.
                '  </DirectoryEntry>'
            );
        }
        $output.= '<?xml-stylesheet version="1.0" href="SnomIPPhoneDirectory.xsl" type="text/xsl" ?>';
        $output.= '<SnomIPPhoneDirectory speedselect="select">';
        $output.= '  <Title>Found '.count($entries).' Entries</Title>';
        $output.= '  <Prompt>Dial</Prompt>';
        $output.= implode('', $entries);
        $output.= '</SnomIPPhoneDirectory>';
        break;

    default:
        // User is placing a new call. Save it into the redial list for later use, and send back a
        // "-> This Person (number)" popup to confirm they're actually calling the right person.
        $callerid = htmlspecialchars(find_callerid($_GET["cid"]));

        $redial = json_decode(file_get_contents(REDIAL_JSON), true);
        if(count($redial) >= 50){
            array_pop($redial);
        }
        array_unshift($redial, [ "text" => $callerid, "number" => $_GET["cid"], "time" => time() ]);
        file_put_contents(REDIAL_JSON, json_encode($redial));

        if( strpos($_SERVER["HTTP_USER_AGENT"], "snom300-SIP") !== FALSE ){
            if( mb_strlen($callerid) > 14 && strpos($callerid, ',') !== FALSE ){
                $callerid = implode(",<br/>", explode(', ', $callerid));
            }
        }

        $output.= "<SnomIPPhoneText>";
        $output.=   "<Text>-&gt; {$callerid}</Text>";
        $output.=   '<fetch mil="5000">http://'.$_SERVER["HTTP_HOST"].$_SERVER['SCRIPT_NAME'].'?action=exit</fetch>';
        $output.= "</SnomIPPhoneText>";

        break;
}


header("Content-Type: text/xml");
header("Content-Length: ".strlen($output));
echo $output;

// kate: space-indent on; indent-width 4; replace-tabs on;
