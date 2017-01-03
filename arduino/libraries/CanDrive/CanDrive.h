/* kate: space-indent on; indent-width 2; replace-tabs on; hl c++

  Poor Man's CAN Bus
  Uses a single wire to build a multi-master realtime bus that operates
  pretty much in the same way as the CAN bus does.

  Wiring:

    * Connect the monitor port to the bus wire
    * Connect the sender port via a diode to the monitor port, kathode
      facing to the sender.
      This way, the sender can write a "0" bit, but does not affect
      the bus state when writing a "1".
    * Connect the bus to VCC via a 10k pull-up resistor.

  Noteworthy Versions:

    * Moved code from PoorMansCan.ino sketch into this library (2017-01-01)
      https://bitbucket.org/Svedrin/misc/src/1634efe2/arduino/libraries/CanDrive/
      Usage example:
      https://bitbucket.org/Svedrin/misc/src/1634efe2/arduino/PoorMansCan.ino

    * Added CRC and End-of-Frame (2016-12-23)
      https://bitbucket.org/Svedrin/misc/src/8c4a29b5/arduino/PoorMansCan.ino

    * Initial Version (2016-12-21)
      https://bitbucket.org/Svedrin/misc/src/83581ca4/arduino/PoorMansCan.ino

 */

#ifndef CANDRIVE_H
#define CANDRIVE_H

#ifdef ARDUINO
#    include "Arduino.h"
#elif defined __linux__
#    include <stdint.h>
#    include <wiringPi.h>
typedef int boolean;
#endif

#define CAN_LEN_ID    11
#define CAN_LEN_MSG   16
#define CAN_LEN_CRC   15
#define CAN_LEN_EOFRM  7

#define CAN_CRC_MASK 0xC599

class CanDrive {
  public:
    // We need at least the sender and monitor pins.
    CanDrive(int pin_sender, int pin_monitor);

    // Call init() from your setup().
    void init();

    // If the bus is idle, you can use send and recv to easily modify
    // its message buffers in a safe way.
    boolean is_idle();

    // Write a message into the send buffers, if we can do that safely
    // now (success indicated by the return value).
    // Note that this call does not actually *send* the message -- it
    // only *schedules* the message to be sent during the next
    // handle_message run.
    boolean send(uint16_t id,  uint16_t value);

    // Get a message from the recv buffers, if those contain a valid
    // message that is complete (success indicated by return value).
    // If no message is available, the output variables are unchanged.
    boolean recv(uint16_t* id, uint16_t* value);

    // Call handle_message to easily send or receive a complete message.
    // You won't be returned control until the bus is idle again. (That is,
    // if you're not sending anything and the bus is quiet, you will be
    // returned control instantly.) You can omit the is_idle() check in
    // this case because your code will only run while the bus is idle.
    void handle_message();

    // Call handle_bit if you need to do things even while the bus is
    // busy. You'll have to use is_idle to see when it's safe to use
    // send and recv.
    void handle_bit();

    // These are the send buffers. Handle with care. See send().
    boolean  send_message;
    uint16_t send_message_id;
    uint16_t send_message_value;

    // These are the receive buffers. Handle with care. See recv().
    uint16_t recv_message_id;
    uint16_t recv_message_value;
    boolean  recv_message_valid;

    // Pin config. sender and monitor are also set by the constructor,
    // the other two only by you.
    int pin_sender;
    int pin_monitor;
    int pin_crcled;   // CRC status LED. Use this pin for the LED's GND.
    int pin_mirror;   // Data mirror, e.g. for bus activity LED.

    // Delay for 500µs between send/recv cycles.
    // We want to be able to transmit a single message in max 10ms. One message
    // is a zero bit + 11 bits ID + 16 bits data. That means we need a min bitrate
    // of 1+11+16 / 0.010 = 1612 b/s. So for simplicity, we'll operate at 2kbps.
    // That means one bit every 500µs, and since that time is split into two phases
    // each with their own delay(), we'll need to set half that time here.
    // Default: phase_delay = 250
    int phase_delay;

  private:
    unsigned int pmc_state;   // Current state of the state machine.
    unsigned int next_state;  // State to transition to after the current bit.
    unsigned int bits_to_go;  // How many bits left to process in the current state.

    uint16_t crc_calc_buf;    // CRC calculation buffer.
    uint16_t crc_verify_buf;  // Buffer for CRC checksum sent by the sender.
};

#endif
