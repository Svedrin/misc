// kate: hl c++

#include "ESP8266WiFi.h"
#include <PubSubClient.h>

// this file #defines WIFI_SSID, WIFI_PASSWORD and the MQTT_* params
#include <WifiParams.h>

#define SENSORNAME "netzwerkschrank"
#define STROMPIN  4

WiFiClient espClient;
PubSubClient client(espClient);

volatile long lastTick  = 0;
volatile long lastCheck = 0;


void reconnect() {
    // Loop until we're reconnected
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");
        // Create a random client ID
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

    client.setServer(MQTT_HOST, MQTT_PORT);

    pinMode(STROMPIN, INPUT);
    attachInterrupt(digitalPinToInterrupt(STROMPIN), tick, CHANGE);
}

void tick() {
    long now = millis();
    // debounce: only accept if more than 100ms ago
    if( now > lastTick + 100 ){
        lastTick = now;
    }
}

void loop() {
    if (!client.connected()) {
        reconnect();
    }

    client.loop();

    double delta;
    double watts;

    if (lastTick > lastCheck) {
        if( lastCheck > 0 ){
            delta = (lastTick - lastCheck) / 1000.;
            watts = 1.0 / delta * 3600.;
            Serial.print("Current consumption = ");
            Serial.print(watts);
            Serial.println("W");
            client.publish("strom/" SENSORNAME "/delta", String(delta).c_str());
            client.publish("strom/" SENSORNAME "/watts", String(watts).c_str());
        }
        else{
            Serial.println("First tick, waiting for more");
        }
        lastCheck = lastTick;
    }
    delay(1000);
}
