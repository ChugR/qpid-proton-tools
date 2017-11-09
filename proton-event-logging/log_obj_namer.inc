/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
#include <math.h>
#include <sys/time.h>
#include <string.h>

// #include <pthread.h>
// #include <unistd.h>

// To disable printing easily:
// #define PRINTF //printf

#ifndef PRINTF
#define PRINTF printf
#endif

#ifndef fatal
#define fatal PRINTF
#endif

#if defined( MUTEX_PTHREAD )
#define MUTEX_ALLOCATE(X) pthread_mutex_t (X)
#define MUTEX_INIT(X)     pthread_mutex_init(&(X), NULL); 
#define MUTEX_LOCK(X)     pthread_mutex_lock(&(X));
#define MUTEX_UNLOCK(X)   pthread_mutex_unlock(&(X));
#define MUTEX_DESTROY(X)  pthread_mutex_destroy(&(X));

#elif defined( MUTEX_SYS_MUTEX )
#define MUTEX_ALLOCATE(X) sys_mutex_t * (X)
#define MUTEX_INIT(X)     (X) = sys_mutex()
#define MUTEX_LOCK(X)     sys_mutex_lock(X)
#define MUTEX_UNLOCK(X)   sys_mutex_unlock(X)
#define MUTEX_DESTROY(X)  sys_mutex_free(X)

#else
#error "define either MUTEX_PTHREAD or MUTEX_SYS_MUTEX"
#endif

typedef enum DELIVERY_QUERY_ENUM {
    DELIVERY_QUERY_ABSENT,
    DELIVERY_QUERY_FALSE,
    DELIVERY_QUERY_TRUE
    } DELIVERY_QUERY;

/* log object namer - shorter names than addresses */
typedef struct log_obj_namer_s {
    struct log_obj_namer_s *next;
    char                   *name;
    void                   *obj_ptr;
    char                   *longname;
} log_obj_namer_t;


typedef struct log_obj_namers_s {
  MUTEX_ALLOCATE(lock);
  const char      *prefix;
  log_obj_namer_t *obj_namers;
  int              next_id;
} log_obj_namers_t;


log_obj_namers_t *log_obj_namers(const char *prefix) {
    log_obj_namers_t *lon = (log_obj_namers_t *)malloc(sizeof(log_obj_namers_t));
    if (lon == 0)
        fatal("failed to allocate namer for %s" , prefix);
    MUTEX_INIT(lon->lock);
    lon->prefix = prefix;
    lon->obj_namers = 0;
    lon->next_id = 1;
    return lon;
}


const char * delivery_query_show(DELIVERY_QUERY dq) {
    if (dq == DELIVERY_QUERY_ABSENT) return "";
    if (dq == DELIVERY_QUERY_TRUE  ) return "T";
    return "F";
}
    

void log_obj_namers_destroy(log_obj_namers_t *namer) {
    MUTEX_DESTROY(namer->lock);
    // TODO:
}

double log_time_uS(void) {
    // Return a loggable time: SSSS.mmmuuu as a double
    struct timeval tv;
    gettimeofday(&tv, NULL);

    uint64_t t_uS = (tv.tv_sec % 1000) * (uint64_t)1000000 + tv.tv_usec;
    double result = t_uS;
    return result / 1000000.0;
}


/* Event csv logger */
static bool              log_obj_inited = false;
static log_obj_namers_t *log_transports = 0;
static log_obj_namers_t *log_sessions   = 0;
static log_obj_namers_t *log_links      = 0;
static log_obj_namers_t *log_linknames  = 0;
static log_obj_namers_t *log_deliveries = 0;
static log_obj_namers_t *log_msg_content= 0;


