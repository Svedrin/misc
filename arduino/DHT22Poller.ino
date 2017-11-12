// kate: hl c++

#include "ESP8266WiFi.h"
#include <PubSubClient.h>

// this file #defines WIFI_SSID and WIFI_PASSWORD
#include <WifiParams.h>

#include <DHT.h>

const char* mqtt_server = "rabbitmq.local.lan";

#define DHTTYPE DHT22
#define DHTPIN  4

// #define USE_DEEPSLEEP

DHT dht(DHTPIN, DHTTYPE, 11); // 11 works fine for ESP8266

WiFiClient espClient;
PubSubClient client(espClient);
long lastMsg = 0;
char msg[150];
int value = 0;
bool maySleep = false;

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
            Serial.print("failed, rc=");
            Serial.print(client.state());
            Serial.println(" try again in 5 seconds");
            // Wait 5 seconds before retrying
            delay(5000);
        }
    }
}

void setup(void)
{
    // Start Serial
//     Serial.begin(115200);
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

    dht.begin();

    client.setServer(mqtt_server, 1883);
}

void loop() {
    if (!client.connected()) {
        reconnect();
    }

    client.loop();

    long now = millis();

    if (lastMsg == 0 || now - lastMsg > 1 * 60 * 1000) {
        lastMsg = now;

        snprintf(msg, sizeof(msg) - 1, "{ \"id\": %d, \"temperature\": %s, \"humidity\": %s }",
            ESP.getChipId(),
            String( dht.readTemperature(false) ).c_str(),
            String( dht.readHumidity() ).c_str()
        );
        client.publish("sensors", msg);
        Serial.println(msg);
        maySleep = true;
    }

#ifdef USE_DEEPSLEEP
    if( lastMsg != 0 && maySleep && now - lastMsg > 5000 ){
        Serial.println("sleeping");
        ESP.deepSleep( 1 * 60 * 1000000 );
        maySleep = false;
    }
#endif
}
