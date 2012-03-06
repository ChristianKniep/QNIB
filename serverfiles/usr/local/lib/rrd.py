#!/usr/bin/env python
#
#  rrd.py
#  Simple RRDTool wrapper
#  Copyright (c) 2008 Corey Goldberg (corey@goldb.org)
#
#  Download the Windows version of RRDTool from:
#    http://www.gknw.net/mirror/rrdtool/
# 
#  You may need these fonts if RRDTool throws an error when you graph:
#    http://dejavu.sourceforge.net/wiki/index.php/Main_Page


import os
import time
import subprocess


class RRD(object):
    def __init__(self, file_name, vertical_label='test'):
        self.file_perf = "%s_perf" % file_name
        self.rrd_perf = "/srv/rrd/qnib/%s.rrd" % self.file_perf
        self.png_perf = "/srv/www/qnib/%s.png" % self.file_perf
        self.file_err = "%s_err" % file_name
        self.rrd_err = "/srv/rrd/qnib/%s.rrd" % self.file_err
        self.png_err = "/srv/www/qnib/%s.png" % self.file_err
        self.vertical_label = vertical_label
        self.rrd_color =  {
            'xmit_data':"FF0000",
            'rcv_data':"00FF00",
            'symbol_err_cnt':'FF0000',
            'xmit_discards':'00FF00',
            'vl15_dropped':'0000FF',
            'link_downed':'FF00FF'
            }

    def create_rrd(self, interval):
        self.create_perf(interval)
        self.create_err(interval)

    def create_perf(self, interval):  
        interval = str(interval) 
        interval_mins = float(interval) / 60  
        heartbeat = str(int(interval) * 2)
        ds_arr = [
            'DS:xmit_data:GAUGE:%s:U:U' % heartbeat,
            'DS:rcv_data:GAUGE:%s:U:U' % heartbeat,
            ]
                  
        cmd_create = ['rrdtool', 'create', self.rrd_perf, '--step', interval]
        cmd_create.extend(ds_arr)
        cmd_create.extend([
            'RRA:AVERAGE:0.5:1:%s' % str(int(4000/interval_mins)),
            'RRA:AVERAGE:0.5:%s:800' % str(int(30/interval_mins)),
            'RRA:AVERAGE:0.5:%s:800' % str(int(120/interval_mins)),
            'RRA:AVERAGE:0.5:%s:800' % str(int(1440/interval_mins)),
            ])

        process = subprocess.Popen(cmd_create, shell=False, stdout=subprocess.PIPE)
        process.communicate()
        
    def create_err(self, interval):  
        interval = str(interval) 
        interval_mins = float(interval) / 60  
        heartbeat = str(int(interval) * 2)
        ds_arr = [
            'DS:symbol_err_cnt:GAUGE:%s:U:U' % heartbeat,
            'DS:xmit_discards:GAUGE:%s:U:U' % heartbeat,
            'DS:vl15_dropped:GAUGE:%s:U:U' % heartbeat,
            'DS:link_downed:GAUGE:%s:U:U' % heartbeat
            ]
                  
        cmd_create = ['rrdtool', 'create', self.rrd_err, '--step', interval]
        cmd_create.extend(ds_arr)
        cmd_create.extend([
            'RRA:AVERAGE:0.5:1:%s' % str(int(4000/interval_mins)),
            'RRA:AVERAGE:0.5:%s:800' % str(int(30/interval_mins)),
            'RRA:AVERAGE:0.5:%s:800' % str(int(120/interval_mins)),
            'RRA:AVERAGE:0.5:%s:800' % str(int(1440/interval_mins)),
            ])

        process = subprocess.Popen(cmd_create, shell=False, stdout=subprocess.PIPE)
        process.communicate()

    def update_perf(self, data):
        cmd_update = ['rrdtool', 'update', self.rrd_perf]
        val =  "N:%(xmit_data)s:%(rcv_data)s" % data
        cmd_update.append(val)
        process = subprocess.Popen(cmd_update, shell=False, stdout=subprocess.PIPE)
        process.communicate()
    def update_err(self, data):
        cmd_update = ['rrdtool', 'update', self.rrd_err]
        val =  "N:%(symbol_err_cnt)s:%(xmit_discards)s" % data
        val += ':%(vl15_dropped)s:%(link_downed)s' % data
        cmd_update.append(val)
        process = subprocess.Popen(cmd_update, shell=False, stdout=subprocess.PIPE)
        process.communicate()
    
    def graph(self, mins):
        self.graph_perf(mins)
        self.graph_err(mins)
        
    def graph_perf(self, mins):       
        start_time = 'now-%s' % (mins * 60)  
        end_time = 'now'
        ds_name = 'test'
        width = '400'
        height = '150'
        cmd_graph = ['rrdtool', 'graph', self.png_perf]
        ds_names = ['xmit_data', 'rcv_data']
        for ds_name in ds_names:
            cmd_graph.append('DEF:%s=%s:%s:AVERAGE' % (ds_name, self.rrd_perf, ds_name))
            cmd_graph.append('LINE:%s#%s:%s' % (ds_name, self.rrd_color[ds_name], ds_name))
            cmd_graph.append('VDEF:%slast=%s,LAST' % (ds_name, ds_name))
            cmd_graph.append('VDEF:%savg=%s,AVERAGE' % (ds_name, ds_name))
            #cmd_graph.append('GPRINT:%slast:last=%%6.2lf\n' % ds_name)
        cmd_graph.extend([
                '--title="%s"' % self.rrd_perf,
                '--vertical-label="%s"' % self.vertical_label,
                '--start=%s' % start_time,
                '--end=%s' % end_time,
                '--width=%s' % width,
                '--height=%s' % height,
                '--lower-limit="0"'
                ])
        process = subprocess.Popen(cmd_graph, shell=False, stdout=subprocess.PIPE)
        process.communicate()
    
    def graph_err(self, mins):       
        start_time = 'now-%s' % (mins * 60)  
        end_time = 'now'
        ds_name = 'test'
        width = '400'
        height = '150'
        cmd_graph = ['rrdtool', 'graph', self.png_err]
        ds_names = ['symbol_err_cnt', 'xmit_discards', \
                    'vl15_dropped', 'link_downed']
        for ds_name in ds_names:
            cmd_graph.append('DEF:%s=%s:%s:AVERAGE' % (ds_name, self.rrd_err, ds_name))
            cmd_graph.append('LINE:%s#%s:%s' % (ds_name, self.rrd_color[ds_name], ds_name))
            cmd_graph.append('VDEF:%slast=%s,LAST' % (ds_name, ds_name))
            cmd_graph.append('VDEF:%savg=%s,AVERAGE' % (ds_name, ds_name))
            #cmd_graph.append('GPRINT:%slast:last=%%6.2lf\n' % ds_name)
        cmd_graph.extend([
                '--title="%s"' % self.rrd_err,
                '--vertical-label="%s"' % self.vertical_label,
                '--start=%s' % start_time,
                '--end=%s' % end_time,
                '--width=%s' % width,
                '--height=%s' % height,
                '--lower-limit="0"'
                ])
        process = subprocess.Popen(cmd_graph, shell=False, stdout=subprocess.PIPE)
        process.communicate()
            
            
class RRDException(Exception): pass

