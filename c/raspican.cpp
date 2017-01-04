/* kate: space-indent on; indent-width 2; replace-tabs on; hl c++

  g++ raspican.cpp -o raspican -lCanDrive -lwiringPi

*/

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <sched.h>
#include <sys/mman.h>
#include <CanDrive.h>

#define MY_PRIORITY 49

#define CAN_PIN_SENDER     2
#define CAN_PIN_MONITOR    3

CanDrive can(CAN_PIN_SENDER, CAN_PIN_MONITOR);

void setup() {
  wiringPiSetup();

//   piHiPri(10);

  /* see https://rt.wiki.kernel.org/index.php/RT_PREEMPT_HOWTO#A_Realtime_.22Hello_World.22_Example */

  struct sched_param param;

  /* Declare ourself as a real time task */

  param.sched_priority = MY_PRIORITY;
  if(sched_setscheduler(0, SCHED_FIFO, &param) == -1) {
    perror("sched_setscheduler failed");
    exit(-1);
  }

  /* Lock memory */

  if(mlockall(MCL_CURRENT|MCL_FUTURE) == -1) {
    perror("mlockall failed");
    exit(-2);
  }

  can.pin_crcled = 6;
  can.pin_mirror = 7;
  can.init();
}

void loop() {
  uint16_t recv_id, recv_val;

  can.handle_message();

  if( can.recv(&recv_id, &recv_val) ){
      printf( "%d: %d\n", recv_id, recv_val );
  }
}

int main(int argc, char** argv){
  setup();
  while(TRUE){
    loop();
  }
}
