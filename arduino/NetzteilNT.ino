/* kate: space-indent on; indent-width 2; replace-tabs on; hl c++

   I rebuilt my power supply from scratch, this time using a TLV2371 OpAmp
   and a 15kΩ/2.2µF RC circuit powering a BD-311 high load transistor as
   indicated by this guy:

   http://provideyourown.com/2011/analogwrite-convert-pwm-to-voltage/

   To measure VCC, I attached a voltage divider made of a 10kΩ resistor
   to VCC and a 4.7kΩ resistor to GND to the Arduino's port A0 - and
   the freaking math even works out this time omfg!

   NB: I found out that this only worked due to a 10µF capacitor I had
       previously plugged in and then forgotten. Remove it and the ADC
       will return to measuring randomness again. So, better have one
       of those handy.

*/

#include "CanDrive.h"

#define CAN_PIN_SENDER     7
#define CAN_PIN_MONITOR    8

#define PIN_OUT1           3
#define CAN_ID_OUT1      250

#define PIN_OUT2           6
#define CAN_ID_OUT2      251

#define R1 ((double)10000)
#define R2 ((double) 4700)

// #define DEBUG

CanDrive can(CAN_PIN_SENDER, CAN_PIN_MONITOR);

void setup() {
  pinMode(PIN_OUT1, OUTPUT);
  pinMode(PIN_OUT2, OUTPUT);
//   can.pin_mirror =  9;
  can.pin_crcled = 10;
  can.init();
#ifdef DEBUG
  Serial.begin(9600);
#endif
}

unsigned long long lasttime = 0;

double voltage_out1 = 0;
double voltage_out2 = 0;
double vcc;


unsigned int set_pwm_for_voltage(unsigned int pin, double wantvolts){
  // The OpAmp amplifies the voltage we feed to it using:
  // Uout = v * Uin
  // v = 1 + (R1/R2)
  // R1 and R2 being the voltage divider we use for the OpAmp's feedback loop.
  // This means we need to feed the Uin such as:
  // Uin = Uout / v
  double u_in;
  unsigned int pwm_value;
  if( wantvolts >= vcc ){
    pwm_value = 255;
  }
  else{
    u_in = wantvolts / (1 + (R1/R2));
    pwm_value = round(u_in / 5.0 * 255);
  }
  analogWrite(pin, pwm_value);
}

void loop() {
  uint16_t recv_id, recv_val;

  if( millis() > lasttime + 1000 ){
    lasttime = millis();

    unsigned int analog_val;
    analog_val = analogRead(A0);

    // ADC:               U2  = x/1023 * 5V
    // Voltage Divider:   VCC = U2 * (R1 + R2) / R2

    vcc = (analog_val / (double)1023.0 * 5) * (R1 + R2) / R2;

#ifdef DEBUG
    Serial.print("Input = ");
    Serial.print(vcc);
    Serial.print(" OUT1 = ");
    Serial.print(voltage_out1);
    Serial.print(" OUT2 = ");
    Serial.println(voltage_out2);
#endif
  }

  can.handle_message();

  if( can.recv(&recv_id, &recv_val) ){
    if( recv_id == CAN_ID_OUT1 ){
      voltage_out1 = recv_val / (double)1000.0;
      set_pwm_for_voltage(PIN_OUT1, voltage_out1);
    }
    else if( recv_id == CAN_ID_OUT2 ){
      voltage_out2 = recv_val / (double)1000.0;
      set_pwm_for_voltage(PIN_OUT2, voltage_out2);
    }
  }
}
