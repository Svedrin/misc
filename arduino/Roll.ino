// kate: hl c++
// Schematic:      https://img.svedr.in/nerdkram/schaltplan-roll.png.html
// Implementation: https://img.svedr.in/nerdkram/IMG_20171105_154456.jpg.html

#include "ESP8266WiFi.h"
#include <ESP8266WebServer.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// this file #defines WIFI_SSID and WIFI_PASSWORD
#include <WifiParams.h>

#define PIN_SWITCH_DOWN 12
#define PIN_SWITCH_UP   13
#define PIN_GATE_DOWN   14
#define PIN_GATE_UP      4


WiFiClient espClient;
PubSubClient client(espClient);
ESP8266WebServer server(80);


long lastMsg = 0;
char msg[150];

typedef enum {
    INIT,
    HALT_WAIT,
    HALT,
    MANUAL_DOWN,
    MANUAL_UP,
    MANUAL_DOWN_DEBOUNCE,
    MANUAL_UP_DEBOUNCE,
    AUTO_DOWN,
    AUTO_UP
} state_t;

typedef enum {
    PROM_NEUTRAL,
    PROM_CONTROLLED,
    PROM_IGNORING
} promstate_t;

int last_halt_position = 0;
int target_position    = 0;
int current_position   = 0;

state_t active_state = INIT;
int     active_since = 0;

promstate_t prom_state = PROM_NEUTRAL;


#define NEWSTATE(state) { active_state = state; active_since = now; Serial.print("New state: "); Serial.print(state); Serial.println(""); }


void callback(char* topic, byte* payload, unsigned int length) {
    char buf[50];
    if( length > sizeof(buf) - 1 ){
        length = sizeof(buf) - 1;
    }
    memcpy(buf, payload, length);
    buf[length] = 0;

    Serial.print("Message arrived [");
    Serial.print(topic);
    Serial.print("] = ");
    Serial.print(buf);
    Serial.print(" => ");

    if( strcmp(topic, "ctrl/roll/set_target_position") == 0 ){
        target_position = constrain(atoi(buf), 0, 100);
        Serial.println(target_position);
        if( prom_state == PROM_CONTROLLED )
            prom_state = PROM_IGNORING;
    }
}

void reconnect() {
    // Loop until we're reconnected
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");
        String clientId = "ESP8266Client-" + String(ESP.getChipId(), HEX);
        if (client.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD)) {
            Serial.println("connected");
            client.subscribe("ctrl/roll/set_target_position");
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

    client.setServer(MQTT_HOST, MQTT_PORT);
    client.setCallback(callback);

    server.on("/", HTTP_GET, [](){
        server.sendHeader("Connection", "close");
        server.send(200, "text/html", "<h1>Roll!</h1>");
    });
    server.on("/promhook", HTTP_POST, [](){
        server.sendHeader("Connection", "close");

        StaticJsonBuffer<2048> jsonBuffer;
        JsonObject& root = jsonBuffer.parseObject(server.arg("plain"));

        if( root.success() && root.containsKey("status") ){
            if( strcmp( root["status"], "firing" ) == 0 ){
                if( prom_state == PROM_NEUTRAL ){
                    target_position = 100;
                    prom_state = PROM_CONTROLLED;
                }
            }
            else if( strcmp( root["status"], "resolved" ) == 0 ){
                if( prom_state == PROM_CONTROLLED ){
                    target_position = 0;
                }
                prom_state = PROM_NEUTRAL;
            }
        }

        server.send(200, "text/plain", "OK");
    });
    server.begin();

}

void loop() {
    if (!client.connected()) {
        reconnect();
    }

    server.handleClient();
    client.loop();

    long now = millis();

    if (now - lastMsg > 500) {
        lastMsg = now;
        client.publish("ctrl/roll/target_position",  String(target_position).c_str());
        client.publish("ctrl/roll/current_position", String(current_position).c_str());
        client.publish("ctrl/roll/active_state",     String(active_state).c_str());
        client.publish("ctrl/roll/active_since",     String(active_since).c_str());
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
        case MANUAL_UP_DEBOUNCE:
        case AUTO_UP:
            digitalWrite(PIN_GATE_DOWN, LOW);
            digitalWrite(PIN_GATE_UP,   HIGH);
            break;

        case MANUAL_DOWN:
        case MANUAL_DOWN_DEBOUNCE:
        case AUTO_DOWN:
            digitalWrite(PIN_GATE_DOWN, HIGH);
            digitalWrite(PIN_GATE_UP,   LOW);
            break;
    }

    // Update current_position

    switch(active_state){
        case MANUAL_DOWN:
        case MANUAL_DOWN_DEBOUNCE:
        case AUTO_DOWN:
            // It takes 20 seconds to go from 0% to 100%. (Gravity helps.)
            // 200 = 20[s] * 1000[ms/s] / 100[%].
            current_position = last_halt_position + ((now - active_since) / 200.0);
            break;

        case MANUAL_UP:
        case MANUAL_UP_DEBOUNCE:
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
                target_position = -1;
                if( prom_state == PROM_CONTROLLED )
                    prom_state = PROM_IGNORING;
                NEWSTATE(MANUAL_UP_DEBOUNCE)
            }
            else if( user_state == MANUAL_DOWN ){
                target_position = -1;
                if( prom_state == PROM_CONTROLLED )
                    prom_state = PROM_IGNORING;
                NEWSTATE(MANUAL_DOWN_DEBOUNCE)
            }
            else if( auto_state == AUTO_UP ){
                NEWSTATE(AUTO_UP)
            }
            else if( auto_state == AUTO_DOWN ){
                NEWSTATE(AUTO_DOWN)
            }
            break;

        case HALT_WAIT:
            if( now - active_since > 1000 ){
                last_halt_position = current_position;
                NEWSTATE(HALT)
            }
            break;

        case MANUAL_DOWN_DEBOUNCE:
            if( now - active_since > 500 ){
                NEWSTATE(MANUAL_DOWN)
            }
            break;

        case MANUAL_UP_DEBOUNCE:
            if( now - active_since > 500 ){
                NEWSTATE(MANUAL_UP)
            }
            break;

        case MANUAL_DOWN:
            if( user_state != MANUAL_DOWN ){
                target_position = current_position;
                NEWSTATE(HALT_WAIT)
            }
            break;

        case MANUAL_UP:
            if( user_state != MANUAL_UP ){
                // Used for calibration: If our app's zero is lower than *real* zero, the user
                // can just manually go to "real" zero and we'll use it as new zero. The hardware
                // will switch off eventually anyway, so this is correct.
                if(current_position < 0)
                    current_position = 0;
                target_position = current_position;
                NEWSTATE(HALT_WAIT)
            }
            break;

        case AUTO_DOWN:
            if( current_position >= target_position ){
                // At the 100% position, the blind can still be shut farther to achieve more
                // darkness. Just take a note of that position in our usual percentage so we
                // open correctly as far as we need to.
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
