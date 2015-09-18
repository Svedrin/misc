// This sketch is used for controlling a laboratory power supply that consists of:
//
// * An ATmega328, obviously
// * A PCF8591 DAC that
//   * talks to us via I²C
//   * controls the output voltage through an LM741 OpAmp
//   * reads measurements at various places about voltage and current
// * An LM385 reference voltage generator
// * A kill transistor attached to D8 that immediately sets the output voltage to zero.
// * Inspired by http://img.svedr.in/nerdkram/netzteil_schaltplan_dt0001.jpg.html
//
// The serial port is used to configure the output voltage.
// To protect against unwanted AT command execution, all serial input is ignored
// until a = is found, so send one first. Then, configure new voltages by just
// sending values in mV.
//
// The console format is currently intended to be human-readable, but should be
// quite easily parseable by splitting at tabs.
//
// By Michael "Svedrin" Ziegler <ich@michaelziegler.name>.

#include <Wire.h>

unsigned long lastCheck = 0;
unsigned int level = 0;

int i2caddr = (0x90 >> 1);

unsigned long rshunt = 10;  // Ohms of Shunt resistor

// Voltage measurements are done using a voltage divider to reduce the voltage from
// up to 30V to <=5V. rVCC is the resistor going up to VCC, rGND goes to ground.

unsigned long rvcc = 50000; // Ohms of VCC resistor
unsigned long rgnd = 10000; // Ohms of GND resistor
unsigned long vref =  1200; // mV of reference voltage
unsigned long vcc  =     0; // current VCC (calculated from vref)

unsigned int pinref = A3;   // pin to read vref from

unsigned int printedLines = 0;

int ignoreInput = 1;

void setup() {
  Serial.begin(9600);
  Wire.begin();
  pinMode(8, OUTPUT);
}

unsigned long toVolts(unsigned long x){
  unsigned long vx = vcc * x / 255; // Convert to measured volts
  return vx * (rvcc + rgnd) / rgnd; // Convert to actual volts
}

unsigned long toAmps(unsigned long u1, unsigned long u2){
  return abs(u1 - u2) / rshunt;
}

unsigned int toLevel(unsigned long vin){
  unsigned long vx = vin * rgnd / (rvcc + rgnd); // Convert to measured volts
  if( vx > vcc ){
    // Can't output more than 100%
    return 255;
  }
  return vx * 255 / vcc;                         // Convert to level
}

void printVal(int x){
  Serial.print(x);
  Serial.print("=");
  Serial.print(toVolts(x));
  Serial.print("\t");
}

void loop() {
  unsigned long utransistor, uresistor;

  if (Serial.available() > 0) {
    long incomingByte = 0;
    if( ignoreInput == 1 ){
      if( Serial.read() == '=' ){
        ignoreInput = 0;
      }
    }
    else{
      incomingByte = Serial.parseInt();
      if (Serial.available() > 0){
        // Read() away extra characters (e.g., line breaks)
        Serial.read();
      }

      if( incomingByte == 0 ){
        level = 0;
        digitalWrite(8, HIGH);
      }
      else{
        level = toLevel(incomingByte);
        digitalWrite(8, LOW);
      }

      // Send new level over I²C
      Wire.beginTransmission(i2caddr);
      Wire.write(0x40);
      Wire.write(level);
      Wire.endTransmission();
    }
  }

  if( millis() - lastCheck >= 1000 ){
    lastCheck = millis();

    if( printedLines >= 10 ){
      printedLines = 0;
    }
    if( printedLines == 0 ){
      Serial.println("\nState\tVCC\t\tLevel\t\tTransistor\tResistor \tSupply\t\tCurrent");
    }

    if( ignoreInput == 1 ){
      Serial.print("noop\t");
    }
    else{
      Serial.print("ok\t");
    }

    int valref = analogRead(pinref);
    vcc = vref * 1024 / valref;
    Serial.print(valref);
    Serial.print("=");
    Serial.print(vcc);
    Serial.print("\t");

    printVal(level);

    // We have to re-transmit the current level
    Wire.beginTransmission(i2caddr);
    Wire.write(0x44);
    Wire.write(level);
    Wire.endTransmission();

    // First read returns crap
    Wire.requestFrom(i2caddr, 1);
    Wire.read();

    // Voltage after Transistor
    Wire.requestFrom(i2caddr, 1);
    utransistor = Wire.read();
    printVal(utransistor);

    // Voltage after Resistor
    Wire.requestFrom(i2caddr, 1);
    uresistor = Wire.read();
    printVal(uresistor);

    // Voltage of Power Supply
    Wire.requestFrom(i2caddr, 1);
    printVal(Wire.read());

    // Calculate the current
    Serial.print(toAmps(toVolts(utransistor), toVolts(uresistor)));

    Serial.println("");
    printedLines++;
  }
}

