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
import re

def exp2int(zahl):
    if zahl in ('0','-nan'):
        return 0
    else:
        reg = '(\d+),(\d+)e\+(\d+)'
        mat = re.search(reg,zahl)
        if mat:
            (pre, post, exp) = mat.groups()
            return int((float(pre)+float(".%s" % post))*(10**int(exp)))

class RRD(object):
    def __init__(self, node, p_ext, vertical_label='test'):
        self.node_name = node
        file_name = "%s_%s" % (node, p_ext)
        self.file_perf = "%s_perf" % file_name
        self.rrd_perf = "/srv/rrd/qnib/%s.rrd" % self.file_perf
        self.html_file = "/srv/www/qnib/%s.html" % node
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

    def create_perf(self, interval, start=None):  
        if os.path.exists(self.rrd_perf):
            return
        else:
            print self.file_perf
        interval = str(interval) 
        interval_mins = float(interval) / 60
        heartbeat = str(int(interval) * 2)
        ds_arr = [
            'DS:xmit_data:GAUGE:%s:U:U' % heartbeat,
            'DS:rcv_data:GAUGE:%s:U:U' % heartbeat,
            ]
                  
        cmd_create = ['rrdtool', 'create', self.rrd_perf, '--step', interval]
        if start != None:
            cmd_create.extend([
                '--start',
                str(start-int(interval))
            ])
        cmd_create.extend(ds_arr)
        cmd_create.extend([
            'RRA:AVERAGE:0.5:30:3600'
            ])
        process = subprocess.Popen(cmd_create, shell=False, stdout=subprocess.PIPE)
        process.communicate()
        
    def create_err(self, interval, start=None):  
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
        if start != None:
            cmd_create.extend([
                '--start',
                str(start-int(interval))
            ])
        cmd_create.extend(ds_arr)
        cmd_create.extend([
            'RRA:AVERAGE:0.5:30:3600'
            ])

        process = subprocess.Popen(cmd_create, shell=False, stdout=subprocess.PIPE)
        process.communicate()

    def update_perf(self, ins):
        cmd_update = ['rrdtool', 'update', self.rrd_perf]
        stamps = ins.keys()
        stamps.sort()
        for stamp in stamps:
            val =  str(stamp)
            val += ":%(xmit_data)s:%(rcv_data)s" % ins[stamp]
            cmd_update.append(val)
        process = subprocess.Popen(cmd_update, shell=False, stdout=subprocess.PIPE)
        process.communicate()
    
    def update_err(self, ins):
        cmd_update = ['rrdtool', 'update', self.rrd_err]
        stamps = ins.keys()
        stamps.sort()
        for stamp in stamps:
            val =  str(stamp)
            val +=  ":%(symbol_err_cnt)s:%(xmit_discards)s" % ins[stamp]
            val += ':%(vl15_dropped)s:%(link_downed)s' % ins[stamp]
            cmd_update.append(val)
        process = subprocess.Popen(cmd_update, shell=False, stdout=subprocess.PIPE)
        process.communicate()
    
    def html5(self, mins):
        self.html_code = """<!DOCTYPE HTML>
<html>
    <head>
      <link rel="stylesheet" href="css/combined.css"/>
      <script src="js/jquery.min.js"></script>
      <script src="js/visualize.jQuery.js"></script>
      <script>
        $(function(){
          $('table.line').visualize({type: 'line', parseDirection:'y'});
         });
      </script>
    </head>
    <body>
"""
        self.html5_perf(mins)
        self.html5_err(mins)

        self.html_code += """
    </body>
</html>
"""
        file_d = open(self.html_file, "w")
        file_d.write(self.html_code)
        file_d.close()
        
    def html5_perf(self, mins):
        start_time = 'now-%s' % (mins * 60)  
        start_time = '1331398900-%s' % (mins * 60)  
        end_time = '1331398900'
        #end_time = 'now'
        
        cmd_html = ['rrdtool', 'fetch', self.rrd_perf,
                    '-s',start_time,'-e',end_time,'AVERAGE']
        process = subprocess.Popen(cmd_html, shell=False, stdout=subprocess.PIPE)

        (out, errc) = process.communicate()
        self.html_code2 = """
        <table class="line" style="display:none;">
          <caption>Performance %s</caption>
          <thead>
            <tr>
              <td></td>
              <th>Symbol ErrCnt</th>
              <th>Xmit Discards</th>
              <th>VL15 dropped</th>
              <th>Link downed</th>
            </tr>
          </thead>
          <tbody>""" % self.node_name
        self.html_code += """
        <table class="line" style="display:none;">
            <caption>Performance %s</caption>
            <thead>
                <tr>
                  <td></td>
                  <th>Xmit Data</th>
                  <th>Rcv Data</th>
                </tr>
            </thead>
            <tbody>""" % self.node_name
              
            
        for line in out.split('\n'):
            if not re.match('\d+',line): continue
            (mat0, mat1, mat2) = line.split()
            stamp = re.search('(\d+)',mat0).group(1)
            val1 = exp2int(mat1)
            val2 = exp2int(mat2)
            self.html_code += """
            <tr>
                <th>%s</th>
                <td>%s</td>
                <td>%s</td>
            </tr>
            """ % (time.strftime("%H:%M", time.localtime(int(stamp))),
                   val1, val2)
        self.html_code += """
            </tbody>
        </table>
        """
    def html5_err(self, mins):
        start_time = 'now-%s' % (mins * 60)  
        start_time = '1331398900-%s' % (mins * 60)  
        end_time = '1331398900'
        #end_time = 'now'
        
        cmd_html = ['rrdtool', 'fetch', self.rrd_err,
                    '-s',start_time,'-e',end_time,'AVERAGE']
        process = subprocess.Popen(cmd_html, shell=False, stdout=subprocess.PIPE)

        (out, errc) = process.communicate()
        self.html_code += """
        <table class="line" style="display:none;">
            <caption>Errorcounter %s</caption>
            <thead>
            <tr>
                <td></td>
                <th>Symbol ErrCnt</th>
                <th>Xmit Discards</th>
                <th>VL15 dropped</th>
                <th>Link downed</th>
                </tr>
            </thead>
            <tbody>""" % self.node_name
              
            
        for line in out.split('\n'):
            if not re.match('\d+',line): continue
            (mat0, mat1, mat2, mat3, mat4) = line.split()
            stamp = re.search('(\d+)',mat0).group(1)
            val1 = exp2int(mat1)
            val2 = exp2int(mat2)
            val3 = exp2int(mat3)
            val4 = exp2int(mat4)
            self.html_code += """
                <tr>
                    <th>%s</th>
                    <td>%s</td>
                    <td>%s</td>
                    <td>%s</td>
                    <td>%s</td>
                </tr>
            """ % (time.strftime("%H:%M", time.localtime(int(stamp))),
                   val1, val2, val3, val4)
        self.html_code += """
            </tbody>
        </table>
        """
        
class RRDException(Exception): pass

