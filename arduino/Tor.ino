// kate: hl c++

#include "ESP8266WiFi.h"
#include <PubSubClient.h>

// this file #defines WIFI_SSID and WIFI_PASSWORD
#include <WifiParams.h>

#define PIN_UP D1
#define PIN_DN D2

#define PIN_TRIGGER D5
#define PIN_LB_BLOCKED D6     // Light barrier says "I'm blocked"
#define PIN_LB_CLEAR   D7     // Light barrier says "I'm clear"

WiFiClient espClient;
PubSubClient client(espClient);

typedef enum {
    GATE_INIT,     // State used for the first reading after boot
    GATE_OPEN,     // Gate is full open (top sensor is low)
    GATE_UNKNOWN,  // Gate is somewhere between full open and full closed
    GATE_CLOSED    // Gate is full closed (bottom sensor is low)
} state_t;

state_t active_state = GATE_INIT;
long received_close_at;
long received_commit_at;
unsigned long last_tick;
unsigned long last_msg;
char* hard_pos = NULL;
char prev_hard_pos[50];

void reconnect() {
    // Loop until we're reconnected
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");
        // Attempt to connect
        String clientId = "ESP8266Client-" + String(ESP.getChipId(), HEX);
        if (client.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD)) {
            client.subscribe("ctrl/tor/set_hard_position");
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

    pinMode(PIN_TRIGGER, OUTPUT);
    digitalWrite(PIN_TRIGGER, LOW);

    pinMode(PIN_UP, INPUT);
    pinMode(PIN_DN, INPUT);
    pinMode(PIN_LB_BLOCKED, INPUT_PULLUP);
    pinMode(PIN_LB_CLEAR,   INPUT_PULLUP);

    client.setServer(MQTT_HOST, MQTT_PORT);
    client.setCallback(on_mqtt_message);

    received_close_at   = 0;
    received_commit_at  = 0;
    last_tick = 0;
    last_msg  = 0;
}


void on_mqtt_message(char* topic, byte* payload, unsigned int length) {
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

    if( strcmp(topic, "ctrl/tor/set_hard_position") == 0 ){
        if(strncmp((const char *)payload, "CLOSED", length) == 0){
            Serial.println("Received CLOSE message");
            if(active_state == GATE_OPEN && received_close_at == 0){
                received_close_at = millis();
                client.publish("ctrl/tor/close_ack", "waiting");
            }
        }
        else if(strncmp((const char *)payload, "COMMIT", length) == 0){
            Serial.println("Received COMMIT message");
            if(active_state == GATE_OPEN && received_commit_at == 0){
                received_commit_at = millis();
                client.publish("ctrl/tor/close_ack", "commit");
            }
        }
    }
}


void trigger() {
    digitalWrite(PIN_TRIGGER, HIGH);
    delay(500);
    digitalWrite(PIN_TRIGGER, LOW);
}

void loop() {
    if (!client.connected()) {
        reconnect();
    }

    client.loop();

    unsigned long now = millis();

    if(now > last_tick + 100){
        last_tick = now;

        switch(active_state){
            default:
            case GATE_INIT:
                if( digitalRead(PIN_DN) == LOW ){
                    active_state = GATE_CLOSED;
                    hard_pos = "CLOSED";
                }
                else if( digitalRead(PIN_UP) == LOW ){
                    active_state = GATE_OPEN;
                    hard_pos = "OPEN";
                }
                else {
                    active_state = GATE_UNKNOWN;
                    hard_pos = "UNKNOWN";
                }
                break;

            case GATE_OPEN:
                hard_pos = "OPEN";
                if( digitalRead(PIN_LB_BLOCKED) == LOW ){
                    hard_pos = "BLOCKED";
                    if(received_close_at != 0){
                        client.publish("ctrl/tor/close_ack", "abort");
                        received_close_at  = 0;
                        received_commit_at = 0;
                    }
                }
                else if( digitalRead(PIN_LB_CLEAR) == HIGH ){
                    hard_pos = "ERROR";
                }
                else if( digitalRead(PIN_UP) != LOW ){
                    active_state = GATE_UNKNOWN;
                }
                else if(received_close_at != 0){
                    if( received_commit_at != 0 ){
                        Serial.println(abs(received_close_at + 10000 - received_commit_at));
                        if(abs(received_close_at + 10000 - received_commit_at) < 100){
                            client.publish("ctrl/tor/close_ack", "closing");
                            trigger();
                        }
                        received_close_at   = 0;
                        received_commit_at  = 0;
                    }
                }
                break;

            case GATE_UNKNOWN:
                hard_pos = "UNKNOWN";
                received_close_at   = 0;
                received_commit_at  = 0;
                if( digitalRead(PIN_DN) == LOW ){
                    active_state = GATE_CLOSED;
                }
                else if( digitalRead(PIN_UP) == LOW ){
                    active_state = GATE_OPEN;
                }
                break;

            case GATE_CLOSED:
                hard_pos = "CLOSED";
                received_close_at   = 0;
                received_commit_at  = 0;
                if( digitalRead(PIN_DN) != LOW ){
                    active_state = GATE_UNKNOWN;
                }
                break;

        }

        if(now > last_msg + 1000 || strcmp(hard_pos, prev_hard_pos) != 0){
            last_msg = now;
            strcpy(prev_hard_pos, hard_pos);
            client.publish("ctrl/tor/current_hard_position", hard_pos);

            Serial.print("Hard position = ");
            Serial.println(hard_pos);
        }
    }

    delay(1);
}
