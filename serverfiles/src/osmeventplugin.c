/*
 * Copyright (c) 2008 Voltaire, Inc. All rights reserved.
 * Copyright (c) 2007 The Regents of the University of California.
 *
 * This software is available to you under a choice of one of two
 * licenses.  You may choose to be licensed under the terms of the GNU
 * General Public License (GPL) Version 2, available from the file
 * COPYING in the main directory of this source tree, or the
 * OpenIB.org BSD license below:
 *
 *     Redistribution and use in source and binary forms, with or
 *     without modification, are permitted provided that the following
 *     conditions are met:
 *
 *      - Redistributions of source code must retain the above
 *        copyright notice, this list of conditions and the following
 *        disclaimer.
 *
 *      - Redistributions in binary form must reproduce the above
 *        copyright notice, this list of conditions and the following
 *        disclaimer in the documentation and/or other materials
 *        provided with the distribution.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
 * BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
 * ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */

#if HAVE_CONFIG_H
#  include <config.h>
#endif				/* HAVE_CONFIG_H */

#include <errno.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <dlfcn.h>
#include <stdint.h>
#include <complib/cl_qmap.h>
#include <complib/cl_passivelock.h>
#include <opensm/osm_version.h>
#include <opensm/osm_opensm.h>
#include <opensm/osm_log.h>

#include <libpq-fe.h>
/**
 * SQL Foo
 */
void
exit_nicely(PGconn *conn)
{
    PQfinish(conn);
    exit(1);
}


/** =========================================================================
 * This is a simple example plugin which logs some of the events the OSM
 * generates to this interface.
 */
#define SAMPLE_PLUGIN_OUTPUT_FILE "/tmp/osm_sample_event_plugin_output"
typedef struct _log_events {
	FILE *log_file;
	osm_log_t *osmlog;
} _log_events_t;

/** =========================================================================
 */
static void *construct(osm_opensm_t *osm)
{
	_log_events_t *log = malloc(sizeof(*log));
	if (!log)
		return (NULL);

	log->log_file = fopen(SAMPLE_PLUGIN_OUTPUT_FILE, "a+");

	if (!(log->log_file)) {
		osm_log(&osm->log, OSM_LOG_ERROR,
			"Sample Event Plugin: Failed to open output file \"%s\"\n",
			SAMPLE_PLUGIN_OUTPUT_FILE);
		free(log);
		return (NULL);
	}

	log->osmlog = &osm->log;
	return ((void *)log);
}

/** =========================================================================
 */
static void destroy(void *_log)
{
	_log_events_t *log = (_log_events_t *) _log;
	fclose(log->log_file);
	free(log);
}

/** =========================================================================
 */
static void handle_port_counter(_log_events_t * log, osm_epi_pe_event_t * pc)
{
    /* SQL-Connection start */
    const char *conninfo;
    static PGconn     *conn = 0;
    PGresult   *res;

    conninfo = "dbname = qnib user = postgres";

    // Make a connection to the database 
    if (conn==0) {
	conn = PQconnectdb(conninfo);
    }
    // Check to see that the backend connection was successfully made 
    if (PQstatus(conn) != CONNECTION_OK) {
        fprintf(stderr, "Connection to database failed: %s",
                PQerrorMessage(conn));
        //exit_nicely(conn);
	PQfinish(conn);
	conn = PQconnectdb(conninfo);
        if (PQstatus(conn) != CONNECTION_OK) {
            fprintf(stderr, "Failed to reconnect, abort!: %s",
                PQerrorMessage(conn));
	    exit_nicely(conn);
	}
    }
    // SQL-Connect end 
    unsigned char str[1024];
    /** !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
     *  Die Werte sind nicht pro Sekunde!!
     *  Kommt auf das Interval der Auswertung an
     * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
     */
	sprintf(str,"SELECT * FROM osmInsertTuple('%" PRIx64 "', '%d', '%ld','symbol_err_cnt', '%ld', 'xmit_discards', '%ld','vl15_dropped', '%ld', 'link_downed', '%ld');\n""",
			pc->port_id.node_guid, pc->port_id.port_num, pc->time_diff_s,
			pc->symbol_err_cnt, pc->xmit_discards, pc->vl15_dropped,
			pc->link_downed);
	res = PQexec(conn, str);
	//fprintf(log->log_file,str);
}

/** =========================================================================
 */
