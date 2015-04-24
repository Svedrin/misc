#include <Charliplexing.h>
#include <Font.h>
#include <Figure.h>

#define STATE_OFF        0
#define STATE_SCROLLTEXT 1

int8_t state;
int8_t currchar, x_offset;
String scrolltext;

void setup() {
  Serial.begin(9600);
  LedSign::Init();
  state = STATE_OFF;
  scrolltext;
}

void loop() {
  if (Serial.available() > 0) {
    boolean cmdprocessed = false;
    String command = Serial.readStringUntil('\n');
    if( command.equals("off") ){
      state = STATE_OFF;
      cmdprocessed = true;
    }
    else if( command.startsWith("scrolltext ") ){
      scrolltext = command.substring(strlen("scrolltext "));
      if( !scrolltext.endsWith(" ") ){
        scrolltext += " ";
      }
      currchar = 0;
      x_offset = DISPLAY_COLS;
      state = STATE_SCROLLTEXT;
      cmdprocessed = true;
    }
    if( cmdprocessed ){
      Serial.println("OK");
    }
    else{
      Serial.println("FAIL");
    }
  }

  LedSign::Clear();

  if( state == STATE_SCROLLTEXT ){
    int8_t drawchar = currchar, len = scrolltext.length();
    for (int8_t x_draw = x_offset; x_draw < DISPLAY_COLS;) {
      x_draw += Font::Draw(scrolltext.charAt(drawchar), x_draw, 0);
      drawchar = (drawchar + 1) % len;
      if(x_draw <= 0){ // off the display even after drawing the letter?
        x_offset = x_draw;
        currchar = drawchar;
      }
    }
    x_offset--;
    delay(80);
  }
}

