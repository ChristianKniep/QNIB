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


import os
import time
import subprocess
import re
import sys

def exp2int(zahl):
    if zahl in ('0','-nan'):
        return str(0)
    else:
        reg = '(\d+)[,\.](\d+)e\+(\d+)'
        mat = re.search(reg,zahl)
        if mat:
            (pre, post, exp) = mat.groups()
            res = str(int((float(pre)+float(".%s" % post))*(10**int(exp))))
            return res

class RRD(object):
    def __init__(self, node, vertical_label='test'):
        self.node_name = node
        self.html_file = "/srv/www/qnib/%s.html" % node
        self.rrd_base =  "/srv/rrd/qnib/"

    def create_rrd(self, interval):
        self.create_perf(interval)
        self.create_err(interval)

    def create_perf(self, interval, p_ext, start=None):  
        rrd_perf = "%s/%s_%s_perf.rrd" % (self.rrd_base, self.node_name, p_ext)
        if os.path.exists(rrd_perf):
            return
        interval = str(interval) 
        interval_mins = float(interval) / 60
        heartbeat = str(int(interval) * 2)
        ds_arr = [
            'DS:xmit_data:GAUGE:%s:U:U' % heartbeat,
            'DS:rcv_data:GAUGE:%s:U:U' % heartbeat,
            ]
                  
        cmd_create = ['rrdtool', 'create', rrd_perf, '--step', interval]
        if start != None:
            cmd_create.extend([
                '--start',
                str(start-int(interval))
            ])
        cmd_create.extend(ds_arr)
        cmd_create.extend([
            'RRA:AVERAGE:0.5:6:3600',
            #'RRA:AVERAGE:0.5:30:3600',
            ])
        process = subprocess.Popen(cmd_create, shell=False, stdout=subprocess.PIPE)
        process.communicate()
        
    def create_err(self, interval, p_ext, start=None):  
        rrd_err = "%s/%s_%s_err.rrd" % (self.rrd_base, self.node_name, p_ext)
        if os.path.exists(rrd_err):
            return
        interval = str(interval) 
        interval_mins = float(interval) / 60  
        heartbeat = str(int(interval) * 2)
        ds_arr = [
            'DS:symbol_err_cnt:GAUGE:%s:U:U' % heartbeat,
            'DS:xmit_discards:GAUGE:%s:U:U' % heartbeat,
            'DS:vl15_dropped:GAUGE:%s:U:U' % heartbeat,
            'DS:link_downed:GAUGE:%s:U:U' % heartbeat
            ]
                  
        cmd_create = ['rrdtool', 'create', rrd_err, '--step', interval]
        if start != None:
            cmd_create.extend([
                '--start',
                str(start-int(interval))
            ])
        cmd_create.extend(ds_arr)
        cmd_create.extend([
            'RRA:AVERAGE:0.5:6:3600',
            #'RRA:AVERAGE:0.5:30:3600'
            ])

        process = subprocess.Popen(cmd_create, shell=False, stdout=subprocess.PIPE)
        process.communicate()

    def update_perf(self, p_ext, ins):
        rrd_perf = "%s/%s_%s_perf.rrd" % (self.rrd_base, self.node_name, p_ext)
        cmd_update = ['rrdtool', 'update', rrd_perf]
        stamps = ins.keys()
        stamps.sort()
        for stamp in stamps:
            val =  str(stamp)
            val += ":%(xmit_data)s:%(rcv_data)s" % ins[stamp]
            cmd_update.append(val)
        process = subprocess.Popen(cmd_update, shell=False, stdout=subprocess.PIPE)
        process.communicate()
    
    def update_err(self, p_ext, ins):
        rrd_err = "%s/%s_%s_err.rrd" % (self.rrd_base, self.node_name, p_ext)
        cmd_update = ['rrdtool', 'update', rrd_err]
        stamps = ins.keys()
        stamps.sort()
        for stamp in stamps:
            val =  str(stamp)
            val +=  ":%(symbol_err_cnt)s:%(xmit_discards)s" % ins[stamp]
            val += ':%(vl15_dropped)s:%(link_downed)s' % ins[stamp]
            cmd_update.append(val)
        process = subprocess.Popen(cmd_update, shell=False, stdout=subprocess.PIPE)
        process.communicate()
    
    def html5(self, mins,s_time='now'):
        self.mins = mins
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
        self.html5_tab(mins, s_time, 'perf')
        #self.html5_tab(mins, s_time, 'err')

        self.html_code += """
    </body>
</html>
"""
        file_d = open(self.html_file, "w")
        file_d.write(self.html_code)
        file_d.close()
        
    def html5_tab(self, mins, s_time, typ):
        start_time = '%s-%s' % (s_time, mins * 60)  
        end_time = s_time
        
        reg = "%s_(\d+)_%s\.rrd" % (self.node_name, typ)
        td_vals = {}
        td_vals_by_stamp = {}
        plain_keys = set([])
        plain_ports = []
        files = os.listdir(self.rrd_base)
        for file_name in [x for x in files if re.match(reg, x)]:
            mat = re.match(reg, file_name)
            p_ext = mat.group(1)
            plain_ports.append(p_ext)
            cmd_html = ['rrdtool', 'fetch',
                        "%s%s" % (self.rrd_base, file_name),
                        '-s',start_time,'-e',end_time,'AVERAGE']
            process = subprocess.Popen(cmd_html, shell=False, stdout=subprocess.PIPE)
    
            (out, errc) = process.communicate()
            reg_head = "[ \t]+([a-z_0-9]+)[ \t]+([a-z_0-9]+)[ \t]+([a-z_0-9]+)"
            for line in out.split('\n'):
                if re.match('[ \t]+[a-z_0-9]', line):
                    td_keys = []
                    td_heads = line.split()
                    for td_head in td_heads:
                        plain_keys.add(td_head)
                        key = "%s[%s]" % (td_head, p_ext)
                        td_keys.append(key)
                        if key not in td_vals.keys():
                            td_vals[key] = {}
                elif re.match('\d+', line):
                    c = 0
                    td_bodys = line.split()
                    stamp = td_bodys[0].replace(":","")
                    if stamp not in td_vals_by_stamp.keys():
                        td_vals_by_stamp[stamp] = {}
                    for td_body in td_bodys[1:]:
                        val = exp2int(td_body)
                        td_vals[td_keys[c]][stamp] = val
                        td_vals_by_stamp[stamp][td_keys[c]] = val
                        c += 1
        if False:
            for k, v in td_vals.items():
                print k, v
        plain_ports.reverse()
        val_keys = []
        for plain_port in plain_ports:
            for plain_key in plain_keys:
                val_keys.append("%s[%s]" % (plain_key, plain_port))
        self.create_tab(typ,val_keys, td_vals_by_stamp)
    def create_tab(self, typ, val_keys, td_vals_by_stamp):
        ## Table start
        if typ=='perf':
            self.create_tab_perf(val_keys, td_vals_by_stamp)
        elif typ=='err':
            tab_typ = "Errorcounter"
        else:
            tab_typ = "Unkown typ"
    def create_tab_perf(self, val_keys, td_vals_by_stamp):
        # xmit
        xmit_keys = filter(lambda x: re.match("xmit", x), val_keys)
        xmit_keys.sort()
        tab_typ = "Xmit-Performance"
        self.html_code += """
        <table class="line" style="display:none;">
            <caption>%s %s</caption>
            <thead>
                <tr>
                  <td></td>
                  <th>%s</th>
                </tr>
            </thead>
            <tbody>""" % (tab_typ, self.node_name,
                "</th>\n                   <th>".join(xmit_keys))
        stamps = td_vals_by_stamp.keys()
        stamps.sort()
        modulo = int(self.mins/4)
        counter = 0
        pop_stamps = [x for x in stamps[:-1]]
        pop_stamps.reverse()
        while len(pop_stamps)>0:
            stamp = pop_stamps.pop()
            #for stamp, vals in td_vals_by_stamp.items():
            vals = td_vals_by_stamp[stamp]
            rrd_vals = []
            for xmit_key in xmit_keys:
                rrd_vals.append(vals[xmit_key])
            #rrd_vals = [x for x in vals.values() if x!=None]
            if counter%modulo==0:
                self.html_code += """
            <tr>
                <th>%s</th>
                """ % time.strftime("%H:%M", time.localtime(int(stamp)))
                counter=1
            else:
                self.html_code += """
            <tr>
                <th></th>"""
                counter += 1
                
            self.html_code += """<td>%s</td>
            </tr>
            """ % "</td>\n                <td>".join(rrd_vals)

        self.html_code += """
            </tbody>
        </table>
        """
        # rcv
        rcv_keys = filter(lambda x: re.match("rcv", x), val_keys)
        rcv_keys.sort()
        tab_typ = "Rcv-Performance"
        self.html_code += """
        <table class="line" style="display:none;">
            <caption>%s %s</caption>
            <thead>
                <tr>
                  <td></td>
                  <th>%s</th>
                </tr>
            </thead>
            <tbody>""" % (tab_typ, self.node_name,
                "</th>\n                   <th>".join(rcv_keys))
        stamps = td_vals_by_stamp.keys()
        stamps.sort()
        modulo = int(self.mins/4)
        counter = 0
        pop_stamps = [x for x in stamps[:-1]]
        pop_stamps.reverse()
        while len(pop_stamps)>0:
            stamp = pop_stamps.pop()
            #for stamp, vals in td_vals_by_stamp.items():
            vals = td_vals_by_stamp[stamp]
            rrd_vals = []
            for rcv_key in rcv_keys:
                rrd_vals.append(vals[rcv_key])
            if counter%modulo==0:
                self.html_code += """
            <tr>
                <th>%s</th>
                """ % time.strftime("%H:%M", time.localtime(int(stamp)))
                counter=1
            else:
                self.html_code += """
            <tr>
                <th></th>"""
                counter += 1
            
            self.html_code += """<td>%s</td>
            </tr>
            """ % "</td>\n                <td>".join(rrd_vals)

        self.html_code += """
            </tbody>
        </table>
        """
    def html5_err(self, mins,s_time):
        start_time = '%s-%s' % (s_time, mins * 60)  
        end_time = s_time
        
        reg = "%s_(\d+)_err\.rrd" % self.node_name
        for root, dirs, files in os.walk(self.rrd_base):
            for file_name in files:
                mat = re.match(reg, file_name)
                if not mat:
                    continue
                p_ext = mat.group(1)
                cmd_html = ['rrdtool', 'fetch',
                            "%s%s" % (self.rrd_base, file_name),
                            '-s',start_time,'-e',end_time,'AVERAGE']
                process = subprocess.Popen(cmd_html, shell=False, stdout=subprocess.PIPE)
        
                (out, errc) = process.communicate()
                self.html_code += """
                <table class="line" style="display:none;">
                    <caption>Errorcounter %s external port %s</caption>
                    <thead>
                    <tr>
                        <td></td>
                        <th>Symbol ErrCnt</th>
                        <th>Xmit Discards</th>
                        <th>VL15 dropped</th>
                        <th>Link downed</th>
                        </tr>
                    </thead>
                    <tbody>""" % (self.node_name, p_ext)
                    
                for line in out.split('\n'):
                    if not re.match('\d+', line): continue
                    try:
                        (mat0, mat1, mat2, mat3, mat4) = line.split()
                    except ValueError,e:
                        print line
                        raise ValueError(e)
                    stamp = re.search('(\d+)', mat0).group(1)
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

