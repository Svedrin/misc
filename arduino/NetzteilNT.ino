
/* I rebuilt my power supply from scratch, this time using a TLV2371 OpAmp
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

void setup() {
  Serial.begin(9600);
  pinMode(3, OUTPUT);
  pinMode(6, OUTPUT);
}

unsigned long long lasttime = 0;
double wantvolts = 7;

void loop() {
  if( millis() > lasttime + 1000 ){
    lasttime = millis();

    unsigned int analog_val;
    double voltage;
    analog_val = analogRead(A0);

    // ADC:               U2  = x/1023 * 5V
    // Voltage Divider:   VCC = U2 * (R1 + R2) / R2

    voltage = (analog_val / (double)1023.0 * 5) * (1000 + 470) / (double)470.0;

    unsigned int pwm_value;
    if( wantvolts >= voltage ){
      pwm_value = 255;
    }
    else{
      pwm_value = wantvolts / voltage * 255;
    }
    analogWrite(6, pwm_value);
    analogWrite(3, pwm_value);
    Serial.print("Input = ");
    Serial.print(voltage);
    Serial.print("V, setting output to ");
    Serial.println(pwm_value);
  }
}
