//                              0    1    2    3    4    5    6    7     8     9    10
int           centigrade[] = {-40, -30, -20, -10,   0,  10,  20,  25,   30,   40,   50};
unsigned long resistance[] = {562, 617, 677, 740, 807, 877, 951, 990, 1029, 1111, 1196};
unsigned int  num_steps    = sizeof(centigrade)/sizeof(int);

unsigned long rvcc = 5000;
unsigned long vref = 1200;
unsigned long vcc  =    0;

unsigned int pinref = A5;

void setup() {
  Serial.begin(9600);
}

float toCentigrade(unsigned long x){
  // Convert ADC units to a voltage
  unsigned long vin = vcc * x / 1024;

  // Find the interval we're in
  unsigned long vupper;
  unsigned long vlower;
  unsigned long rgnd;
  int idx;
  for( idx = 1; idx < num_steps; idx++ ){
    // vupper is the voltage at the upper boundary, vlower the one at the lower boundary.
    rgnd = resistance[idx];
    vupper = vcc * rgnd / (rvcc + rgnd);

    rgnd = resistance[idx - 1];
    vlower = vcc * rgnd / (rvcc + rgnd);

    if(vlower <= vin && vin < vupper){
      break;
    }
  }

  // We're in [idx - 1:idx]. Interpolate where exactly
  float partial = (vin - vlower) / (float)(vupper - vlower);
  int   cupper = centigrade[idx];
  int   clower = centigrade[idx - 1];
  return clower + (partial * (cupper - clower));
}

void readTemp(int analogInPin){
  unsigned long sensorValue = analogRead(analogInPin);

  // print the results to the serial monitor:
  Serial.print("sensor = " );
  Serial.print(sensorValue);
  Serial.print("\t temp = ");
  Serial.print(toCentigrade(sensorValue));
}

void loop() {
  vcc = vref * 1024 / analogRead(pinref);

  readTemp(A0);
  Serial.print("\t");

  readTemp(A1);
  Serial.println();

  delay(200);
}
