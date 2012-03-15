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

import subprocess
import time
import datetime

class IBsim(object):
    """ lib-Class to control ibsimulation"""
    def __init__(self, topo_file, binary):
        self.topo_file  = topo_file
        self.bin        = binary
        self.log_file   = "/var/log/ibsom.log"
        self.count_cmd = 0
    def log(self, msg):
        zeit = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        file_d = open(self.log_file, "a")
        file_d.write("%s: %s\n" % (zeit, msg))
        file_d.close()
    def service_ibsim(self, log_e, start=True):
        if start:
            command = [self.bin, "-s", self.topo_file]
            self.ibs_proc = subprocess.Popen(command, shell=False, stderr=None,
                                             stdout=subprocess.PIPE,
                                             stdin=subprocess.PIPE)
            log_e.set_status("OK")
        else:
            self.ibs_proc.kill()
            log_e.set_status("OK")
    def service_opensm(self, log_e, start=True):
        if start:
            cmd = ["/usr/local/sbin/opensm", "-F", "/etc/opensm.conf"]
            self.sm_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
            log_e.set_status("OK")
        else:
            self.sm_proc.kill()
            log_e.set_status("OK")
    def unlink(self, log_e, host, port=False):
        if port:
            node = "\"%s\"[%s]" % (host, port)
        else:
            node = "\"%s\"" % host
        line = "unlink %s\n" % node
        log_e.set_desc("Unlink %s" % node)
        self.ibs_proc.stdin.write(line)
        self.count_cmd += 1
        if check_ib():
            log_e.set_status("OK")
        else:
            log_e.set_status("IB hangs CMD:%s" % self.count_cmd)
            raise IOError("IB-Error")
            
    def relink(self, log_e, host, port=False):
        if port:
            node = "\"%s\"[%s]" % (host, port)
        else:
            node = "\"%s\"" % host
        log_e.set_desc("Relink %s" % node)
        line = "relink %s\n" % node
        self.ibs_proc.stdin.write(line)
        self.count_cmd += 1
        if check_ib():
            log_e.set_status("OK")
        else:
            log_e.set_status("IB hangs CMD:%s" % self.count_cmd)
            raise IOError("IB-Error")

## Function
def check_ib(timeout=2):
    """ check wether ib is working or not
        if not the command will not run nicely and the timeout will
        kick in"""
    cmd = ["ibstat"]
    ibstat_p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    time.sleep(0.1)
    # poll for terminated status till timeout is reached
    t_beginning = time.time()
    seconds_passed = 0
    while True:
        if ibstat_p.poll() is not None:
            break
        seconds_passed = time.time() - t_beginning
        if timeout and seconds_passed > timeout:
            ibstat_p.terminate()
            return False
        time.sleep(0.2)
    return True
