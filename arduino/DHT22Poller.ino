// kate: hl c++

#include "ESP8266WiFi.h"
#include <PubSubClient.h>

// this file #defines WIFI_SSID and WIFI_PASSWORD
#include <WifiParams.h>

#include <DHT.h>

#define SENSORNAME "netzwerkschrank"

#define DHTTYPE DHT22
#define DHTPIN  5

DHT dht(DHTPIN, DHTTYPE, 11); // 11 works fine for ESP8266

WiFiClient espClient;
PubSubClient client(espClient);
long lastMsg = 0;

void reconnect() {
    // Loop until we're reconnected
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");
        // Attempt to connect
        String clientId = "ESP8266Client-" + String(ESP.getChipId(), HEX);
        if (client.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD)) {
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
    Serial.begin(115200);

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

    client.setServer(MQTT_HOST, MQTT_PORT);
}

void loop() {
    if (!client.connected()) {
        reconnect();
    }

    client.loop();

    long now = millis();
    double temp;
    double humd;

    if (lastMsg == 0 || now - lastMsg > 1 * 30 * 1000) {
        lastMsg = now;

        temp = dht.readTemperature(false);
        humd = dht.readHumidity();

        client.publish("sensor/" SENSORNAME "/temperature", String(temp).c_str());
        client.publish("sensor/" SENSORNAME "/humidity",    String(humd).c_str());

        Serial.print("Temp = ");
        Serial.print(temp);
        Serial.print("; Humidity = ");
        Serial.println(humd);
    }

    delay(1000);
}
