/* kate: space-indent on; indent-width 2; replace-tabs on; hl c++

  Poor Man's CAN Bus
  Uses a single wire to build a multi-master realtime bus that operates
  pretty much in the same way as the CAN bus does.

  See CanDrive.h for details.

 */


#include "Arduino.h"
#include "CanDrive.h"


#define STATE_INIT  0
#define STATE_ID    1
#define STATE_MSG   2
#define STATE_WAIT  3
#define STATE_CRC   4
#define STATE_EOFRM 5



void digitalWriteOrDelay(int pin, int val){
  // digitalWrite is actually a pretty slow thing to do on an Arduino.
  // So, if optional pins are disabled, we need to call delayMicroseconds
  // to avoid messing up our timing when some devices on the bus have
  // those pins enabled and others have them disabled.
  if( pin != 0 ){
    digitalWrite(pin, val);
  }
  else{
    delayMicroseconds(5);
  }
}



CanDrive::CanDrive(int pin_sender, int pin_monitor){
  this->pin_sender  = pin_sender;
  this->pin_monitor = pin_monitor;
  this->pin_mirror  = 0;
  this->pin_crcled  = 0;
  this->phase_delay = 250;

  this->recv_message_valid = false;
  this->send_message = false;
}


void CanDrive::init(){
  pinMode(this->pin_sender,  OUTPUT);
  pinMode(this->pin_monitor, INPUT);

  digitalWrite(this->pin_sender, HIGH);

  if( pin_mirror ){
    pinMode(this->pin_mirror, OUTPUT);
    digitalWrite(this->pin_mirror, HIGH);
  }
  if( pin_crcled ){
    pinMode(this->pin_crcled, OUTPUT);
    digitalWrite(this->pin_crcled, HIGH);
  }
}


boolean CanDrive::is_idle(){
  return pmc_state == STATE_INIT;
}

boolean CanDrive::send(uint16_t id, uint16_t value){
  if( this->send_message ){
    // Another message is currently being sent -> abort
    return false;
  }
  this->send_message_id    = id;
  this->send_message_value = value;
  this->send_message       = true;
  return true;
}

boolean CanDrive::recv(uint16_t* id, uint16_t* value){
  // Return the received ID and value, if any
  if( this->recv_message_valid ){
    *id    = this->recv_message_id;
    *value = this->recv_message_value;
    this->recv_message_valid = false;
    return true;
  }
  return false;
}

void CanDrive::handle_message(){
  do{
    this->handle_bit();
  } while( pmc_state != STATE_INIT );
}

void CanDrive::handle_bit(){
  int my_value, bus_value;

  // WRITE STAGE

  my_value = HIGH;

  if( send_message ){
    if( pmc_state == STATE_INIT ){
      // This looks like a perfect opportunity to start a new frame
      next_state = STATE_ID;
      bits_to_go = CAN_LEN_ID;
      crc_calc_buf    = 0;
      my_value   = LOW;
    }
    else if( pmc_state == STATE_ID ){
      bits_to_go--;
      my_value = (send_message_id & (1<<bits_to_go)) > 0;
      if( bits_to_go == 0 ){
        next_state = STATE_MSG;
        bits_to_go = CAN_LEN_MSG;
      }
    }
    else if( pmc_state == STATE_MSG ){
      bits_to_go--;
      my_value = (send_message_value & (1<<bits_to_go)) > 0;
      if( bits_to_go == 0 ){
        next_state = STATE_CRC;
        bits_to_go = CAN_LEN_CRC;
      }
    }
    else if( pmc_state == STATE_CRC ){
      bits_to_go--;
      my_value = (crc_calc_buf & (1<<bits_to_go)) > 0;
      if( bits_to_go == 0 ){
        next_state = STATE_EOFRM;
        bits_to_go = CAN_LEN_EOFRM;
      }
    }
    else if( pmc_state == STATE_EOFRM ){
      bits_to_go--;
      if( bits_to_go == 0 ){
        // Message sent successfully
        next_state = STATE_INIT;
        send_message_id    = 0;
        send_message_value = 0;
        send_message       = false;
      }
    }

    // calculate CRC checksum while sending
    if( pmc_state == STATE_ID || pmc_state == STATE_MSG ){
      if( ((crc_calc_buf >> CAN_LEN_CRC) & 1) != my_value ){
        crc_calc_buf = (crc_calc_buf << 1) ^ CAN_CRC_MASK;
      }
      else{
        crc_calc_buf = (crc_calc_buf << 1);
      }
    }
  }

  digitalWrite(pin_sender, my_value);

  if( pmc_state != STATE_INIT ){
    delayMicroseconds(phase_delay);
  }

  // READ STAGE
  bus_value = digitalRead(pin_monitor);
  digitalWriteOrDelay(pin_mirror, bus_value);

  if( send_message ){
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
      }
    }
  }
  else{ /* !send_message */
    if( pmc_state == STATE_INIT ){
      if( bus_value == LOW ){
        // Someone announced they're gonna send
        next_state = STATE_ID;
        crc_calc_buf = 0;
        crc_verify_buf = 0;
        recv_message_id    = 0;
        recv_message_valid = false;
        recv_message_value = 0;
        bits_to_go = CAN_LEN_ID;
        digitalWriteOrDelay(pin_crcled, HIGH);
      }
    }
    else if( pmc_state == STATE_ID ){
      bits_to_go--;
      recv_message_id = (recv_message_id << 1) | bus_value;
      if( bits_to_go == 0 ){
        next_state = STATE_MSG;
        bits_to_go = CAN_LEN_MSG;
      }
    }
    else if( pmc_state == STATE_MSG ){
      bits_to_go--;
      recv_message_value = (recv_message_value << 1) | bus_value;
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
        crc_calc_buf |= (1 << CAN_LEN_CRC);
        crc_verify_buf |= (1 << CAN_LEN_CRC);
        recv_message_valid = (crc_calc_buf == crc_verify_buf);
        if( !recv_message_valid ){
          // CRC checksum error occurred
          digitalWriteOrDelay(pin_crcled, LOW);
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
      if( ((crc_calc_buf >> CAN_LEN_CRC) & 1) != bus_value ){
        crc_calc_buf = (crc_calc_buf << 1) ^ CAN_CRC_MASK;
      }
      else{
        crc_calc_buf = (crc_calc_buf << 1);
      }
    }
  }

  delayMicroseconds(phase_delay);

  pmc_state = next_state;
}
