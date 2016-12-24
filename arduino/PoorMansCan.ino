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

    * Added CRC and End-of-Frame (2016-12-23)
      https://bitbucket.org/Svedrin/misc/src/8c4a29b5/arduino/PoorMansCan.ino

    * Initial Version (2016-12-21)
      https://bitbucket.org/Svedrin/misc/src/83581ca4/arduino/PoorMansCan.ino

 */



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

// Delay for 500µs between send/recv cycles.
// We want to be able to transmit a single message in max 10ms. One message
// is a zero bit + 11 bits ID + 16 bits data. That means we need a min bitrate
// of 1+11+16 / 0.010 = 1612 b/s. So for simplicity, we'll operate at 2kbps.
// That means one bit every 500µs, and since that time is split into two phases
// each with their own delay(), we'll need to set half that time here.
int phase_delay = 250;

int sender_pause = 100;
unsigned long long pause_until  = 0;

#define CAN_LEN_ID    11
#define CAN_LEN_MSG   16
#define CAN_LEN_CRC   15
#define CAN_LEN_EOFRM  7

#define CAN_CRC_MASK 0xC599

#define STATE_INIT 0
#define STATE_ID   1
#define STATE_MSG  2
#define STATE_WAIT 3
#define STATE_CRC   4
#define STATE_EOFRM 5

int pmc_state  = STATE_INIT;
int next_state = STATE_INIT;

uint16_t source_val;
uint16_t message_id;
uint16_t message_val;

unsigned int bits_to_go = 0;

uint16_t crc_buf;
uint16_t crc_verify_buf;


void setup() {
  pinMode(PIN_ROLE,    INPUT);
  pinMode(PIN_MONITOR, INPUT);
  pinMode(PIN_SENDER,  OUTPUT);
  pinMode(PIN_MIRROR,  OUTPUT);
  pinMode(PIN_CRCLED,  OUTPUT);

  digitalWrite(PIN_SENDER, HIGH);

  my_role = digitalRead(PIN_ROLE);
  if( my_role == ROLE_SENDER ){
    pause_until = millis() + sender_pause;
  }
}


void loop() {
  int my_value, bus_value;

  // WRITE STAGE

  my_value = HIGH;

  if( my_role == ROLE_SENDER ){
    if( pmc_state == STATE_INIT ){
      if( millis() > pause_until ){
        // This looks like a perfect opportunity to start a new frame
        next_state = STATE_ID;

        crc_buf = 0;
        message_id = 42;
        source_val = analogRead(PIN_SOURCE);
        bits_to_go = CAN_LEN_ID;

        my_value = LOW;
      }
    }
    else if( pmc_state == STATE_ID ){
      bits_to_go--;
      my_value = (message_id & (1<<bits_to_go)) > 0;
      if( bits_to_go == 0 ){
        next_state = STATE_MSG;
        bits_to_go = CAN_LEN_MSG;
      }
    }
    else if( pmc_state == STATE_MSG ){
      bits_to_go--;
      my_value = (source_val & (1<<bits_to_go)) > 0;
      if( bits_to_go == 0 ){
        next_state = STATE_CRC;
        bits_to_go = CAN_LEN_CRC;
      }
    }
    else if( pmc_state == STATE_CRC ){
      bits_to_go--;
      my_value = (crc_buf & (1<<bits_to_go)) > 0;
      if( bits_to_go == 0 ){
        next_state = STATE_EOFRM;
        bits_to_go = CAN_LEN_EOFRM;
      }
    }
    else if( pmc_state == STATE_EOFRM ){
      bits_to_go--;
      if( bits_to_go == 0 ){
        next_state = STATE_INIT;
        pause_until = millis() + sender_pause;
      }
    }

    // calculate CRC checksum while sending
    if( pmc_state == STATE_ID || pmc_state == STATE_MSG ){
      if( ((crc_buf >> CAN_LEN_CRC) & 1) != my_value ){
        crc_buf = (crc_buf << 1) ^ CAN_CRC_MASK;
      }
      else{
        crc_buf = (crc_buf << 1);
      }
    }
  }

  digitalWrite(PIN_SENDER, my_value);

  if( pmc_state != STATE_INIT ){
    delayMicroseconds(phase_delay);
  }

  // READ STAGE
  bus_value = digitalRead(PIN_MONITOR);
  digitalWrite(PIN_MIRROR, bus_value);

  if( my_role == ROLE_SENDER ){
    if( pmc_state == STATE_ID ){
      // See if we have a recessive bit which was killed
      if( my_value == HIGH && bus_value == LOW ){
        // Someone else killed our bit -> Wait until next frame
        next_state = STATE_WAIT;
        bits_to_go += CAN_LEN_MSG + CAN_LEN_CRC + CAN_LEN_EOFRM;
      }
    }
    else if( pmc_state == STATE_WAIT ){
      // Can only happen to the sender
      bits_to_go--;
      if( bits_to_go == 0 ){
        next_state = STATE_INIT;
        pause_until = millis() + sender_pause;
      }
    }
  }
  else if( my_role == ROLE_RECVER ){
    if( pmc_state == STATE_INIT ){
      if( bus_value == LOW ){
        // Someone announced they're gonna send
        next_state = STATE_ID;
        crc_buf = 0;
        crc_verify_buf = 0;
        message_id = 0;
        bits_to_go = CAN_LEN_ID;
        // Turn off the LED while recving. this way, it can share
        // a resistor with an LED attached to PIN_MIRROR. (I don't
        // have room for a second R on my breadboard. no shit.)
        digitalWrite(PIN_CRCLED, HIGH);
      }
    }
    else if( pmc_state == STATE_ID ){
      bits_to_go--;
      message_id = (message_id << 1) | bus_value;
      if( bits_to_go == 0 ){
        next_state = STATE_MSG;
        bits_to_go = CAN_LEN_MSG;
        message_val = 0;
      }
    }
    else if( pmc_state == STATE_MSG ){
      bits_to_go--;
      message_val = (message_val << 1) | bus_value;
      if( bits_to_go == 0 ){
        bits_to_go = CAN_LEN_CRC;
        next_state = STATE_CRC;
      }
    }
    else if( pmc_state == STATE_CRC ){
      bits_to_go--;
      crc_verify_buf = (crc_verify_buf << 1) | bus_value;
      if( bits_to_go == 0 ){
        bits_to_go = CAN_LEN_EOFRM;
        next_state = STATE_EOFRM;
        // 16th bit is not sent, but may be set to 1 by the algo
        // so, normalize the most significant bit to 1
        crc_buf |= (1 << CAN_LEN_CRC);
        crc_verify_buf |= (1 << CAN_LEN_CRC);
        if( crc_buf == crc_verify_buf ){
          // CRC valid, LED off, need HIGH
          digitalWrite(PIN_CRCLED, HIGH);
        }
        else{
          digitalWrite(PIN_CRCLED, LOW);
        }
      }
    }
    else if( pmc_state == STATE_EOFRM ){
      bits_to_go--;
      if( bits_to_go == 0 ){
        next_state = STATE_INIT;
      }
    }

    // calculate CRC checksum while recving
    if( pmc_state == STATE_ID || pmc_state == STATE_MSG ){
      if( ((crc_buf >> CAN_LEN_CRC) & 1) != bus_value ){
        crc_buf = (crc_buf << 1) ^ CAN_CRC_MASK;
      }
      else{
        crc_buf = (crc_buf << 1);
      }
    }
  }

  delayMicroseconds(phase_delay);

  pmc_state = next_state;
}
