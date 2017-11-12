// kate: hl c++

#include "ESP8266WiFi.h"
#include <SPI.h>
#include "SPISlave.h"
#include <PubSubClient.h>

// this file #defines WIFI_SSID and WIFI_PASSWORD
#include <WifiParams.h>

const char* mqtt_server = "rabbitmq.local.lan";

WiFiClient espClient;
PubSubClient client(espClient);
long msg_clean = true;
char msg[250];
int value = 0;

void reconnect() {
    // Loop until we're reconnected
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");
        // Create a random client ID
        String clientId = "ESP8266Client-";
        clientId += String(random(0xffff), HEX);
        // Attempt to connect
        if (client.connect(clientId.c_str(), "ardu", "ino")) {
            Serial.println("connected");
        } else {
            Serial.printf("failed, rc=%d -- trying again in 5 seconds\n", client.state());
            // Wait 5 seconds before retrying
            delay(5000);
        }
    }
}

void setup(void)
{
    // Start Serial
    Serial.begin(74880);

    // Connect to WiFi
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    WiFi.mode(WIFI_STA);
    Serial.println();
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("");
    Serial.println("WiFi connected");

    // Print the IP address
    Serial.println(WiFi.localIP());

    randomSeed(micros());

    client.setServer(mqtt_server, 1883);


    SPISlave.onData([](uint8_t * data, size_t len) {
        uint16_t recv_id,
                 recv_val;
        memcpy(&recv_id,  data + 0, 2);
        memcpy(&recv_val, data + 2, 2);
        if( recv_id != 0 && msg_clean ){
            snprintf(msg, sizeof(msg) - 1, "{ \"esp_id\": %d, \"msg_id\": %d, \"value\": %d }",
                ESP.getChipId(),
                recv_id,
                recv_val
            );
            msg_clean = false;
            Serial.println(msg);
        }
    });
    SPISlave.begin();
}

void loop() {
    if (!client.connected()) {
        reconnect();
    }

    if( !msg_clean ){
        client.publish("from_can", msg);
        msg_clean = true;
    }
    client.loop();
}
