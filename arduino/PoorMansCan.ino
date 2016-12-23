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

    * Initial Version (2016-12-21)
      https://bitbucket.org/Svedrin/misc/src/83581ca4/arduino/PoorMansCan.ino

 */


// Config variables

#define ROLE_RECVER 0
#define ROLE_SENDER 1

int my_role;

// when I'm a sender, send this pin's value as message
int source  = A0;

int rolepin = 4;
int sender  = 7;
int monitor = 8;
int mirror  = 9;

// Delay for 500µs between send/recv cycles.
// We want to be able to transmit a single message in max 10ms. One message
// is a zero bit + 11 bits ID + 16 bits data. That means we need a min bitrate
// of 1+11+16 / 0.010 = 1612 b/s. So for simplicity, we'll operate at 2kbps.
// That means one bit every 500µs, and since that time is split into two phases
// each with their own delay(), we'll need to set half that time here.
int microdelay = 250;

int sender_pause = 2000;
unsigned long long pause_until  = 0;

#define CAN_LEN_ID    11
#define CAN_LEN_MSG   16
#define CAN_LEN_EOFRM  7

#define STATE_INIT 0
#define STATE_ID   1
#define STATE_MSG  2
#define STATE_WAIT 3
#define STATE_EOFRM 4
int pmc_state = STATE_INIT;
int next_state = STATE_INIT;


// state variables

uint16_t source_val = 0;
uint16_t message_val;
unsigned int message_id = 0;
unsigned int bitsToGo = 0;

void setup() {
  Serial.begin(9600);
  pinMode(sender,  OUTPUT);
  pinMode(monitor, INPUT);
  pinMode(mirror,  OUTPUT);
  pinMode(rolepin, INPUT);
  pmc_state = STATE_INIT;
  digitalWrite(sender, HIGH);
  my_role = digitalRead(rolepin);
  if( my_role == ROLE_SENDER ){
    pause_until = millis() + sender_pause;
  }
}


void loop() {
  int myValue, busValue;

  // WRITE STAGE

  if( my_role == ROLE_SENDER ){
    if( pmc_state == STATE_INIT ){
      if( millis() > pause_until ){
        // This looks like a perfect opportunity to start a new frame
        next_state = STATE_ID;

        message_id = 42;
        source_val = analogRead(source);
        bitsToGo = CAN_LEN_ID;

        myValue = LOW;
      }
      else{
        myValue = HIGH;
      }
    }
    else if( pmc_state == STATE_ID ){
      bitsToGo--;
      myValue = (message_id & (1<<bitsToGo)) > 0;
      if( bitsToGo == 0 ){
        next_state = STATE_MSG;
        bitsToGo = CAN_LEN_MSG;
      }
    }
    else if( pmc_state == STATE_MSG ){
      bitsToGo--;
      myValue = (source_val & (1<<bitsToGo)) > 0;
      if( bitsToGo == 0 ){
        next_state = STATE_EOFRM;
        bitsToGo = CAN_LEN_EOFRM;
        Serial.println(".");
      }
    }
    else if( pmc_state == STATE_WAIT ){
      myValue = HIGH;
    }
    else if( pmc_state == STATE_EOFRM ){
      myValue = HIGH;
      bitsToGo--;
      if( bitsToGo == 0 ){
        next_state = STATE_INIT;
        Serial.println(".");
        pause_until = millis() + sender_pause;
      }
    }
  }
  else{
    myValue = HIGH;
  }

  digitalWrite(sender, myValue);

  delayMicroseconds(microdelay);

  // READ STAGE
  busValue = digitalRead(monitor);
  digitalWrite(mirror, busValue);

  if( my_role == ROLE_SENDER ){
    if( pmc_state == STATE_ID ){
      // See if we have a recessive bit which was killed
      if( myValue == HIGH && busValue == LOW ){
        // Someone else killed our bit -> Wait until next frame
        next_state = STATE_WAIT;
        bitsToGo += CAN_LEN_MSG;
      }
    }
    else if( pmc_state == STATE_WAIT ){
      // Can only happen to the sender
      bitsToGo--;
      if( bitsToGo == 0 ){
        next_state = STATE_INIT;
        pause_until = millis() + sender_pause;
      }
    }
  }
  else if( my_role == ROLE_RECVER ){
    if( pmc_state == STATE_INIT ){
      if( busValue == LOW ){
        // Someone announced they're gonna send
        next_state = STATE_ID;
        message_id = 0;
        bitsToGo = CAN_LEN_ID;
      }
    }
    else if( pmc_state == STATE_ID ){
      bitsToGo--;
      message_id = (message_id << 1) | busValue;
      if( bitsToGo == 0 ){
        next_state = STATE_MSG;
        bitsToGo = CAN_LEN_MSG;
        message_val = 0;
      }
    }
    else if( pmc_state == STATE_MSG ){
      bitsToGo--;
      message_val = (message_val << 1) | busValue;
      if( bitsToGo == 0 ){
        bitsToGo = CAN_LEN_EOFRM;
        next_state = STATE_EOFRM;
      }
    }
    else if( pmc_state == STATE_EOFRM ){
      bitsToGo--;
      if( bitsToGo == 0 ){
        next_state = STATE_INIT;
        Serial.print(message_id);
        Serial.print(" = ");
        Serial.println(message_val);
      }
    }
  }

  delayMicroseconds(microdelay);

  pmc_state = next_state;
}