static void
handle_port_counter_ext(_log_events_t * log, osm_epi_dc_event_t * epc)
{
    // SQL-Connection start 
    const char *conninfo;
    static PGconn     *conn = 0;
    PGresult   *res;

    conninfo = "dbname = qnib user = postgres";

    // Make a connection to the database 
    if (conn==0) {
	conn = PQconnectdb(conninfo);
    }
    // Check to see that the backend connection was successfully made 
    if (PQstatus(conn) != CONNECTION_OK) {
        fprintf(stderr, "Connection to database failed: %s",
                PQerrorMessage(conn));
        //exit_nicely(conn);
		PQfinish(conn);
		conn = PQconnectdb(conninfo);
        if (PQstatus(conn) != CONNECTION_OK) {
            fprintf(log->log_file, "Failed to reconnect, abort\n");
	    exit_nicely(conn);
		}
    }
    // SQL-Connect end 
    unsigned char str[1024];
    // !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    //  Die Werte sind nicht pro Sekunde!!
    //  Kommt auf das Interval der Auswertung an
    // !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
	
	sprintf(str,"SELECT * FROM osmInsertTuple('%" PRIx64 "', '%d', '%ld', 'xmit_data', '%ld', 'rcv_data', '%ld');\n",
		epc->port_id.node_guid, epc->port_id.port_num, epc->time_diff_s,
		epc->xmit_data*4/(1024*1024), epc->rcv_data*4/(1024*1024));
	res = PQexec(conn, str);
	//fprintf(log->log_file,str);
}

/** =========================================================================
 */
static void handle_port_select(_log_events_t * log, osm_epi_ps_event_t * ps)
{
	if (ps->xmit_wait > 0) {
		fprintf(log->log_file,
			"Port select Xmit Wait counts for node 0x%" PRIx64
			" (%s) port %d\n", ps->port_id.node_guid,
			ps->port_id.node_name, ps->port_id.port_num);
	}
}

/** =========================================================================
 */
static void handle_trap_event(_log_events_t *log, ib_mad_notice_attr_t *p_ntc)
{
    // SQL-Connection start 
    const char *conninfo;
    static PGconn     *conn = 0;
    PGresult   *res;

    conninfo = "dbname = qnib user = postgres";

    // Make a connection to the database 
    if (conn==0) {
	conn = PQconnectdb(conninfo);
    }
    // Check to see that the backend connection was successfully made 
    if (PQstatus(conn) != CONNECTION_OK) {
        fprintf(stderr, "Connection to database failed: %s",
                PQerrorMessage(conn));
        //exit_nicely(conn);
		PQfinish(conn);
		conn = PQconnectdb(conninfo);
        if (PQstatus(conn) != CONNECTION_OK) {
            fprintf(log->log_file, "Failed to reconnect, abort\n");
	    exit_nicely(conn);
		}
    }
	if (ib_notice_is_generic(p_ntc)) {
		fprintf(log->log_file,
			"Generic trap type %d; event %d; from LID 0x%x\n",
			ib_notice_get_type(p_ntc),
			cl_ntoh16(p_ntc->g_or_v.generic.trap_num),
			cl_ntoh16(p_ntc->issuer_lid));

			unsigned char str[1024];
			sprintf(str,"INSERT INTO traps (trap_type, trap_event, trap_lid) VALUES (%d, %d, %d);\n",
				ib_notice_get_type(p_ntc),
				cl_ntoh16(p_ntc->g_or_v.generic.trap_num),
				cl_ntoh16(p_ntc->issuer_lid));
			fprintf(log->log_file,str);
			res = PQexec(conn, str);
	} else {
		fprintf(log->log_file,
			"Vendor trap type %d; from LID 0x%x\n",
			ib_notice_get_type(p_ntc),
			cl_ntoh16(p_ntc->issuer_lid));
			unsigned char str[1024];
			sprintf(str,"INSERT INTO traps (trap_type, trap_lid) VALUES (%d, %d);\n",
				ib_notice_get_type(p_ntc),
				cl_ntoh16(p_ntc->issuer_lid));
			res = PQexec(conn, str);
			fprintf(log->log_file,str);
	}

}

/** =========================================================================
 */
// I would like to have the connection as an argument that is initialized outside
// of this plugin... So that the callback does not have to check it over and over again
static void report(void *_log, osm_epi_event_id_t event_id, void *event_data)
{
	_log_events_t *log = (_log_events_t *) _log;

	switch (event_id) {
	case OSM_EVENT_ID_PORT_ERRORS:
		handle_port_counter(log, (osm_epi_pe_event_t *) event_data);
		break;
	case OSM_EVENT_ID_PORT_DATA_COUNTERS:
		handle_port_counter_ext(log, (osm_epi_dc_event_t *) event_data);
		break;
	case OSM_EVENT_ID_PORT_SELECT:
		handle_port_select(log, (osm_epi_ps_event_t *) event_data);
		break;
	case OSM_EVENT_ID_TRAP:
		handle_trap_event(log, (ib_mad_notice_attr_t *) event_data);
		break;
	case OSM_EVENT_ID_SUBNET_UP:
		fprintf(log->log_file, "Subnet up reported...\n");
		break;
	case OSM_EVENT_ID_MAX:
	default:
		osm_log(log->osmlog, OSM_LOG_ERROR,
			"Unknown event (%d) reported to plugin\n", event_id);
	}
	fflush(log->log_file);
}

/** =========================================================================
 * Define the object symbol for loading
 */

#if OSM_EVENT_PLUGIN_INTERFACE_VER != 2
#error OpenSM plugin interface version missmatch
#endif

osm_event_plugin_t osm_event_plugin = {
      osm_version:OSM_VERSION,
      create:construct,
      delete:destroy,
      report:report
};
