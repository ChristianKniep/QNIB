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


class RRD(object):
    def __init__(self, rrd_name, vertical_label='test'):     
        self.rrd_name = rrd_name
        self.vertical_label = vertical_label

    def create_rrd(self, interval):  
        interval = str(interval) 
        interval_mins = float(interval) / 60  
        heartbeat = str(int(interval) * 2)
        ds_string = ' DS:test:GAUGE:%s:U:U' % heartbeat
        cmd_create = ''.join((
            'rrdtool create ', self.rrd_name, ' --step ', interval, ds_string,
            ' RRA:AVERAGE:0.5:1:', str(int(4000 / interval_mins)),
            ' RRA:AVERAGE:0.5:', str(int(30 / interval_mins)), ':800',
            ' RRA:AVERAGE:0.5:', str(int(120 / interval_mins)), ':800',
            ' RRA:AVERAGE:0.5:', str(int(1440 / interval_mins)), ':800',
            ))
        cmd = os.popen4(cmd_create)
        cmd_output = cmd[1].read()
        for fd in cmd: fd.close()
        if len(cmd_output) > 0:
            raise RRDException, 'Unable to create RRD: ' + cmd_output
  
  
    def update(self, *values):   
        values_args = ''.join([str(value) + ':' for value in values])[:-1]
        cmd_update = 'rrdtool update %s N:%s' % (self.rrd_name, values_args)
        cmd = os.popen4(cmd_update)
        cmd_output = cmd[1].read()
        for fd in cmd: fd.close()
        if len(cmd_output) > 0:
            raise RRDException, 'Unable to update RRD: ' + cmd_output
    
    
    def graph(self, mins):       
        start_time = 'now-%s' % (mins * 60)  
        output_filename = self.rrd_name + '.png'
        end_time = 'now'
        ds_name = 'test'
        width = '400'
        height = '150'
        cur_date = time.strftime('%m/%d/%Y %H\:%M\:%S', time.localtime())       
        cmd_graph = 'rrdtool graph ' + output_filename + \
            ' DEF:' + ds_name + '=' + self.rrd_name + ':' + ds_name + ':AVERAGE' + \
            ' AREA:' + ds_name + '#FF0000' + \
            ' VDEF:' + ds_name + 'last=' + ds_name + ',LAST' + \
            ' VDEF:' + ds_name + 'avg=' + ds_name + ',AVERAGE' + \
            ' COMMENT:"' + cur_date + '"' + \
            ' GPRINT:' + ds_name + 'avg:"                         average=%6.2lf%S"' + \
            ' --title="' + self.rrd_name +'"' + \
            ' --vertical-label="' + self.vertical_label + '"' \
            ' --start=' + start_time + \
            ' --end=' + end_time + \
            ' --width=' + width + \
            ' --height=' + height + \
            ' --lower-limit="0"'
        cmd = os.popen4(cmd_graph)
        for fd in cmd: fd.close()
            
            
class RRDException(Exception): pass

