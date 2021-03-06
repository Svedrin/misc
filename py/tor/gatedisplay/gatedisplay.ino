#include <avr/pgmspace.h>
#include <Charliplexing.h>
#include <Font.h>
#include <Figure.h>

#define STATE_OFF        0
#define STATE_SCROLLTEXT 1
#define STATE_FILL       2
#define STATE_COUNTDOWN  3
#define STATE_ARROWUP    4
#define STATE_ARROWDOWN  5
#define STATE_BLOCKED    6

int8_t state;
int8_t currchar, x_offset;
String scrolltext;

long fill_xfrom;
long fill_xto;
long fill_yfrom;
long fill_yto;

unsigned long countdown_last_update = 0;
long seconds;

const unsigned char arrow[9][14] PROGMEM = {
  { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },
  { 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0 },
  { 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0 },
  { 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0 },
  { 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0 },
  { 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0 },
  { 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0 },
  { 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0 },
  { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },
};

uint8_t arrow_row_offset;
boolean arrow_move = false;

const unsigned char blocked[9][14] PROGMEM = {
  { 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0 },
  { 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0 },
  { 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0 },
  { 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0 },
  { 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0 },
  { 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0 },
  { 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0 },
  { 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0 },
  { 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0 },
};

const char helptext[] PROGMEM = ""
  "Commands:\n"
  "help                -- display this help message\n"
  "off                 -- clear the display\n"
  "scrolltext [text]   -- display [text] as a scrolling marquee\n"
  "filltop [rows]      -- light up the top n rows\n"
  "fillbtm [rows]      -- light up the bottom n rows\n"
  "filllft [columns]   -- light up the left n columns\n"
  "fillrgt [columns]   -- light up the right n columns\n"
  "countdown [seconds] -- count down from n seconds to 0 (max 99 seconds)\n"
  "arrowmoveup         -- display an upward-facing scrolling arrow\n"
  "arrowup             -- display an upward-facing fixed arrow\n"
  "arrowmovedown       -- display a downward-facing scrolling arrow\n"
  "arrowdown           -- display a downward-facing fixed arrow\n"
  "blocked             -- display the \"blocked\" picture\n"
  "\n"
  "Commands are acknowledged with OK.\n"
  "Failures are indicated with FAIL.\n"
  "Commands are processed every 100ms.\n"
  "Commands should be terminated with \\n only.\n";


void setup() {
  Serial.begin(9600);
  LedSign::Init();
  state = STATE_OFF;
}

void loop() {
  if (Serial.available() > 0) {
    boolean cmdprocessed = false;
    String command = Serial.readStringUntil('\n');
    if( command.endsWith("\r") ){
      command.replace("\r", "");
    }
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
      if( seconds > 99 ) seconds = 99;
      countdown_last_update = 0;
      state = STATE_COUNTDOWN;
      cmdprocessed = true;
    }
    else if( command.equals("arrowmoveup") ){
      arrow_row_offset = 0;
      arrow_move = true;
      state = STATE_ARROWUP;
      cmdprocessed = true;
    }
    else if( command.equals("arrowup") ){
      arrow_row_offset = 0;
      arrow_move = false;
      state = STATE_ARROWUP;
      cmdprocessed = true;
    }
    else if( command.equals("arrowmovedown") ){
      arrow_row_offset = 0;
      arrow_move = true;
      state = STATE_ARROWDOWN;
      cmdprocessed = true;
    }
    else if( command.equals("arrowdown") ){
      arrow_row_offset = 0;
      arrow_move = false;
      state = STATE_ARROWDOWN;
      cmdprocessed = true;
    }
    else if( command.equals("blocked") ){
      state = STATE_BLOCKED;
      cmdprocessed = true;
    }
    else if( command.equals("help") ){
      char buffer[33];
      for( int i = 0; i < strlen(helptext); i+= 32 ){
        strncpy_PF(buffer, (uint_farptr_t)(helptext + i), 32);
        buffer[32] = 0;
        Serial.print(buffer);
      }
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
    int drawchar = currchar, len = scrolltext.length();
    for (int8_t x_draw = x_offset; x_draw < DISPLAY_COLS;) {
      x_draw += Font::Draw(scrolltext.charAt(drawchar), x_draw, 0);
      drawchar = (drawchar + 1) % len;
      if(x_draw <= 0){ // off the display even after drawing the letter?
        x_offset = x_draw;
        currchar = drawchar;
      }
    }
    x_offset--;
  }
  else if( state == STATE_FILL ){
    for( int8_t y = 0; y < DISPLAY_ROWS; y++ ){
      for( int8_t x = 0; x < DISPLAY_COLS; x++ ){
        LedSign::Set(x, y, x >= fill_xfrom && x < fill_xto && y >= fill_yfrom && y < fill_yto);
      }
    }
  }
  else if( state == STATE_COUNTDOWN ){
    if( millis() - countdown_last_update >= 1000 ){
      countdown_last_update = millis();
      LedSign::Clear();
      Serial.print("t=");
      Serial.println(seconds);
      if( seconds > 0 ){
        if( seconds > 9 ){
          Font::Draw('0' + seconds / 10, 2, 0);
          Font::Draw('0' + seconds % 10, 8, 0);
        }
        else{
          Font::Draw('0' + seconds, 5, 0);
        }
        seconds--;
      }
      else{
        state = STATE_OFF;
      }
    }
  }
  else if( state == STATE_ARROWUP || state == STATE_ARROWDOWN ){
    for( int8_t y = 0; y < DISPLAY_ROWS; y++ ){
      for( int8_t x = 0; x < DISPLAY_COLS; x++ ){
        unsigned char px = pgm_read_byte_near(&(arrow[y][x]));
        if( state == STATE_ARROWDOWN )
          LedSign::Set(x, (y + arrow_row_offset) % DISPLAY_ROWS, px );
        if( state == STATE_ARROWUP )
          LedSign::Set(x, DISPLAY_ROWS - 1 - ((y + arrow_row_offset) % DISPLAY_ROWS), px);
      }
    }
    if( arrow_move )
      arrow_row_offset = (arrow_row_offset + 1) % DISPLAY_ROWS;
  }
  else if( state == STATE_BLOCKED ){
    for( int8_t y = 0; y < DISPLAY_ROWS; y++ ){
      for( int8_t x = 0; x < DISPLAY_COLS; x++ ){
        unsigned char px = pgm_read_byte_near(&(blocked[y][x]));
        LedSign::Set(x, y, px);
      }
    }
  }
  delay(100);
}