void log_this_init(void) {
    if (log_obj_inited) {
        return;
    }
    log_obj_inited = true;

#define PRINT_HEADER
#ifdef PRINT_HEADER
    PRINTF("Time(S), note, event, "
        "xport, maxFrame, "
        "session, incoming_capacty, outgoing_window, incoming_bytes, outgoing_bytes, "
        "link, "
        "linkName, link_is_receiver, max_message_size, remote_max_message_size, "
        "credit, available, queued, unsettled, " 
        "delivery, readable, partial, pending, remote_settled\n");
#endif
    log_transports = log_obj_namers("xport-");
    log_sessions   = log_obj_namers("sessn-");
    log_links      = log_obj_namers("link-");
    log_linknames  = log_obj_namers("linkname-");
    log_deliveries = log_obj_namers("dlvry-");
    log_msg_content= log_obj_namers("content-");
}


/* Given a pointer, return the short name from List
 * or add a new name
 */
const char * log_obj_name_of(log_obj_namers_t *name_pool, void *ptr) {
    MUTEX_LOCK(name_pool->lock);
    log_obj_namer_t *last = 0;
    log_obj_namer_t *curr =  name_pool->obj_namers;
    while (curr) {
        if (curr->obj_ptr == ptr) {
            break;
        }
        last = curr;
        curr = curr->next;
    }
    if (curr == 0) {
        curr = (log_obj_namer_t*)malloc(sizeof(log_obj_namer_t));
        curr->next = 0;
        curr->name = (char *)malloc(strlen(name_pool->prefix) + 20);  // "prefix-" + int-as-string
        if (ptr == (void*)0) {
            curr->name[0] = '\0';
        } else {
            strncpy(curr->name, name_pool->prefix, strlen(name_pool->prefix));
            sprintf(&curr->name[strlen(name_pool->prefix)], "%d", name_pool->next_id++);
            printf("log_obj_name_of mapped address %p to name %s\n", ptr, curr->name);
        }
        curr->obj_ptr = ptr;
        if (last == 0)
            name_pool->obj_namers = curr;
        else
            last->next = curr;
    }
    MUTEX_UNLOCK(name_pool->lock);
    return curr->name;
}


/* Given the name of an object namer and a pointer
 *  return the short name or add a new name.
 * Hack alert, the object namers are named:
 *  transport, session, link, linkname, delivery, and content.
 */
const char * log_obj_find_name(const char *log_obj, void *ptr) {
    if (strcmp(log_obj, "transport") == 0)
        return log_obj_name_of(log_transports, ptr);
    if (strcmp(log_obj, "session") == 0)
        return log_obj_name_of(log_sessions, ptr);
    if (strcmp(log_obj, "link") == 0)
        return log_obj_name_of(log_links, ptr);
    if (strcmp(log_obj, "linkname") == 0)
        return log_obj_name_of(log_linknames, ptr);
    if (strcmp(log_obj, "delivery") == 0)
        return log_obj_name_of(log_deliveries, ptr);
    if (strcmp(log_obj, "content") == 0)
        return log_obj_name_of(log_msg_content, ptr);
    return "Unknown log_obj_find_name log_obj_namer";
}


/* Given a string, return the short name from List
 * or add a new name
 */
const char * log_obj_short_name_of(log_obj_namers_t *name_pool, const char* lname) {
    MUTEX_LOCK(name_pool->lock);
    log_obj_namer_t *last = 0;
    log_obj_namer_t *curr =  name_pool->obj_namers;
    while (curr) {
        if (strcmp(curr->longname, lname) == 0) {
            break;
        }
        last = curr;
        curr = curr->next;
    }
    if (curr == 0) {
        curr = (log_obj_namer_t*)malloc(sizeof(log_obj_namer_t));
        curr->next = 0;
        curr->name = (char *)malloc(strlen(name_pool->prefix) + 20);  // "prefix-" + int-as-string
        if ((void*)lname == (void*)0) {
            curr->name[0] = '\0';
        } else {
            strncpy(curr->name, name_pool->prefix, strlen(name_pool->prefix));
            sprintf(&curr->name[strlen(name_pool->prefix)], "%d", name_pool->next_id++);
        }
        size_t len = strlen(lname) + 1;
        curr->longname = (char *)malloc(len);
        memmove(curr->longname, lname, len);
        if (last == 0)
            name_pool->obj_namers = curr;
        else
            last->next = curr;
        //PRINTF(",MAPPED LINK NAME %s to long name %s\n", curr->name, curr->longname);
    }
    MUTEX_UNLOCK(name_pool->lock);
    return curr->name;
}


