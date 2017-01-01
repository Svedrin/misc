/* kate: space-indent on; indent-width 2; replace-tabs on; hl c++

  Poor Man's CAN Bus
  Uses a single wire to build a multi-master realtime bus that operates
  pretty much in the same way as the CAN bus does.

  Wiring:

    * Connect port 8 to the bus wire
    * Connect port 7 via a diode to port 8, kathode facing to 7.
      This way, port 7 can write a "0" bit, but does not affect
      the bus state when writing a "1".
    * Connect the bus to VCC via a 10k pull-up resistor.

  Also, hardwire port 4 to VCC for the sender and GND for the receiver.

  Noteworthy Versions:

    * Moved code into the CanDrive library (2017-01-01)
      https://bitbucket.org/Svedrin/misc/src/1634efe2/arduino/libraries/CanDrive/
      https://bitbucket.org/Svedrin/misc/src/1634efe2/arduino/PoorMansCan.ino

    * Added CRC and End-of-Frame (2016-12-23)
      https://bitbucket.org/Svedrin/misc/src/8c4a29b5/arduino/PoorMansCan.ino

    * Initial Version (2016-12-21)
      https://bitbucket.org/Svedrin/misc/src/83581ca4/arduino/PoorMansCan.ino

 */

#include "CanDrive.h"

#define ROLE_RECVER 0
#define ROLE_SENDER 1

int my_role;

// when I'm a sender, send this pin's value as message
#define PIN_SOURCE  A0

#define PIN_ROLE     4
#define PIN_SENDER   7
#define PIN_MONITOR  8
#define PIN_MIRROR   9
#define PIN_CRCLED  10

int sender_pause = 100;
unsigned long long pause_until = 0;
CanDrive can(PIN_SENDER, PIN_MONITOR);

void setup() {
  pinMode(PIN_ROLE, INPUT);
  my_role = digitalRead(PIN_ROLE);
  if( my_role == ROLE_SENDER ){
    pause_until = millis() + sender_pause;
  }

  can.pin_mirror = PIN_MIRROR;
  can.pin_crcled = PIN_CRCLED;
  can.init();

  pinMode(13, INPUT);
  pinMode(12, INPUT);
  pinMode(11, INPUT);
  pinMode(10, INPUT);
}

void loop() {
  uint16_t recv_id, recv_val;

  if( my_role == ROLE_SENDER && millis() > pause_until ){
    if( digitalRead(13) == LOW ){
      can.send(250, analogRead(PIN_SOURCE) * 10);
    }
    else if( digitalRead(12) == LOW ){
      can.send(251, analogRead(PIN_SOURCE) * 10);
    }
    else if( digitalRead(11) == LOW ){
      can.send(250, 0);
    }
    else if( digitalRead(10) == LOW ){
      can.send(251, 0);
    }
    else{
      can.send(42, analogRead(PIN_SOURCE));
    }
    pause_until = millis() + sender_pause;
  }

  can.handle_message();

  if( can.recv(&recv_id, &recv_val) ){
    // do something with the received message.
  }
}
