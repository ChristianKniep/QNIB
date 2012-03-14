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

import gtk
import pango
import sys
import time
import re
import random
import subprocess
import commands

sys.path.append("/root/QNIB/serverfiles/usr/local/lib/")
import libibsim
sys.path.append("/root/QNIB/serverfiles/usr/local/bin/")
from parse_ibnetdiscover import Parameter

class LOG(object):
    def __init__(self, opt, qnib):
        self.opt    = opt
        self.qnib   = qnib
        self.status_list = []
        self.perf_list   = []
        self.ret_ec = 0
        self.stat_dict = {}
        self.res  = {}
    def add_perf(self, key, val):
        self.perf_list.append("%s=%s" % (key, val))
        if val != 0:
            self.status_list.append("%sms %s" % (val, key))
    def __str__(self):
        if   self.ret_ec == 0:
            ret_txt = "OK"
        elif self.ret_ec == 1:
            ret_txt = "WARN"
        elif self.ret_ec == 2:
            ret_txt = "CRIT"
        ret_txt += " - % s  | %s" % (", ".join(self.status_list), \
                                     ", ".join(self.perf_list))
        return ret_txt
    def get_status(self):
        return ", ".join(self.status_list)
    def get_ec(self):
        return self.ret_ec
    def start(self, stat):
        if not self.res.has_key(stat):
            self.res[stat] = 0
        self.stat_dict[stat] = time.time()
    def end(self, stat):
        end = time.time()
        self.res[stat] += int((end - self.stat_dict[stat])*1000)
        self.stat_dict[stat] = 0
    def finish(self, stat):
        self.add_perf(stat, self.res[stat])
        self.res[stat] = 0
    def debug(self, msg, deb=3):
        if self.opt.debug >= deb:
            log_e = LOGentry(msg)
            self.qnib.add_log(log_e)
            self.qnib.refresh_log()
    def get_status_list(self):
        return self.status_list


class LOGentry(object):
    def __init__(self, desc):
        self.desc   = desc.strip()
        self.status = ""
        self.time = time.time()
    def set_status(self, status):
        self.status = status.strip()
    def add_status(self, msg):
        self.status += msg
    def add_desc(self, msg):
        self.desc += msg
    def set_desc(self, desc):
        self.desc = desc.strip()
    def getTime(self):
        return time.strftime("%H:%M", time.localtime(self.time))
    def __str__(self):
        if self.status != "":
            res = "%s# %s:%s" % (self.getTime(), self.desc.ljust(30), self.status)
        else:
            res = self.desc
        return res


