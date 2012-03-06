#!/usr/bin/env python
#  Copyright (c) 2008 Corey Goldberg (corey@goldb.org)
#
#  Create RRD

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


def main(argv=None):
    opt = MYparameter(argv)
    opt.check()
    
    datab = dbCon.dbCon(opt)
    interval = 10
    
    
    
    query = """SELECT   n_name, p_ext, EXTRACT(EPOCH FROM pdat_time),
                        pk_name, pdat_val
                FROM perfdata   NATURAL JOIN perfkeys
                        NATURAL JOIN ports
                        NATURAL JOIN nodes;"""
    res = datab.sel(query)
    data = {}
    for row in res:
        (n_name, p_ext, pdat_time, pk_name, pdat_val) = row
        if n_name not in data.keys():
            data[n_name] = {}
        if p_ext not in data[n_name].keys():
            data[n_name][p_ext] = {}
        data[n_name][p_ext][pk_name] = {'ts':pdat_time, 'val':pdat_val}
    
    for node, ports in data.items():
        for p_ext, perfkeys in ports.items():
            rrd_file = "%s_%s" % (node,p_ext)
            my_rrd = rrd.RRD(rrd_file)
            if not os.path.exists(rrd_file):
                my_rrd.create_rrd(interval)
            ins =  {
                'xmit_data':0,
                'rcv_data':0,
                'symbol_err_cnt':0,
                'xmit_discards':0,
                'vl15_dropped':0,
                'link_downed':0
                }
            for key, val in perfkeys.items():
                ins[key] = val['val']

            my_rrd.update_perf(ins)
            my_rrd.update_err(ins)
     
    
if __name__ == "__main__":
    main()
