# proton-event-logging

A simple include file that exposes proton event details.

I like to add this to disptach, or to proton example C code to
show what proton is doing to the application.

The output is a flood of CSV records that you can import into a spreadsheet
and see the state of the proton event, transport, session, link, and delivery.

One feature is that instead of printing hex addresses (boring, hard to
read and correlate in your head) the code indexes the addresses and then
prints them with a prefix and an index. Link at address 7FFC8000E940 is
'link-1'. A shortcoming of this feature is that if the address gets reused
for another object of the same type then it will still print the first name
even though there is a different object.

The code is set up to use two styles of mutex. You select which style to
use with a #define before the code is added with #include.

Sometimes you want to run with logging and then without. The easiest way
to do this is to short circuit the print statement in the included code with

  #define PRINTF //printf

# How to use

* Define the style of mutex with a #define
* #include "log_obj_namer.inc"
* Find a place to call "log_this_init();" early in your program.
* Call "log_this(event, "some text");" in the event loop.
* Call "log_text("text");" as needed
* Call "log_obj_find_name("log_object (like 'transport')", void* (address of struct))" as needed

Here's an example. echo_srv.c gets the source treatment in patch:

    From 31609e3d394e9738f9693ffa07429e5fcdbb4cfa Mon Sep 17 00:00:00 2001
    From: Chuck Rolke <crolke@redhat.com>
    Date: Thu, 2 Nov 2017 10:21:53 -0400
    Subject: Add event snooping to echo_srv
    
    
    diff --git a/echo_srv.c b/echo_srv.c
    index 09cef17..d6bb52d 100644
    --- a/echo_srv.c
    +++ b/echo_srv.c
    @@ -102,6 +102,9 @@ static inline void unlock(pmutex *m) { pthread_mutex_unlock(m); }
     #endif
     
    +#define MUTEX_PTHREAD 1
    +#include "log_obj_namer.inc"
    +
     pmutex global_mutex;
     
     bool sasl_anon = false;
    @@ -322,6 +325,7 @@ void set_c_context(pn_connection_t *c, connection_context_t *cc) {
     int WINDOW_old=10;            /* Incoming credit window */
     
     static void handle(broker_t* b, pn_event_t* e) {
    +  log_event(e, "ENTRY");
       pn_connection_t *c = pn_event_connection(e);
     
       switch (pn_event_type(e)) {
    @@ -471,6 +475,7 @@ static void handle(broker_t* b, pn_event_t* e) {
        default:
         break;
       }
    +  log_event(e, "EXIT ");
     }
     
     static int ZZZbno = 0;
    @@ -506,6 +511,7 @@ static void usage(const char *arg0) {
     }
     
     int main(int argc, char **argv) {
    +  log_this_init();
       pmutex_init(&global_mutex);
       //  if (getenv("ZZZCW")) WINDOW=atoi(getenv("ZZZCW"));  window maintained to match peer
       /* Command line options */