class MyApp(object):
    def __init__(self, opt):
        self.opt = opt
        self.builder = gtk.Builder()
        self.builder.add_from_file("/root/QNIB/serverfiles/usr/local/etc/perf_control.ui")
        self.builder.connect_signals(self)
        log_win = self.builder.get_object("log")
        self.log_buffer = log_win.get_buffer()
        arr = [""]*15
        self.log_buffer.set_text("\n".join(arr))
        font_desc = pango.FontDescription('Courier 10')
        log_win.modify_font(font_desc)
        self.srv_free = set([])
        self.cli_free = set([])
        self.servers = set([])
        self.clients = set([])
        self.next_cli = ""
        self.next_srv = ""
        self.test_type = ""
        self.srv_proc = {}
        self.cli_proc = {}
        self.ignore_but = False
        log_e = LOGentry("")
        self.log_text = [log_e]*15
        dst_obj = self.builder.get_object("src_emv111")
    def start_qperf(self, obj):
        test_read_obj = self.builder.get_object("rc_rdma_read_bw")
        test_write_obj = self.builder.get_object("rc_rdma_write_bw")
        test_bi_obj  = self.builder.get_object("rc_bi_bw")
        if test_read_obj.get_active():
            test = "rc_rdma_read_bw"
            dir = "<-"
        elif test_write_obj.get_active():
            test = "rc_rdma_write_bw"
            dir = "->"
        elif test_bi_obj.get_active():
            test = "rc_bi_bw"
            dir = "<>"
        dur_obj = self.builder.get_object("duration_min")
        dur_min = int(dur_obj.get_text())
        dur_sec = 60*dur_min
        delay_obj = self.builder.get_object("delay_min")
        delay_min = int(delay_obj.get_text())
        delay_sec = 60*delay_min
        
        log_e = LOGentry("%smin(delay:%s)" % (dur_min, delay_min))
        self.add_log(log_e)
        stamp = int(time.time())
        stamp_end = int(dur_sec)+stamp+15
        
        # Start Servers
        srv = self.next_srv
        srv_obj = self.builder.get_object("srv_%s" % srv)
        srv_obj.set_property('visible', False)
        self.srv_free -= set([srv])
        self.servers  |= set([srv])
        
        srv_subp = self.start_server(srv)
        if stamp_end not in self.srv_proc.keys():
            self.srv_proc[stamp_end] = []
        self.srv_proc[stamp_end].append((srv, log_e, srv_subp))
        
        # Start Client
        cli = self.next_cli
        log_stat= ", %s%s%s" % (cli,dir,srv)
        log_e.add_desc(log_stat)
        self.refresh_log()
        cli_obj = self.builder.get_object("cli_%s" % cli)
        cli_obj.set_property('visible', False)
        self.cli_free -= set([cli])
        self.clients  |= set([cli])
        
        if stamp_end not in self.cli_proc.keys():
            self.cli_proc[stamp_end] = []
        cli_subp = self.start_client(cli, srv, test, delay_sec, dur_sec)
        self.cli_proc[stamp_end].append((cli, log_e, cli_subp))
        
        log_e.set_status("ONGOING")
        self.refresh_log()
    def start_server(self, node):
        cmd = ["/usr/bin/ssh", "-n", "-f", node, "/usr/bin/qperf"]
        sm_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        time.sleep(2)
        return sm_proc
    def start_client(self, cli, srv, test, delay, duration):
        if delay>0:
            cmd = ["/usr/bin/ssh", "-n", "-f", cli, "sleep", str(delay),";",
               "/usr/bin/qperf", srv, "-t", "%ss" % duration, test]
        else:
            cmd = ["/usr/bin/ssh", "-n", "-f", cli,
               "/usr/bin/qperf", srv, "-t", "%ss" % duration, test]
        sm_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        return sm_proc
    def eval_objects(self):
        objs = self.builder.get_objects()
        if len(self.servers)==0 and len(self.srv_free)==0:
            # The sets are not initilized
            for obj in objs:
                mat_cli_srv = re.match("(srv|cli)_([a-z0-9A-Z]+)", obj.get_name())
                if  type(obj) is gtk.RadioButton and mat_cli_srv:
                    (pre, name) = mat_cli_srv.groups()
                    if pre=="srv":
                        self.srv_free.add(name)
                    elif pre=="cli":    
                        self.cli_free.add(name)
        for obj in objs:
            if type(obj) is gtk.RadioButton:
                self.eval_buttons(obj)
    def eval_buttons(self, obj):
        if obj.get_active():
            # Client / Server  buttons
            mat_cli_srv = re.match("(srv|cli)_([a-z0-9A-Z]+)", obj.get_name())
            mat_test = re.match("(rc|uc)", obj.get_name())
            if mat_cli_srv:
                (pre, name) = mat_cli_srv.groups()
                if pre=='srv':
                    self.next_srv = name
                elif pre=="cli":
                    self.next_cli = name
                return
            # Testtype buttons
            elif mat_test:
                name = obj.get_name()
                self.test_type = name
    def run(self):
        try:
            gtk.main()
        except KeyboardInterrupt:
            pass
    def exit(self, obj):
        self.quit()
    def quit(self):
        gtk.main_quit()
    def rand_press(self):
        node = self.get_rand_node()
        node_obj = self.builder.get_object(node)
        if node_obj.get_active():
            print "%s is active" % node
            node_obj.set_active(False)
        else:
            print "%s is inactive" % node
            node_obj.set_active(True)
        node_obj.queue_draw()
    def get_rand_node(self, blacklist=None):
        if blacklist == None:
            blacklist = []
        just_nodes = set(self.node_list.keys()) - set(self.sw_list)
        nodes = set([x for x in list(just_nodes) if self.node_list[x]['blocked'] in [0, 1]])
        whitelist = list(nodes - set(blacklist))
        index = random.randint(0, len(whitelist)-1)
        rand_node = whitelist[index]
        return rand_node
    def add_log(self, log_e):
        self.log_text.append(log_e)
        self.refresh_log()
    def refresh_log(self):
        log_list = [x.__str__() for x in self.log_text[-15:]]
        log_list.reverse()
        self.log_buffer.set_text("\n".join(log_list))
    def change_window(self, obj):
        pass
    def change_label(self, obj):
        """ Change attributes of label widgets """
        obj.modify_font(pango.FontDescription('bold 10'))
    def change_textview(self, obj):
        """ Change color of the textbox"""
        #obj.modify_base(gtk.STATE_NORMAL,gtk.gdk.color_parse('#000000'))
        #obj.modify_text(gtk.STATE_NORMAL,gtk.gdk.color_parse('#FFFFFF'))
        obj.modify_font(pango.FontDescription('Monospace 6'))
    def change_button(self,opt):
        cmap = opt.get_colormap()
        color_normal = cmap.alloc_color("darkgrey")
        color_active = cmap.alloc_color("white")
        color2 = cmap.alloc_color("lightblue")
        style = opt.get_style().copy()
        style.bg[gtk.STATE_NORMAL] = color_normal
        style.bg[gtk.STATE_ACTIVE] = color_active
        style.bg[gtk.STATE_PRELIGHT] = color2

        opt.set_style(style)
    def on_window1_delete_event(self, *args):
        self.quit()
    def pair_changed(self, obj):
        (pre, name) = obj.get_name().split("_")
    
        if obj.get_active():
            self.eval_objects()
    def refresh_nodes(self, obj):
        all_cli = []
        all_srv = []
        now = int(time.time())
        for end, srv_list in self.srv_proc.items():
            if end<now:
                while len(srv_list)>0:
                    (node,log_e, proc) = srv_list.pop()
                    cmd = "ssh -n -f %s 'pkill -f qperf$'" % node
                    (out, errc) = commands.getstatusoutput(cmd)
                    out, err = proc.communicate()
                    srv_obj = self.builder.get_object("srv_%s" % node)
                    srv_obj.set_property('visible', True)
                    log_e.set_status("DONE")
            else:
                all_srv.extend([x[0] for x in srv_list])
                
        for end, cli_list in self.cli_proc.items():
            reg_mb = "(\d+)[ \t]+MB"
            reg_gb = "(\d+)\.(\d+)[ \t]+GB"
            if end<now:
                while len(cli_list)>0:
                    (node, log_e, proc) = cli_list.pop()
                    out,err = proc.communicate()
                    perf = ""
                    for line in out.split("\n"):
                        mat_mb = re.search(reg_mb, line)
                        mat_gb = re.search(reg_gb, line)
                        if mat_mb:
                            perf = "%sMB/s" % mat_mb.group(1)
                        elif mat_gb:
                            perf = "%s.%sGB/s" % mat_gb.groups()
                    if perf!="":
                        log_e.set_status(perf)
                    else:
                        log_e.set_status("NO PERF")
                        
                    cli_obj = self.builder.get_object("cli_%s" % node)
                    cli_obj.set_property('visible', True)
            else:
                all_cli.extend([x[0] for x in cli_list])
        self.refresh_log()
        #print "Still running:"
        #print "  srv: %s // cli: %s" % (", ".join(all_srv), ", ".join(all_cli))
    def start_scenario(self, obj):
        mat = re.search("(\d+)",obj.get_name())
        if mat:
            scen_id = mat.groups()[0]
        else:
            raise IOError
        if scen_id=="1":
            scenarios = [
                {'cli':'emv107','srv':'emv104','delay':0, 'dur':11,'test':'rc_bi_bw'},
                {'cli':'emv106','srv':'emv111','delay':2, 'dur':18,'test':'rc_bi_bw'},
                
                {'cli':'emv109','srv':'emv108','delay':0, 'dur':20,'test':'rc_rdma_read_bw'},
                {'cli':'emv105','srv':'emv106','delay':0, 'dur':18,'test':'rc_rdma_read_bw'},
                {'cli':'emv111','srv':'emv107','delay':2, 'dur':18,'test':'rc_rdma_read_bw'},
                
                {'cli':'emv110','srv':'emv105','delay':1, 'dur':18,'test':'rc_rdma_write_bw'},
                {'cli':'emv104','srv':'emv110','delay':2, 'dur':17,'test':'rc_rdma_write_bw'},
                ]
        for scen in scenarios:
            cli = scen['cli']
            cli_obj = self.builder.get_object("cli_%s" % cli)
            cli_obj.set_active(True)
            srv = scen['srv']
            srv_obj = self.builder.get_object("srv_%s" % srv)
            srv_obj.set_active(True)
            dur = scen['dur']
            dur_obj = self.builder.get_object("duration_min")
            dur_obj.set_text(str(dur))
            delay = scen['delay']
            delay_obj = self.builder.get_object("delay_min")
            delay_obj.set_text(str(delay))
            test = scen['test']
            test_obj = self.builder.get_object(test)
            test_obj.set_active(True)
            
            start_obj = self.builder.get_object('test_start')
            start_obj.clicked()

class MYparameter(Parameter):
    def extra(self):
        self.parser.add_option("-n",
            dest="netlist",
            default="/root/QNIB/serverfiles/test/netlist.clos5",
            action = "store",
            help = "Netlist-File to parse and simulate (default: %default)")

if __name__ == '__main__':
    options = MYparameter()
    options.check()
    app = MyApp(options)
    app.eval_objects()
    if False:
        app.print_netlist()
        sys.exit()
    app.run()
