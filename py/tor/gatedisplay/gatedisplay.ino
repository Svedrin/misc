#include <Charliplexing.h>
#include <Font.h>
#include <Figure.h>

int8_t currchar, x_offset;

void setup() {
  Serial.begin(9600);
  LedSign::Init();
  currchar = 0;
  x_offset = DISPLAY_COLS;
}

static const char test[] = "HELLO WORLD! ";

void loop() {
  LedSign::Clear();
  int8_t drawchar = currchar;
  for (int8_t x_draw = x_offset; x_draw < DISPLAY_COLS;) {
    x_draw += Font::Draw(test[drawchar], x_draw, 0);
    drawchar = (drawchar + 1) % strlen(test);
    if(x_draw <= 0){ // off the display even after drawing the letter?
      x_offset = x_draw;
      currchar = drawchar;
    }
  }
  delay(80);
  x_offset--;
}

