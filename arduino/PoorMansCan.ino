/*
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

// Delay for 500µs between send/recv cycles.
// We want to be able to transmit a single message in max 10ms. One message
// is a zero bit + 11 bits ID + 16 bits data. That means we need a min bitrate
// of 1+11+16 / 0.010 = 1612 b/s. So for simplicity, we'll operate at 2kbps.
// That means one bit every 500µs, and since that time is split into two phases
// each with their own delay(), we'll need to set half that time here.
int microdelay = 250;

int sender_pause = 2000;
unsigned long long pause_until  = 0;

#define STATE_INIT 0
#define STATE_ID   1
#define STATE_MSG  2
#define STATE_WAIT 3
int pmc_state = STATE_INIT;
int next_state = STATE_INIT;


// state variables

int source_val = 0;
int message_val;
unsigned int message_id = 0;
unsigned int bitsToGo = 0;

void setup() {
  Serial.begin(9600);
  pinMode(sender,  OUTPUT);
  pinMode(monitor, INPUT);
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
        Serial.println("STATE_INIT -> STATE_ID");

        message_id = 42;
        source_val = analogRead(source);
        bitsToGo = 11;

        digitalWrite(sender, LOW);
      }
      else{
        digitalWrite(sender, HIGH);
      }
    }
    else if( pmc_state == STATE_ID ){
      bitsToGo--;
      myValue = (message_id & (1<<bitsToGo)) > 0;
      digitalWrite(sender, myValue);
      if( bitsToGo == 0 ){
        Serial.println("STATE_ID -> STATE_MSG");
        next_state = STATE_MSG;
        bitsToGo = 16;
      }
    }
    else if( pmc_state == STATE_MSG ){
      bitsToGo--;
      myValue = (source_val & (1<<bitsToGo));
      digitalWrite(sender, myValue);
      if( bitsToGo == 0 ){
        next_state = STATE_INIT;
        Serial.println("STATE_MSG -> STATE_INIT");
        pause_until = millis() + sender_pause;
      }
    }
    else if( pmc_state == STATE_WAIT ){
      digitalWrite(sender, HIGH);
    }
  }
  else{
    digitalWrite(sender, HIGH);
  }

  delayMicroseconds(microdelay);

  // READ STAGE
  busValue = digitalRead(monitor);
  if( pmc_state != STATE_INIT ){
    Serial.println(busValue);
  }

  if( my_role == ROLE_SENDER ){
    if( pmc_state == STATE_ID ){
      // See if we have a recessive bit which was killed
      if( myValue == HIGH && busValue == LOW ){
        // Someone else killed our bit -> Wait until next frame
        next_state = STATE_WAIT;
        Serial.println("STATE_ID -> STATE_WAIT");
        bitsToGo += 16;
      }
    }
    else if( pmc_state == STATE_WAIT ){
      // Can only happen to the sender
      bitsToGo--;
      if( bitsToGo == 0 ){
        next_state = STATE_INIT;
        Serial.println("STATE_WAIT -> STATE_INIT");
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
        bitsToGo = 11;
        Serial.println("STATE_INIT -> STATE_ID");
      }
    }
    else if( pmc_state == STATE_ID ){
      bitsToGo--;
      message_id = (message_id << 1) | busValue;
      if( bitsToGo == 0 ){
        next_state = STATE_MSG;
        bitsToGo = 16;
        message_val = 0;
        Serial.println("STATE_ID -> STATE_MSG");
        Serial.println(message_id);
      }
    }
    else if( pmc_state == STATE_MSG ){
      bitsToGo--;
      message_val = (message_val << 1) | busValue;
      if( bitsToGo == 0 ){
        next_state = STATE_INIT;
        Serial.println("STATE_MSG -> STATE_INIT");
        Serial.println(message_val);
      }
    }
  }

  delayMicroseconds(microdelay);

  if( next_state != pmc_state ){
    Serial.print("State is currently ");
    Serial.print(pmc_state);
    Serial.print(", setting to ");
    Serial.print(next_state);
    Serial.println();
  }
  pmc_state = next_state;
}



