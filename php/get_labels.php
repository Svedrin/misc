<?php
/*  --------------------------------------------------------------
    Gambio shipping module for DHL Intraship that requests one
    label for each item ordered. Useful if you mostly ship very
    large and/or heavy items that need to be packaged individually.

    Requires https://github.com/myokyawhtun/PDFMerger to be installed
    in your shop's catalog directory.

    Known limitations:
      * Germany is hardcoded in a coupl'a places, so sending to/from
        another country is currently not supported.

    Installation:
      * Copy this file to <your shop>/admin/get_labels.php
      * alter table admin_access add get_labels boolean not null default true;
      * Create <your shop>/user_classes/conf/AdminMenu/menu_getlabels.xml
        with the following content:

        <?xml version="1.0"?>
        <admin_menu>
            <menugroup id="BOX_HEADING_CUSTOMERS">
                <menuitem sort="15" link="get_labels.php" title="Labeldruck" />
            </menugroup>
        </admin_menu>

      * Log out and log in to your shop again to refresh the menu.
      * You should now see "Labeldruck" appear in the customers
        section of the adminmenu.

    Copyright (c) 2016 Michael Ziegler <i.am@svedr.in>
    Copyright (c) 2011 Gambio GmbH

    Released under the GNU General Public License (Version 2)
    [http://www.gnu.org/licenses/gpl-2.0.html]
    --------------------------------------------------------------*/

require ('includes/application_top.php');

include(DIR_WS_MODULES.FILENAME_SECURITY_CHECK);

require(DIR_FS_CATALOG . "PDFMerger/PDFMerger.php");

