/* kate: space-indent on; indent-width 2; replace-tabs on; hl c++

  CAN-controlled controller for two railroad switches.

 */

#include "CanDrive.h"

#define PIN_SENDER   7
#define PIN_MONITOR  8

CanDrive can(PIN_SENDER, PIN_MONITOR);

void setup() {
  can.init();

  pinMode(13, OUTPUT);
  pinMode(12, OUTPUT);
  pinMode(11, OUTPUT);
  pinMode( 9, OUTPUT);
}

unsigned long long reset1 = 0;
unsigned long long reset2 = 0;


void loop() {
  uint16_t recv_id, recv_val;

  if( reset1 != 0 && millis() > reset1 ){
    digitalWrite(13, LOW);
    digitalWrite(12, LOW);
    reset1 = 0;
  }

  if( reset2 != 0 && millis() > reset2 ){
    digitalWrite(11, LOW);
    digitalWrite( 9, LOW);
    reset2 = 0;
  }

  can.handle_message();

  if( can.recv(&recv_id, &recv_val) ){
    if( recv_id == 450 ){
      digitalWrite( (recv_val == 0 ? 13 : 12), HIGH);
      reset1 = millis() + 500;
    }
    else if( recv_id == 451 ){
      digitalWrite( (recv_val == 0 ? 11 :  9), HIGH);
      reset2 = millis() + 500;
    }
  }
}
