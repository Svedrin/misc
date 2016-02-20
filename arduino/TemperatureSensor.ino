//                              0    1    2    3    4    5    6    7     8     9    10
int           centigrade[] = {-40, -30, -20, -10,   0,  10,  20,  25,   30,   40,   50};
unsigned long resistance[] = {562, 617, 677, 740, 807, 877, 951, 990, 1029, 1111, 1196};
unsigned int  num_steps    = sizeof(centigrade)/sizeof(int);

unsigned long rvcc = 5000;
unsigned long rref = 1200;
unsigned long vref = 1200;
unsigned long vcc  =    0;

unsigned int pinref = A5;

void setup() {
  Serial.begin(9600);
}

double toVoltsSimple(unsigned long x){
  // Convert ADC units to a voltage, without any amplification stuff.
  return vcc * x / 1024.0;
}

double toVoltsWithOpAmp(unsigned long x){
  // Convert ADC units to a voltage, reading amplified data.
  // See https://de.wikipedia.org/wiki/Operationsverst%C3%A4rker#Nichtinvertierender_Verst.C3.A4rker_.28Elektrometerverst.C3.A4rker.29
  // The voltage we're reading is the input voltage amplified by v = (1 + rvcc / rref).
  return toVoltsSimple(x) / (1 + (rvcc / (double)rref));
}

double toCentigrade(unsigned long vin){
  // Find the interval we're in
  double vupper;
  double vlower;
  unsigned long rgnd;
  int idx;
  for( idx = 1; idx < num_steps; idx++ ){
    // vupper is the voltage at the upper boundary, vlower the one at the lower boundary.
    rgnd = resistance[idx];
    vupper = vcc * rgnd / (double)(rvcc + rgnd);

    rgnd = resistance[idx - 1];
    vlower = vcc * rgnd / (double)(rvcc + rgnd);

    if(vlower <= vin && vin < vupper){
      break;
    }
  }

  // We're in [idx - 1:idx]. Interpolate where exactly
  double partial = (vin - vlower) / (vupper - vlower);
  int    cupper = centigrade[idx];
  int    clower = centigrade[idx - 1];
  return clower + (partial * (cupper - clower));
}

void readTemp(int analogInPin){
  unsigned long sensorValue = analogRead(analogInPin);

  // print the results to the serial monitor:
  Serial.print("sensor = " );
  Serial.print(sensorValue);
  Serial.print("\t temp = ");
  Serial.print(toCentigrade(toVoltsSimple(sensorValue)));
}

void readTempTheCoolWay(int analogInPin){
  unsigned long sensorValue = analogRead(analogInPin);
  double vin = toVoltsWithOpAmp(sensorValue);

  // print the results to the serial monitor:
  Serial.print("sensor = " );
  Serial.print(sensorValue);
  Serial.print("\t volts = ");
  Serial.print(vin);
  Serial.print("\t temp = ");
  Serial.print(toCentigrade(vin));
}

void loop() {
  vcc = vref * 1024.0 / analogRead(pinref);

  readTemp(A0);
  Serial.print("\t");

  readTemp(A1);
  Serial.print("\t");

  readTempTheCoolWay(A2);
  Serial.println();

  delay(200);
}
