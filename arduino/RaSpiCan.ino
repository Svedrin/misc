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
  Serial.begin(74880);
  SPI.begin();
//  pinMode(PIN_SLAVESEL, OUTPUT);

  can.pin_mirror = PIN_MIRROR;
  can.pin_crcled = PIN_CRCLED;
  can.init();

  Serial.println("hai!");
  SPI.beginTransaction(SPISettings(15000000, MSBFIRST, SPI_MODE0));
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

  /*if( recv_id != 0 ){
    Serial.print(recv_id);
    Serial.print(" -> ");
    Serial.println(recv_val);
  }*/

  SPI.transfer(0x02);
  SPI.transfer(0x00);
  new_id  = (
    SPI.transfer((recv_id >> 0) & 0xFF) << 0 |
    SPI.transfer((recv_id >> 8) & 0xFF) << 8 );
  new_val = (
    SPI.transfer((recv_val >> 0) & 0xFF) << 0 |
    SPI.transfer((recv_val >> 8) & 0xFF) << 8);
  for( int i = 0; i < (32 - 2 - 2); i++ ){
    SPI.transfer(0);
  }

  /*if( new_id != 0 && new_id != 65535 ){
    can.send(new_id, new_val);
    Serial.print(new_id);
    Serial.print(" <- ");
    Serial.println(new_val);
  }*/
}
