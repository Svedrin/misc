// kate: hl c++

#include "ESP8266WiFi.h"
#include <PubSubClient.h>
#include <ArduinoJson.h>

// this file #defines WIFI_SSID and WIFI_PASSWORD
#include <WifiParams.h>

const char* mqtt_server = "rabbitmq.local.lan";

#define PIN_SWITCH_DOWN 12
#define PIN_SWITCH_UP   13
#define PIN_GATE_DOWN   14
#define PIN_GATE_UP      4


WiFiClient espClient;
PubSubClient client(espClient);

long lastMsg = 0;
char msg[150];

typedef enum {
    INIT,
    HALT_WAIT,
    HALT,
    MANUAL_DOWN,
    MANUAL_UP,
    AUTO_DOWN,
    AUTO_UP
} state_t;

int last_halt_position = 0;
int target_position    = 0;
int current_position   = 0;

state_t active_state = INIT;
int     active_since = 0;


#define NEWSTATE(state) { active_state = state; active_since = now; Serial.print("New state: "); Serial.print(state); Serial.println(""); }


void callback(char* topic, byte* payload, unsigned int length) {
    Serial.print("Message arrived [");
    Serial.print(topic);
    Serial.print("] ");

    // The message is supposed to be {"id": <hopefully ours>, "target_position": 75%}.
    const int BUFFER_SIZE = JSON_OBJECT_SIZE(2);
    StaticJsonBuffer<BUFFER_SIZE> jsonBuffer;

    JsonObject& root = jsonBuffer.parseObject(payload);

    if( root["id"] == ESP.getChipId() ){
        target_position = constrain(root["target_position"], 0, 100);
    }
}

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
            // Once connected, publish an announcement...
            client.publish("outTopic", "hello world");
            // ... and resubscribe
            client.subscribe("inTopic");
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
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("");
    Serial.println("WiFi connected");

    // Print the IP address
    Serial.println(WiFi.localIP());

    pinMode(PIN_SWITCH_DOWN, INPUT);
    pinMode(PIN_SWITCH_UP,   INPUT);
    pinMode(PIN_GATE_DOWN,   OUTPUT);
    pinMode(PIN_GATE_UP,     OUTPUT);

    randomSeed(micros());

    client.setServer(mqtt_server, 1883);
    client.setCallback(callback);
}

void loop() {
    if (!client.connected()) {
        reconnect();
    }

    client.loop();

    long now = millis();

    if (now - lastMsg > 2000) {
        lastMsg = now;

        const int BUFFER_SIZE = JSON_OBJECT_SIZE(5);
        StaticJsonBuffer<BUFFER_SIZE> jsonBuffer;

        JsonObject& root = jsonBuffer.createObject();
        root["id"]    = ESP.getChipId();
        root["state"] = (long)active_state;
        root["since"] = now - active_since;
        root["current_position"] = current_position;
        root["target_position"]  = target_position;

        root.printTo(msg);
        client.publish("outTopic", msg);
    }

    // Read the states desired by the user and by our controller

    int user_state = HALT;
    if( digitalRead(PIN_SWITCH_UP) == LOW ){
        user_state = MANUAL_UP;
    }
    else if( digitalRead(PIN_SWITCH_DOWN) == LOW ){
        user_state = MANUAL_DOWN;
    }

    int auto_state = HALT;
    if( target_position < current_position - 10 ){
        auto_state = AUTO_UP;
    }
    else if( target_position > current_position + 10 ){
        auto_state = AUTO_DOWN;
    }

    // Make sure our outputs reflect what we *should* be doing

    switch(active_state){
        default:
            digitalWrite(PIN_GATE_DOWN, LOW);
            digitalWrite(PIN_GATE_UP,   LOW);
            break;

        case MANUAL_UP:
        case AUTO_UP:
            digitalWrite(PIN_GATE_DOWN, LOW);
            digitalWrite(PIN_GATE_UP,   HIGH);
            break;

        case MANUAL_DOWN:
        case AUTO_DOWN:
            digitalWrite(PIN_GATE_DOWN, HIGH);
            digitalWrite(PIN_GATE_UP,   LOW);
            break;
    }

    // Update current_position

    switch(active_state){
        case MANUAL_DOWN:
        case AUTO_DOWN:
            // It takes 20 seconds to go from 0% to 100%. (Gravity helps.)
            // 200 = 23[s] * 1000[ms/s] / 100[%].
            current_position = last_halt_position + ((now - active_since) / 200.0);
            break;

        case MANUAL_UP:
        case AUTO_UP:
            // It takes 23 seconds to go from 100% to 0%.
            // 230 = 23[s] * 1000[ms/s] / 100[%].
            current_position = last_halt_position - ((now - active_since) / 230.0);
            break;
    }


    // Now decide what we're gonna do next

    switch(active_state){
        case HALT:
            if( user_state == MANUAL_UP ){
                if( current_position > 0 ){
                    target_position = -1;
                    NEWSTATE(MANUAL_UP)
                }
            }
            else if( user_state == MANUAL_DOWN ){
                if( current_position < 100 ){
                    target_position = -1;
                    NEWSTATE(MANUAL_DOWN)
                }
            }
            else if( auto_state == AUTO_UP ){
                NEWSTATE(AUTO_UP)
            }
            else if( auto_state == AUTO_DOWN ){
                NEWSTATE(AUTO_DOWN)
            }
            break;

        case HALT_WAIT:
            if( now - active_since > 3000 ){
                last_halt_position = constrain(current_position, 0, 100);
                NEWSTATE(HALT)
            }
            break;

        case MANUAL_DOWN:
            if( user_state != MANUAL_DOWN || current_position >= 100 ){
                target_position = current_position;
                NEWSTATE(HALT_WAIT)
            }
            break;

        case MANUAL_UP:
            if( user_state != MANUAL_UP || current_position <= 0 ){
                target_position = current_position;
                NEWSTATE(HALT_WAIT)
            }
            break;

        case AUTO_DOWN:
            if( current_position >= target_position ){
                target_position = current_position;
                NEWSTATE(HALT_WAIT)
            }
            break;

        case AUTO_UP:
            if( current_position <= target_position ){
                target_position = current_position;
                NEWSTATE(HALT_WAIT)
            }
            break;

        default:
            NEWSTATE(HALT_WAIT)
    }

}