void log_text(const char * text) {
    PRINTF("%011.6f, %s\n", log_time_uS(), text);
}

void log_event(pn_event_t *event, const char * note) {

    const char * ename = pn_event_type_name(pn_event_type(event));

    pn_transport_t * xport = pn_event_transport(event);
    uint32_t max_frame = 0;
    if (!!xport) {
        max_frame = pn_transport_get_max_frame(xport);
    }
    
    pn_session_t * sessn = pn_event_session(event);
    size_t incoming_capacity = 0;
    size_t outgoing_window   = 0;
    size_t incoming_bytes    = 0;
    size_t outgoing_bytes    = 0;
    if (!!sessn) {
        incoming_capacity = pn_session_get_incoming_capacity(sessn);
        outgoing_window   = pn_session_get_outgoing_window(sessn);
        incoming_bytes    = pn_session_incoming_bytes(sessn);
        outgoing_bytes    = pn_session_outgoing_bytes(sessn);
    }
    
    pn_link_t * link = pn_event_link(event);
    const char * linkname      = "";
    bool is_rcvr                = true;
    const char * rcvr_status    = "";
    uint64_t max_message        = 0;
    uint64_t remote_max_message = 0;
    pn_delivery_t * dlvry       = 0;
    int credit                  = 0;
    int available               = 0;
    int queued                  = 0;
    int unsettled               = 0;
    if (!!link) {
        linkname           = pn_link_name(link);
        is_rcvr            = pn_link_is_receiver(link);
        rcvr_status        = is_rcvr ? "recvr" : "sendr";
        max_message        = pn_link_max_message_size(link);
        remote_max_message = pn_link_remote_max_message_size(link);
        dlvry              = pn_link_current(link);
        credit             = pn_link_credit(link);
        available          = pn_link_available(link);
        queued             = pn_link_queued(link);
        unsettled          = pn_link_unsettled(link);
    }

    DELIVERY_QUERY is_readable = DELIVERY_QUERY_ABSENT;
    DELIVERY_QUERY is_partial  = DELIVERY_QUERY_ABSENT;
    size_t pending             = 0;
    DELIVERY_QUERY is_settled  = DELIVERY_QUERY_ABSENT;
    if (!!dlvry) {
        is_readable = pn_delivery_readable(dlvry) ? DELIVERY_QUERY_TRUE : DELIVERY_QUERY_FALSE;
        is_partial  = pn_delivery_partial (dlvry) ? DELIVERY_QUERY_TRUE : DELIVERY_QUERY_FALSE;
        pending     = pn_delivery_pending (dlvry);
        is_settled  = pn_delivery_settled (dlvry) ? DELIVERY_QUERY_TRUE : DELIVERY_QUERY_FALSE;
    }

    

    PRINTF("%011.06f, %s, %s, "      /* time, note, eventname */
        "%s, %d, "                   /* transportName, maxframe */
        "%s, %ld, %ld, %ld, %ld, "   /* sessionName, inCap, outWin, inBytes, outBytes */
        "%s, %s, %s, "               /* linkId, linkName, s_or_r */ 
        "%lu, %lu, %d, %d, %d, %d, "  /* maxMsg, rMaxMsg, credit, avail, queued, unsettled */
        "%s, %s, %s, %ld, %s\n",     /* dlvry, readable, partial, pending, settled */
        log_time_uS(), note, ename,
        log_obj_name_of(log_transports, (void*)xport), max_frame,
        log_obj_name_of(log_sessions,   (void*)sessn), incoming_capacity, outgoing_window, incoming_bytes, outgoing_bytes,
        log_obj_name_of(log_links,      (void*)link), 
        log_obj_short_name_of(log_linknames,  linkname), rcvr_status, max_message, remote_max_message, 
        credit, available, queued, unsettled,
        log_obj_name_of(log_deliveries, (void*)dlvry), delivery_query_show(is_readable),
        delivery_query_show(is_partial), pending, delivery_query_show(is_settled)
        );
}
