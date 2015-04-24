#include <Charliplexing.h>
#include <Font.h>
#include <Figure.h>

#define STATE_OFF        0
#define STATE_SCROLLTEXT 1
#define STATE_FILL       2
#define STATE_COUNTDOWN  3

int8_t state;
int8_t currchar, x_offset;
String scrolltext;

long fill_xfrom;
long fill_xto;
long fill_yfrom;
long fill_yto;

long seconds;

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
      scrolltext.toUpperCase();
      if( !scrolltext.endsWith(" ") ){
        scrolltext += " ";
      }
      currchar = 0;
      x_offset = DISPLAY_COLS;
      state = STATE_SCROLLTEXT;
      cmdprocessed = true;
    }
    else if( command.startsWith("filltop ") ){
      fill_xfrom = 0;
      fill_xto = DISPLAY_COLS;
      fill_yfrom = 0;
      fill_yto = command.substring(strlen("filltop ")).toInt();
      state = STATE_FILL;
      cmdprocessed = true;
    }
    else if( command.startsWith("fillbtm ") ){
      fill_xfrom = 0;
      fill_xto = DISPLAY_COLS;
      fill_yfrom = DISPLAY_ROWS - command.substring(strlen("fillbtm ")).toInt();
      fill_yto = DISPLAY_ROWS;
      state = STATE_FILL;
      cmdprocessed = true;
    }
    else if( command.startsWith("filllft ") ){
      fill_xfrom = 0;
      fill_xto = command.substring(strlen("filllft ")).toInt();
      fill_yfrom = 0;
      fill_yto = DISPLAY_ROWS;
      state = STATE_FILL;
      cmdprocessed = true;
    }
    else if( command.startsWith("fillrgt ") ){
      fill_xfrom = DISPLAY_COLS - command.substring(strlen("fillrgt ")).toInt();
      fill_xto = DISPLAY_COLS;
      fill_yfrom = 0;
      fill_yto = DISPLAY_ROWS;
      state = STATE_FILL;
      cmdprocessed = true;
    }
    else if( command.startsWith("countdown ") ){
      seconds = command.substring(strlen("countdown ")).toInt();
      state = STATE_COUNTDOWN;
      cmdprocessed = true;
    }
    if( cmdprocessed ){
      Serial.println("OK");
    }
    else{
      Serial.println("FAIL");
    }
  }

  if( state == STATE_OFF ){
    LedSign::Clear();
  }
  else if( state == STATE_SCROLLTEXT ){
    LedSign::Clear();
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
  else if( state == STATE_FILL ){
    for( int8_t y = 0; y < DISPLAY_ROWS; y++ ){
      for( int8_t x = 0; x < DISPLAY_COLS; x++ ){
        LedSign::Set(x, y, x >= fill_xfrom && x < fill_xto && y >= fill_yfrom && y < fill_yto);
      }
    }
  }
  else if( state == STATE_COUNTDOWN ){
    for(; seconds > 0; seconds--){
      LedSign::Clear();
      Font::Draw('0' + seconds, 5, 0);
      Serial.println(seconds);
      delay(1000);
    }
    Serial.println("0");
    state = STATE_OFF;
  }
}

