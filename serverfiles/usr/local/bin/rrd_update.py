#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of QNIB.  QNIB is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Christian Kniep, 2012
# Inspired by the Work of Corey due to his rrd.py-Examplelibrary:
# http://code.google.com/p/rrdpy/
## Copyright (c) 2008 Corey Goldberg (corey@goldb.org)

import sys
import os
import time
sys.path.append('/root/QNIB/serverfiles/usr/local/lib')
import rrd
import dbCon
import libTopology


class MYparameter(libTopology.Parameter):
    def default(self):
        # Default-Options
        self.parser.add_option("-d",
            action="count",
            dest="debug",
            help="increases debug [default:None, -d:1, -ddd: 3]")
        self.parser.add_option("-c", dest="cfgfile",
            default="/root/QNIB/serverfiles/usr/local/etc/default.cfg",
            action = "store", help = "Configfile (default: %default)")
        self.parser.add_option("--loop", dest="loop", default=False,
            action = "store_true", help = "Loop the script")
        self.parser.add_option("--delay", dest="loop_delay", default=11,
            action = "store",
            help = "Delay in seconds if loop is set (default: %default)")


def update_err(opt, datab, interval):
    ## Err
    query = """SELECT   pd_id, n_name, p_ext, EXTRACT(EPOCH FROM pdat_time),
                        pk_name, pdat_val
                FROM perfdata   NATURAL JOIN perfkeys
                        NATURAL JOIN ports
                        NATURAL JOIN nodes
                WHERE pk_name in (
                    'symbol_err_cnt', 'xmit_discards',
                    'vl15_dropped', 'link_downed'
                    )
                ORDER BY pd_id ASC LIMIT 500"""
    res = datab.sel(query)
    data = {}
    pd_ids = []
    count_res = len(res)
    if count_res == 0:
        return count_res
    for row in res:
        (pd_id, n_name, p_ext, pdat_time, pk_name, pdat_val) = row
        pd_ids.append(str(pd_id))
        time_s = int(pdat_time)
        if n_name not in data.keys():
            data[n_name] = {}
        if p_ext not in data[n_name].keys():
            data[n_name][p_ext] = {}
        if time_s not in data[n_name][p_ext].keys():
            data[n_name][p_ext][time_s] = {}
        data[n_name][p_ext][time_s][pk_name] = pdat_val
    query = "DELETE FROM perfdata WHERE pd_id in ('%s')" % "','".join(pd_ids)
    datab.exe(query)
    
    for node, ports in data.items():
        for p_ext, time_stamps in ports.items():
            rrd_file = "%s_%s" % (node, p_ext)
            my_rrd = rrd.RRD(node, p_ext)
            stamps = time_stamps.keys()
            stamps.sort()
            my_rrd.create_err(interval, p_ext, stamps[0])
            ins = data[node][p_ext]
            my_rrd.update_err(p_ext, ins)
    return count_res

def update_perf(opt, datab, interval):
    ## Perf
    query = """SELECT   pd_id, n_name, p_ext, EXTRACT(EPOCH FROM pdat_time),
                        pk_name, pdat_val
                FROM perfdata   NATURAL JOIN perfkeys
                        NATURAL JOIN ports
                        NATURAL JOIN nodes
                WHERE   pk_name in ('xmit_data', 'rcv_data')
                ORDER BY pd_id ASC LIMIT 1000"""
    res = datab.sel(query)
    data = {}
    pd_ids = []
    count_res = len(res)
    if count_res == 0:
        return count_res
    for row in res:
        (pd_id, n_name, p_ext, pdat_time, pk_name, pdat_val) = row
        pd_ids.append(str(pd_id))
        time_s = int(pdat_time)
        if n_name not in data.keys():
            data[n_name] = {}
        if p_ext not in data[n_name].keys():
            data[n_name][p_ext] = {}
        if time_s not in data[n_name][p_ext].keys():
            data[n_name][p_ext][time_s] = {}
        data[n_name][p_ext][time_s][pk_name] = pdat_val
    query = "DELETE FROM perfdata WHERE pd_id in ('%s')" % "','".join(pd_ids)
    datab.exe(query)
    
    for node, ports in data.items():
        for p_ext, time_stamps in ports.items():
            my_rrd = rrd.RRD(node, p_ext)
            stamps = time_stamps.keys()
            stamps.sort()
            my_rrd.create_perf(interval, p_ext, stamps[0])
            ins = data[node][p_ext]
            my_rrd.update_perf(p_ext, ins)
    return count_res


def main(argv=None):
    opt = MYparameter(argv)
    opt.check()
    
    while True:
        datab = dbCon.dbCon(opt)
        interval = 10
        count_res = 1
        while count_res > 0:
            count_res = update_perf(opt, datab, interval)
        count_res = 1
        while count_res > 0:
            count_res = update_err(opt, datab, interval)
        if not opt.loop:
            break
        time.sleep(int(opt.loop_delay))
            
    
if __name__ == "__main__":
    main()
