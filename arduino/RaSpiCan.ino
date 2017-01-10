/* kate: space-indent on; indent-width 2; replace-tabs on; hl c++

  PMC<->SPI Connector. Best served together with a Raspberry Pi.
 */

#include <SPI.h>
#include "CanDrive.h"

#define PIN_SLAVESEL 10
#define PIN_SENDER   7
#define PIN_MONITOR  8
#define PIN_MIRROR   9
#define PIN_CRCLED  10

CanDrive can(PIN_SENDER, PIN_MONITOR);

void setup() {
  SPI.begin();
  pinMode(PIN_SLAVESEL, OUTPUT);

  can.pin_mirror = PIN_MIRROR;
//   can.pin_crcled = PIN_CRCLED;
  can.init();
}

uint16_t transfer16(uint16_t data){
  // SPI should have this one as well, but apparently Debian's
  // Arduino version doesn't yet have it, so here goes
  uint16_t buf = 0;
  buf |= (SPI.transfer(data >> 8) << 8);
  buf |= SPI.transfer(data & 0xFF);
  return buf;
}

void loop() {
  uint16_t recv_id  = 0,
           recv_val = 0,
           new_id   = 0,
           new_val  = 0;

  can.handle_message();

  // Recv. We don't care about whether or not this worked: If it
  // didn't, recv_id is still 0, so we can just use that.
  can.recv(&recv_id, &recv_val);

//   SPI.beginTransaction(SPISettings(14000000, MSBFIRST, SPI_MODE0));
  digitalWrite(PIN_SLAVESEL, LOW);

  new_id  = transfer16(recv_id);
  new_val = transfer16(recv_val);

  digitalWrite(PIN_SLAVESEL, HIGH);
//   SPI.endTransaction();

  if( new_id != 0 ){
    can.send(new_id, new_val);
  }
}
