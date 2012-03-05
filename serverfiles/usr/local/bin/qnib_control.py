#!/usr/bin/env python
#-*- coding: utf-8 -*-

import gtk
import pango
import sys
import copy
import time
import re
import random

sys.path.append("/root/QNIB/serverfiles/usr/local/lib/")
import libibsim
sys.path.append("/root/QNIB/serverfiles/usr/local/bin/")
from parse_ibnetdiscover import Parameter

class logC(object):
    def __init__(self, opt, qnib):
        self.opt    = opt
        self.qnib   = qnib
        self.statusList = []
        self.perfList   = []
        self.retEC = 0
        self.s = {}
        self.res  = {}
    def addPerf(self,key,val):
        self.perfList.append("%s=%s" % (key,val))
        if val!=0:
            self.statusList.append("%sms %s" % (val,key))
    def __str__(self):
        if   self.retEC==0: retTXT = "OK"
        elif self.retEC==1: retTXT = "WARN"
        elif self.retEC==2: retTXT = "CRIT"
        retTXT += " - %s | %s" % (", ".join(self.statusList),", ".join(self.perfList))
        return retTXT
    def get_status(self):
        return ", ".join(self.statusList)
    def getEC(self):
        return self.retEC
    def start(self,stat):
        if not self.res.has_key(stat): self.res[stat] = 0
        self.s[stat] = time.time()
    def end(self,stat):
        e = time.time()
        self.res[stat] += int((e - self.s[stat])*1000)
        self.s[stat] = 0
    def finish(self,stat):
        self.addPerf(stat,self.res[stat])
        self.res[stat] = 0
    def debug(self, msg, deb=3):
        if self.opt.debug>=deb:
            logE = log_entry(msg)
            self.qnib.addLog(logE)
            self.qnib.refresh_log()
    def get_statusList(self):
        return self.statusList