if( !isset($_GET["action"]) || $_GET["action"] == "" || $_GET["action"] == "list" ){

    $orders_query =
        "SELECT ".
            "o.orders_id, o.orders_status, ".
            "o.customers_firstname, o.customers_lastname, o.customers_street_address, o.customers_postcode, o.customers_city, ".
            "o.delivery_firstname,  o.delivery_lastname,  o.delivery_street_address,  o.delivery_postcode,  o.delivery_city,  o.delivery_company, o.delivery_suburb, ".
            "s.orders_status_name, sum(op.products_quantity) as products_count ".
        "FROM ".TABLE_ORDERS." o ".
        "INNER JOIN ".TABLE_ORDERS_STATUS." s ON (o.orders_status = s.orders_status_id) ".
        "INNER JOIN orders_products op ON (o.orders_id = op.orders_id) ".
        "WHERE ".
            "s.language_id = '".$_SESSION['languages_id']."' AND ".
            "o.orders_status NOT IN (3, 99) ".
        "GROUP BY o.orders_id ".
        "ORDER BY o.date_purchased DESC";

    error_log($orders_query);
    $orders_result = xtc_db_query($orders_query);

    $orders = array();

    while( $db_order = xtc_db_fetch_array($orders_result) ){
        $orders[] = $db_order;
    }

?><!doctype html public "-//W3C//DTD HTML 4.01 Transitional//EN">
<html <?php echo HTML_PARAMS; ?>>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=<?php echo $_SESSION['language_charset']; ?>">
        <title><?php echo TITLE; ?></title>
        <link rel="stylesheet" type="text/css" href="<?php echo DIR_WS_ADMIN; ?>includes/stylesheet.css">
    </head>
    <body topmargin="0" leftmargin="0" bgcolor="#FFFFFF">
        <?php require(DIR_WS_INCLUDES . 'header.php'); ?>
        <table border="0" cellspacing="2" cellpadding="2">
            <tr>
                <td class="columnLeft2" width="<?php echo BOX_WIDTH; ?>" valign="top" height="100%">
                    <table border="0" width="<?php echo BOX_WIDTH; ?>" cellspacing="1" cellpadding="1" class="columnLeft">
                        <?php require(DIR_WS_INCLUDES . 'column_left.php'); ?>
                    </table>
                </td>
                <td class="boxCenter" width="100%" valign="top" height="100%">
                    <table width="100%" cellspacing="0" cellpadding="2">
                        <tr class="dataTableHeadingRow">
                            <td class="dataTableHeadingContent">Nr</td>
                            <td class="dataTableHeadingContent">Kunde</td>
                            <td class="dataTableHeadingContent">Lieferadresse</td>
                            <td class="dataTableHeadingContent">Status</td>
                            <td class="dataTableHeadingContent">Pakete</td>
                            <td class="dataTableHeadingContent">&nbsp;</td>
                        </tr>
                        <?php foreach($orders as $order): ?>
                            <tr class="dataTableRow">
                                <td class="dataTableContent"><?=$order["orders_id"]?></td>
                                <td class="dataTableContent">
                                    <?=$order["customers_firstname"]?> <?=$order["customers_lastname"]?><br />
                                    <?=$order["customers_street_address"]?><br />
                                    <?=$order["customers_postcode"]?> <?=$order["customers_city"]?>
                                </td>
                                <td class="dataTableContent">
                                    <?=$order["delivery_company"]?> <?=$order["delivery_suburb"]?><br />
                                    <?=$order["delivery_firstname"]?> <?=$order["delivery_lastname"]?><br />
                                    <?=$order["delivery_street_address"]?><br />
                                    <?=$order["delivery_postcode"]?> <?=$order["delivery_city"]?>
                                </td>
                                <td class="dataTableContent"><?=$order["orders_status_name"]?></td>
                                <td class="dataTableContent"><?=(int)$order["products_count"]?></td>
                                <td class="dataTableContent">
                                    <div align="center">
                                        <a class="button" href="<?=$_SERVER["REQUEST_URI"]?>?action=labels&amp;order=<?=$order["orders_id"]?>" target="_blank">DHL-Labels </a>
                                    </div>
                                </td>
                            </tr>
                        <?php endforeach ?>
                    </table>
                </td>
            </tr>
        </table>
        <?php require(DIR_WS_INCLUDES . 'footer.php'); ?>
    </body>
</html>
<?php
    require(DIR_WS_INCLUDES . 'application_bottom.php');

}
else if( $_GET["action"] == "labels" ){

    function get_with_curl($url){
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        $data = curl_exec($ch);
        curl_close($ch);
        return $data;
    }


    function createShipment( $order_details, $customer_details ){
        $WSDL_URL           = 'https://cig.dhl.de/cig-wsdls/com/dpdhl/wsdl/geschaeftskundenversand-api/1.0/geschaeftskundenversand-api-1.0.wsdl';
        $DHL_SANDBOX_URL    = 'https://cig.dhl.de/services/sandbox/soap';
        $DHL_PRODUCTION_URL = 'https://cig.dhl.de/services/production/soap';

        $gmintraship = new GMIntraship();

        $credentials = array(
//             'wsdl_url'      => $gmintraship->getWSDLLocation(),       // returns bullshit for some reason
//             'endpoint_url'  => $gmintraship->getWebserviceEndpoint(),
            'wsdl_url'      => $WSDL_URL,
            'endpoint_url'  => ( $gmintraship->debug ? $DHL_SANDBOX_URL       : $DHL_PRODUCTION_URL                ),
            'user'          => ( $gmintraship->debug ? 'geschaeftskunden_api' : $gmintraship->user                 ),
            'signature'     => ( $gmintraship->debug ? 'Dhl_ep_test1'         : $gmintraship->password             ),
            'ekp'           => ( $gmintraship->debug ? '5000000000'           : $gmintraship->ekp                  ),
            'partner_id'    => ( $gmintraship->debug ? '01'                   : $gmintraship->getPartnerID("DE")   ),
            'product_code'  => ( $gmintraship->debug ? 'EPN'                  : $gmintraship->getProductCode("DE") ),
            'api_user'      => GMIntraship::APPID,
            'api_password'  => GMIntraship::APPToken
        );

        // your company info
        $sender_details = array(
            'company_name'    => $gmintraship->shipper_name,
            'contact_person'  => $gmintraship->shipper_contact,
            'street_name'     => $gmintraship->shipper_street,
            'street_number'   => $gmintraship->shipper_house,
            'zip'             => $gmintraship->shipper_postcode,
            'city'            => $gmintraship->shipper_city,
            'country'         => 'Germany',
            'email'           => $gmintraship->shipper_email,
            'phone'           => $gmintraship->shipper_phone,
            'internet'        => HTTP_SERVER
        );

        $header = new SoapHeader( 'http://dhl.de/webservice/cisbase', 'Authentification', array(
            'user'      => $credentials['user'],
            'signature' => $credentials['signature'],
            'type'      => 0
        ) );

        $client = new SoapClient( $credentials['wsdl_url'], array(
            'login'    => $credentials['api_user'],
            'password' => $credentials['api_password'],
            'location' => $credentials['endpoint_url'],
            'trace'    => 1,
            'encoding' => 'ISO-8859-1',
            "stream_context" => stream_context_create(
                array(
                    'ssl' => array(
                        'verify_peer'       => false,
                        'verify_peer_name'  => false,
                    )
                )
            )
        ) );

        $client->__setSoapHeaders( $header );


        $shipment = array(
            "Version" => array(
                'majorRelease' => '1',
                'minorRelease' => '0'
            ),
            'ShipmentOrder' => array(
                'SequenceNumber' => '1',
                "Shipment" => array(
                    "ShipmentDetails" => array(
                        "ProductCode" => $credentials["product_code"],
                        "ShipmentDate" => date( 'Y-m-d' ),
                        "EKP"          => $credentials['ekp'],
                        "Attendance"   => array(
                            "partnerID" => $credentials["partner_id"]
                        ),
                        "ShipmentItem" => array(
                            "WeightInKG" => "25",
                            "PackageType" => "PK"
//                             "LengthInCM" => "80",
//                             "WidthInCM"  => "40",
//                             "HeightInCM" => "20",
//                             "PackageType" => "PL"
                        ),
                        "CustomerReference" => $order_details["orders_id"],
                        "Notification" => array(
                            "RecipientName"         => "{$customer_details["first_name"]} {$customer_details["last_name"]}",
                            "RecipientEmailAddress" => $customer_details["email"]
                        )
                    ),
                    "Shipper" => array(
                        "Company" => array(
                            "Company" => array(
                                "name1" => $sender_details['company_name']
                            )
                        ),
                        "Address" => array(
                            "streetName"   => $sender_details['street_name'],
                            "streetNumber" => $sender_details['street_number'],
                            "Zip"          => array( "germany" => $sender_details['zip'] ),
                            "city"         => $sender_details["city"],
                            "Origin"       => array( 'countryISOCode' => 'DE' )
                        ),
                        "Communication" => array(
                            "email"         => $sender_details["email"],
                            "phone"         => $sender_details["phone"],
                            "internet"      => $sender_details["internet"],
                            "contactPerson" => $sender_details["contact_person"]
                        )
                    ),
                    "Receiver" => array(
                        "Company" => array(
                            "Company" => array(
                                "name1"     => ( !empty($customer_details['company_name'])
                                    ? $customer_details['company_name']
                                    : "{$customer_details["first_name"]} {$customer_details["last_name"]}" )
                            ),
                        ),
                        "Address" => array(
                            "streetName"   => $customer_details['street_name'],
                            "streetNumber" => $customer_details['street_number'],
                            "Zip"          => array( "germany" => $customer_details['zip'] ),
                            "city"         => $customer_details["city"],
                            "Origin"       => array( 'countryISOCode' => 'DE' )
                        ),
                        "Communication" => array(
                            "email" => $customer_details["email"],
                            "contactPerson" => "{$customer_details["first_name"]} {$customer_details["last_name"]}"
                        )
                    )
                )
            )
        );

        $response = $client->CreateShipmentDD( $shipment );

        if( is_soap_fault( $response ) ){
            return array(
                "success"  => false,
                "client"   => $client,
                "shipment" => $shipment,
                "error"    => $response->faultstring
            );

        }
        else if( $response->status->StatusCode != 0 ){
            return array(
                "success"  => false,
                "client"   => $client,
                "shipment" => $shipment,
                "error"    => $response->status->StatusMessage
            );
        }
        else {
            return array(
                "success"         => true,
                "shipment"        => $shipment,
                'shipment_number' => (String) $response->CreationState->ShipmentNumber->shipmentNumber,
                'piece_number'    => (String) $response->CreationState->PieceInformation->PieceNumber->licensePlate,
                'label_url'       => (String) $response->CreationState->Labelurl
            );
        }

    }


    if(!isset($_GET["order"]) || empty($_GET["order"]) || !is_numeric($_GET["order"])){
        die("order param needs to be a number");
    }

    $order_id = $_GET["order"];

    $orders_query =
        "SELECT ".
            "o.orders_id, o.orders_status, o.customers_email_address, ".
            "o.customers_firstname, o.customers_lastname, o.customers_street_address, o.customers_postcode, o.customers_city, ".
            "o.delivery_firstname,  o.delivery_lastname,  o.delivery_street_address,  o.delivery_postcode,  o.delivery_city,  o.delivery_company, o.delivery_suburb, ".
            "s.orders_status_name, sum(op.products_quantity) as products_count ".
        "FROM ".TABLE_ORDERS." o ".
        "INNER JOIN ".TABLE_ORDERS_STATUS." s ON (o.orders_status = s.orders_status_id) ".
        "INNER JOIN orders_products op ON (o.orders_id = op.orders_id) ".
        "WHERE ".
            "s.language_id = '".$_SESSION['languages_id']."' AND ".
            "o.orders_id = '{$order_id}' ".
        "GROUP BY o.orders_id ".
        "ORDER BY o.date_purchased DESC";

    error_log($orders_query);
    $orders_result = xtc_db_query($orders_query);

    $db_order = xtc_db_fetch_array($orders_result)

    if( !$db_order ){
        die("Could not get order info from database");
    }

    // split street name and number
    if(preg_match('/(.*)\s+(\d+.*)$/i', trim($db_order['delivery_street_address']), $matches) == 1) {
            $receiver_streetname   = $matches[1];
            $receiver_streetnumber = $matches[2];
    }
    else {
            $receiver_streetname   = trim($db_order['delivery_street_address']);
            $receiver_streetnumber = '';
    }

    $customer = array(
        'company_name'  => $db_order["delivery_company"],
        'first_name'    => $db_order["delivery_firstname"],
        'last_name'     => $db_order["delivery_lastname"],
        'street_name'   => $receiver_streetname,
        'street_number' => $receiver_streetnumber,
        'zip'           => $db_order["delivery_postcode"],
        'city'          => $db_order["delivery_city"],
        'country'       => 'Germany',
        'email'         => trim($db_order["customers_email_address"])
    );


    $failed = false;
    $tfiles = array();
    $getting_labels_at = microtime(true);

    $lockfp = fopen(DIR_FS_CATALOG . "cache/dhl_label-{$order_id}.lock", "w+");
    if(!$lockfp || !flock($fp, LOCK_EX)){
        die("Could not get lock. We can't be sure there's no other process currently running, aborting.");
    }

    for( $i = 0; $i < $db_order["products_count"]; $i++ ){
        $labelfile = DIR_FS_CATALOG . "cache/dhl_label-{$order_id}-{$i}.pdf"
        $tfiles[]  = $labelfile;

        if( !file_exists($labelfile) || !filesize($labelfile)){
            set_time_limit(29);
            $label = createShipment( $db_order, $customer );

            if( $label["success"] ){
                // Download the label into a temp file
                $retries = 0;
                while(($label = get_with_curl($label["label_url"])) === false){
                    if( $retries < 5 ){
                        error_log("download failed, retry...");
                        $retries++;
                        sleep(.2);
                    }
                    else{
                        error_log("download failed, giving up.");
                        $failed = true;
                        break;
                    }
                }
                file_put_contents($labelfile, $label);
            }
            else{
                echo "<pre>Failed:\n";
                print_r($label);
                echo "</pre>";
                $failed = true;
            }
        }

        if($failed)
            break;

        sleep(.2);
    }

    flock($fp, LOCK_UN);
    fclose($fp);

    if( !$failed ){
        $merging_pdf_at = microtime(true);
        $pdf = new PDFMerger();
        foreach($tfiles as $tfile){
            $pdf->addPDF($tfile, "all");
        }
        $mergedPdf = $pdf->merge("string");
        $done_at = microtime(true);

        $num_labels = count($tfiles);
        $download_secs = $merging_pdf_at - $getting_labels_at;
        $merging_secs  = $done_at - $merging_pdf_at;
        error_log("Returning {$num_labels} labels downloaded in {$download_secs} and merged in {$merging_secs}");

        header("Content-Type: Application/PDF");
        echo $mergedPdf;
    }

    foreach($tfiles as $tfile){
        unlink($tfile);
    }
}

