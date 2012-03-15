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
    def set_status(self, status):
        self.status = status.strip()
    def add_status(self, msg):
        self.status += msg
    def set_desc(self, desc):
        self.desc = desc.strip()
    def __str__(self):
        if self.status != "":
            res = "%s : %s" % (self.desc.ljust(25), self.status)
        else:
            res = self.desc
        return res


class MyApp(object):
    def __init__(self, opt):
        self.opt = opt
        self.eval_netlist()
        self.builder = gtk.Builder()
        self.builder.add_from_file("/root/QNIB/serverfiles/usr/local/etc/ibsim.ui")
        self.builder.connect_signals(self)
        log_win = self.builder.get_object("log")
        self.log_buffer = log_win.get_buffer()
        arr = [""]*10
        self.log_buffer.set_text("\n".join(arr))
        font_desc = pango.FontDescription('Courier 10')
        log_win.modify_font(font_desc)

        self.ibs = libibsim.IBsim("/root/QNIB/serverfiles/test/netlist.clos5", "/usr/bin/ibsim")

        log_e = LOGentry("")
        self.log_text = [log_e]*10
        #self.start_services()
    def change_buttons(self):
        objs = self.builder.get_objects()
        for obj in objs:
            if type(obj) is gtk.ToggleButton:
                self.change_button(obj)
            elif type(obj) is gtk.TextView:
                self.change_textview(obj)
            elif type(obj) is gtk.Window:
                self.change_window(obj)
            elif type(obj) is gtk.Label:
                self.change_label(obj)

    def run(self):
        try:
            gtk.main()
        except KeyboardInterrupt:
            pass
    def quit(self):
        self.ibsim(False)
        self.opensm(False)
        gtk.main_quit()
    def start_services(self):
        """ We are pressing the butons and using the callback functions """
        ibsim_but = self.builder.get_object("ibsim")
        ibsim_but.set_active(True)
        ibsim_but = self.builder.get_object("opensm")
        ibsim_but.set_active(True)
    def start_simulation(self, opt):
        mat = re.search("(\d+)", opt.get_name())
        if mat:
            steps = int(mat.group(1))
            log_e = LOGentry("Starting %s Sim-Steps" % steps)
            self.add_log(log_e)
            while steps > 0:
                steps -= 1
                self.rand_press()
                time.sleep(5)
        else:
            while True:
                self.rand_press()
                time.sleep(5)
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
    def switch_service(self, opt):
        if opt.get_name()=='ibsim':
            self.ibsim(opt.get_active())
        elif opt.get_name()=='opensm':
            self.opensm(opt.get_active())
    def ibsim(self, start=True):
        if start:
            log_e = LOGentry("Starting ibsim")
        else:
            log_e = LOGentry("Stoping ibsim")
        self.add_log(log_e)
        self.ibs.service_ibsim(log_e, start)
        self.refresh_log()
    def opensm(self, start=True):
        if start:
            log_e = LOGentry("Starting opensm")
        else:
            log_e = LOGentry("Stoping opensm")
        self.add_log(log_e)
        self.ibs.service_opensm(log_e, start)
        self.refresh_log()
    def add_log(self, log_e):
        self.log_text.append(log_e)
        self.refresh_log()
    def refresh_log(self):
        log_list = [x.__str__() for x in self.log_text[-10:]]
        log_list.reverse()
        self.log_buffer.set_text("\n".join(log_list))
    def change_window(self, obj):
        pass
    def change_label(self, obj):
        """ Change attributes of label widgets """
        obj.modify_font(pango.FontDescription('bold 10'))
    def change_textview(self, obj):
        """ Change color of the textbox"""
        pass
        #obj.modify_base(gtk.STATE_NORMAL,gtk.gdk.color_parse('#000000'))
        #obj.modify_text(gtk.STATE_NORMAL,gtk.gdk.color_parse('#FFFFFF'))
        #obj.modify_font(pango.FontDescription('Monospace 11'))

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
    def node_toggled(self, opt):
        node = opt.get_name()

        node_obj = self.builder.get_object(node)
        if opt.get_active():
            if self.node_list[node]['blocked'] == 2:
                log_e = LOGentry("Relink %s" % node)
                self.add_log(log_e)
                log_e.set_status("BLOCKED")
                node_obj.set_active(False)
            elif self.node_list[node]['blocked'] == 1:
                # I am the root, so unblock me 
                log_e = LOGentry("Relink %s" % node)
                self.add_log(log_e)
                self.node_list[node]['blocked'] = 0
                self.ibs.relink(log_e, node)
                # And pimp me childs to let them think they are root 
                self.set_blocker(node)                
                self.unblock_recursiv(node)
            else:
                # I am not block, so unblock me 
                self.node_list[node]['blocked'] = 0
                self.ibs.relink(log_e, node)
                self.unblock_recursiv(node)
        else:
            if self.node_list[node]['blocked'] == 2:
                pass
            elif self.node_list[node]['blocked'] == 0:
                log_e = LOGentry("Unlink %s" % node)
                self.add_log(log_e)
                self.node_list[node]['blocked'] = 1
                self.ibs.unlink(log_e, node)
            else:
                log_e = LOGentry("Unlink %s" % node)
                self.add_log(log_e)
                log_e.set_status("BLOCKED")
            self.block_recursiv(node)
        self.refresh_log()
    def set_blocker(self, node):
        for child_name in self.node_list[node]['childs']:
            self.node_list[child_name]['blocked'] = 1
    def block_recursiv(self, node, parent=None):
        """ If Child is not blocked, we press/block it """
        for child_name in self.node_list[node]['childs']:
            if self.node_list[child_name]['blocked'] == 0:
                #print "Releasing childs button: '%s'->'%s'" % (node,child_name)
                self.node_list[child_name]['blocked'] = 2
                self.node_list[child_name]['bocker'] = node
                child_obj = self.builder.get_object(child_name)
                child_obj.set_active(False)
                self.block_recursiv(child_name, node)
    def unblock_recursiv(self, node):
        """ If Child is blocked, we release/unblock it"""
        for child_name in self.node_list[node]['childs']:
            if self.node_list[child_name]['blocked'] == 1:
                #print "Pressing childs button: '%s'->'%s'" % (node,child_name)
                child_obj = self.builder.get_object(child_name)
                child_obj.set_active(True)
                self.node_list[child_name]['bocker'] = None
                self.node_list[child_name]['blocked'] = 0
                self.unblock_recursiv(child_name)
    def on_window1_delete_event(self, *args):
        self.quit()
    def eval_netlist(self):
        self.node_list  = {}
        self.sw_list    = []
        self.child_list = []
        reg_switch = "Switch[ \t]+\d+[ \t]+\"(.*)\""
        reg_switchport = "\[(\d+)\][ \t]+\"(.*)\"\[(\d+)\]"
        reg_host = "(Hca|Ca)"
        for line in open(self.opt.netlist,"r"):
            mat_switch      = re.match(reg_switch, line)
            mat_switchport  = re.match(reg_switchport, line)
            mat_host        = re.search(reg_host, line)
            if mat_switch:
                sw_name = mat_switch.group(1)
                self.sw_list.append(sw_name)
                self.node_list[sw_name] = {'blocked':0, 'blocker':None, 'childs':[]}
            elif mat_switchport and sw_name != None:
                (sw_port, dst_name, dst_port) = mat_switchport.groups()
                if not self.node_list.has_key(dst_name):
                    self.node_list[dst_name] = {'blocked':0, 'blocker':None, 'childs':[]}
                self.add_child(sw_name, sw_port, dst_name, dst_port)
            if mat_host:
                sw_name = None
    def add_child(self, sw_name, sw_port, dst_name, dst_port):
        """ Destination was not seen yet, must be a child """
        if dst_name not in self.node_list.keys():
            #print "'%s' is not in node_list, must be a child of '%s'" % (dst_name,sw_name)
            self.node_list[sw_name]['childs'].append(dst_name)
        else:
            """ Destination is in Nodelist, so it is possible that
            - it is an uplink switch and should not be linked as a child"""
            if sw_name not in self.node_list[dst_name]['childs']:
                self.node_list[sw_name]['childs'].append(dst_name)
            else:
                #print "'%s' is an uplink switch of '%s'" % (dst_name, sw_name)
                pass    
    def print_netlist(self):
        for node_name, val in self.node_list.items():
            print "# %s" % node_name
            for key1, val1 in val.items():
                print key1, val1
            
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
    app.change_buttons()
    if False:
        app.print_netlist()
        sys.exit()
    app.run()