class log_entry(object):
    def __init__(self,desc):
        self.desc   = desc.strip()
        self.status = ""
    def set_status(self,status):
        self.status = status.strip()
    def add_status(self,msg):
        self.status += msg
    def set_desc(self,desc):
        self.desc = desc.strip()
    def __str__(self):
        if self.status!="":
            res = "%s : %s" % (self.desc.ljust(25),self.status)
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
        self.log_win = self.builder.get_object("log")
        self.log_buffer = self.log_win.get_buffer()
        self.log_buffer.set_text("starting")
        font_desc=pango.FontDescription('Courier 10')
        self.log_win.modify_font(font_desc)

        self.ibs = libibsim.ibsim("/root/QNIB/serverfiles/test/netlist.clos5")
        
        logE = log_entry("")
        self.log_text = [logE]*10
        self.start_services()
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
    def start_simulation(self,opt):
        mat = re.search("(\d+)",opt.get_name())
        if mat:
            steps = int(mat.group(1))
            logE = log_entry("Starting %s Sim-Steps" % steps)
            self.addLog(logE)
            while steps>0:
                steps -= 1
                self.rand_press()
                time.sleep(5)
        else:
            while True:
                self.rand_press()
                time.sleep(5)
    def rand_press(self):
        node = self.get_randNode()
        node_obj = self.builder.get_object(node)
        if node_obj.get_active():
            print "%s is active" % node
            node_obj.set_active(False)
        else:
            print "%s is inactive" % node
            node_obj.set_active(True)
        node_obj.queue_draw()
    def get_randNode(self,blacklist=[]):
        just_nodes = set(self.node_list.keys()) - set(self.sw_list)
        nodes = set([x for x in list(just_nodes) if self.node_list[x]['blocked'] in [0,1]])
        whitelist = list(nodes - set(blacklist))
        index = random.randint(0,len(whitelist)-1)
        rand_node = whitelist[index]
        return rand_node
    def switch_service(self,opt):
        if opt.get_name()=='ibsim':
            self.ibsim(opt.get_active())
        elif opt.get_name()=='opensm':
            self.opensm(opt.get_active())
    def ibsim(self,start=True):
        if start: logE = log_entry("Starting ibsim")
        else: logE = log_entry("Stoping ibsim")
        self.addLog(logE)
        self.ibs.service_ibsim(logE, start)
        self.refresh_log()
    def opensm(self,start=True):
        if start: logE = log_entry("Starting opensm")
        else: logE = log_entry("Stoping opensm")
        self.addLog(logE)
        self.ibs.service_opensm(logE, start)
        self.refresh_log()
    def addLog(self,logE):
        self.log_text.append(logE)
        self.refresh_log()
    def refresh_log(self):
        logList = [x.__str__() for x in self.log_text[-10:]]
        logList.reverse()
        self.log_buffer.set_text("\n".join(logList))
    def node_toggled(self,opt):
        node = opt.get_name()
        node_obj = self.builder.get_object(node)
        if opt.get_active():
            if self.node_list[node]['blocked']==2:
                logE = log_entry("Relink %s" % node)
                self.addLog(logE)
                logE.set_status("BLOCKED")
                node_obj.set_active(False)
            elif self.node_list[node]['blocked']==1:
                """ I am the root, so unblock me """
                logE = log_entry("Relink %s" % node)
                self.addLog(logE)
                self.node_list[node]['blocked'] = 0
                res = self.ibs.relink(logE, node)
                """ And pimp me childs to let them think they are root """
                self.set_blocker(node)                
                self.unblock_recursiv(node)
            else:
                """ I am not block, so unblock me """
                self.node_list[node]['blocked'] = 0
                res = self.ibs.relink(logE, node)
                self.unblock_recursiv(node)
        else:
            if self.node_list[node]['blocked']==2:
                pass
            elif self.node_list[node]['blocked']==0:
                logE = log_entry("Unlink %s" % node)
                self.addLog(logE)
                self.node_list[node]['blocked'] = 1
                res = self.ibs.unlink(logE, node)
            else:
                logE = log_entry("Unlink %s" % node)
                self.addLog(logE)
                logE.set_status("BLOCKED")
            self.block_recursiv(node)
        self.refresh_log()
    def set_blocker(self,node):
        for child_name in self.node_list[node]['childs']:
            self.node_list[child_name]['blocked'] = 1
    def block_recursiv(self,node,parent=None):
        for child_name in self.node_list[node]['childs']:
            """ If Child is not blocked, we press/block it"""
            if self.node_list[child_name]['blocked']==0:
                #print "Releasing childs button: '%s'->'%s'" % (node,child_name)
                self.node_list[child_name]['blocked'] = 2
                self.node_list[child_name]['bocker'] = node
                child_obj = self.builder.get_object(child_name)
                child_obj.set_active(False)
                self.block_recursiv(child_name, node)
    def unblock_recursiv(self,node):
        for child_name in self.node_list[node]['childs']:
            """ If Child is blocked, we release/unblock it"""
            if self.node_list[child_name]['blocked']==1:
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
            elif mat_switchport and sw_name!=None:
                (sw_port, dst_name, dst_port) = mat_switchport.groups()
                if not self.node_list.has_key(dst_name):
                    self.node_list[dst_name] = {'blocked':0, 'blocker':None, 'childs':[]}
                self.add_child(sw_name,sw_port,dst_name,dst_port)
            if mat_host:
                sw_name = None
    def add_child(self,sw_name, sw_port, dst_name, dst_port):
        if dst_name not in self.node_list.keys():
            """ Destination was not seen yet, must be a child """
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
        for node_name,v in self.node_list.items():
            print "# %s" % node_name
            for k1,v1 in v.items():
                print k1,v1
    def exec_script(self,opt):
        script = opt.get_name()
        if script=="parse_ibnetdiscover":
            parse_ibnetdiscover.gui(self,self.opt)
        elif script=="uptopo":
            uptopo.gui(self,self.opt)
        elif script=="create_netgraph":
            create_netgraph.gui(self,self.opt)
        if script=="complete_run":
            parse_ibnetdiscover.gui(self,self.opt)
            uptopo.gui(self,self.opt)
            create_netgraph.gui(self,self.opt)
            
class my_parameter(Parameter):
    def extra(self):
        self.parser.add_option("-n",
                               dest="netlist",
                               default="/root/QNIB/serverfiles/test/netlist.clos5",
                               action = "store",
                               help = "Netlist-File to parse and simulate (default: %default)")    

if __name__ == '__main__':
    options = my_parameter()
    options.check()
    app = MyApp(options)
    if False:
        app.print_netlist()
        sys.exit()
    app.run()
