#!/usr/bin/python
# rhn.py - Copyright (C) 2011 Red Hat, Inc.
# Register system to RHN
# Written by Joey Boggs <jboggs@redhat.com> and Alan Pevec <apevec@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.

import os
import sys
from ovirtnode.ovirtfunctions import *
from subprocess import Popen, PIPE, STDOUT
from snack import *
import _snack

RHN_CONFIG_FILE = "/etc/sysconfig/rhn/up2date"

def run_rhnreg( serverurl="", cacert="", activationkey="", username="", password="", profilename="", proxyhost="", proxyuser="", proxypass=""):
    # novirtinfo: rhn-virtualization daemon refreshes virtinfo
    extra_args="--novirtinfo --norhnsd --nopackages --force"
    args=""
    # Get cacert location
    if len(serverurl) > 0:
        args+=" --serverUrl %s" % serverurl
    location="/etc/sysconfig/rhn/%s" % os.path.basename(cacert)
    if len(cacert) > 0:
        if not os.path.exists(cacert):
            log("cacert: " + cacert)
            log("location: " + location)
            log("Downloading Satellite CA cert.....")
            log("From: " + cacert + " To: " + location)
            os.system("wget -q -r -nd --no-check-certificate --timeout=30 --tries=3 -O \"" + location +"\" \"" + cacert + "\"")
        if os.path.isfile(location):
            if os.stat(location).st_size > 0:
                args+=" --sslCACert %s" % location
                ovirt_store_config(location)
            else:
                log("Error Downloading Satellite CA cert!")
                return 3

    if len(activationkey):
        args+=" --activationkey '%s'" % activationkey
    elif len(username):
        args+=" --username '%s'" % username
        if len(password):
            args+=" --password '%s' " % password
    else:
        # skip RHN registration when neither activationkey
        # nor username/password is supplied
        # return success for AUTO w/o rhn_* parameters
        return 1

    if len(profilename):
        args+=" --profilename '%s'" % profilename

    if len(proxyhost):
        args+=" --proxy=%s" % proxyhost
        if len(proxyuser):
            args+=" --proxyUser='%s'" % proxyuser
            if len(proxypass):
                args+=" --proxyPassword='%s'" % proxypass

    if len(extra_args):
        args+=" %s" % extra_args

    log("Registering to RHN account.....")

    unmount_config("/etc/sysconfig/rhn/systemid")
    unmount_config("/etc/sysconfig/rhn/up2date")
    # regenerate up2date config
    if os.path.exists("/etc/sysconfig/rhn/up2date"):
        os.unlink("/etc/sysconfig/rhn/up2date")
    logged_args = args.replace(password, "XXXXXXXX")
    log(logged_args)
    rhn_reg_cmd = "rhnreg_ks %s" % args
    rhn_reg = subprocess.Popen(rhn_reg_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    rhn_reg_output = rhn_reg.stdout.read()
    log(rhn_reg_output)
    rhn_reg.wait()
    rhn_reg_rc = rhn_reg.returncode
    if rhn_reg_rc == 0:
        ovirt_store_config("/etc/sysconfig/rhn/up2date")
        ovirt_store_config("/etc/sysconfig/rhn/systemid")
        log("System %s sucessfully registered to %s" % (profilename, serverurl))
        return 0
    else:
        if "username/password" in rhn_reg_output:
            rc = 2
        else:
            rc = 1
        log("Error registering to RHN account!")
        return rc

def ov(var):
    if OVIRT_VARS.has_key(var):
        return OVIRT_VARS[var]
    else:
        return ""

# AUTO for auto-install
#if len(sys.argv):
#    if sys.argv[1] == "AUTO":
#            run_rhnreg( ov("OVIRT_RHN_URL"), ov("OVIRT_RHN_CA_CERT"), ov("OVIRT_RHN_ACTIVATIONKEY"), ov("OVIRT_RHN_USERNAME"), ov("OVIRT_RHN_PASSWORD"), ov("OVIRT_RHN_PROFILE"), ov("OVIRT_RHN_PROXY"), ov("OVIRT_RHN_PROXYUSER"), ov("OVIRT_RHN_PROXYPASSWORD") )
#
#
# configuration UI plugin interface
#
class Plugin(PluginBase):
    """Plugin for RHN registration option.
    """

    def __init__(self, ncs):
        PluginBase.__init__(self, "Red Hat Network", ncs)
        self.rhn_conf = {}
    def form(self):
        elements = Grid(2, 12)
        login_grid = Grid(4,2)
        self.rhn_user = Entry(15, "")
        self.rhn_pass = Entry(15, "", password = 1)
        login_grid.setField(self.rhn_user, 1, 0)
        login_grid.setField(Label("Login: "), 0, 0, anchorLeft = 1)
        login_grid.setField(Label(" Password: "), 2, 0, anchorLeft = 1)
        login_grid.setField(self.rhn_pass, 3, 0, padding = (0,0,0,1))
        elements.setField(login_grid, 0, 4, anchorLeft = 1)
        profile_grid = Grid(2, 2)
        self.profilename = Entry(30, "")
        profile_grid.setField(Label("Profile Name (optional): "), 0, 0, anchorLeft = 1)
        profile_grid.setField(self.profilename, 1, 0, anchorLeft = 1)
        elements.setField(profile_grid, 0, 5, anchorLeft= 1, padding = (0, 0, 0, 1))
        rhn_type_grid = Grid(2, 2)
        self.public_rhn = Checkbox("RHN ")
        self.public_rhn.setCallback(self.public_rhn_callback)
        self.rhn_satellite = Checkbox("Satellite ")
        self.rhn_satellite.setCallback(self.rhn_satellite_callback)
        rhn_type_grid.setField(self.public_rhn, 0, 0)
        rhn_type_grid.setField(self.rhn_satellite, 1, 0)
        elements.setField(rhn_type_grid, 0, 6, anchorLeft= 1, padding = (0, 0, 0, 1))
        rhn_grid = Grid(2,2)
        rhn_grid.setField(Label("URL: "), 0, 0, anchorLeft = 1)
        self.rhn_url = Entry(40, "")
        self.rhn_url.setCallback(self.rhn_url_callback)
        rhn_grid.setField(self.rhn_url, 1, 0, anchorLeft = 1, padding=(1, 0, 0, 0))
        self.rhn_ca = Entry(40, "")
        self.rhn_ca.setCallback(self.rhn_ca_callback)
        rhn_grid.setField(Label("CA : "), 0, 1, anchorLeft = 1)
        rhn_grid.setField(self.rhn_ca, 1, 1, anchorLeft = 1, padding=(1, 0, 0, 0))
        elements.setField(rhn_grid, 0, 7, anchorLeft = 1, padding = (0, 0, 0, 1))
        top_proxy_grid = Grid(4,2)
        bot_proxy_grid = Grid(4,2)
        elements.setField(Label("HTTP Proxy"), 0, 8, anchorLeft = 1)
        self.proxyhost = Entry(20, "")
        self.proxyport = Entry(5, "", scroll = 0)
        self.proxyuser = Entry(14, "")
        self.proxypass = Entry(12, "", password = 1)
        self.proxyhost.setCallback(self.proxyhost_callback)
        self.proxyport.setCallback(self.proxyport_callback)
        top_proxy_grid.setField(Label("Server: "), 0, 0, anchorLeft = 1)
        top_proxy_grid.setField(self.proxyhost, 1, 0, anchorLeft = 1, padding = (0, 0, 1, 0))
        top_proxy_grid.setField(Label("Port: "), 2, 0, anchorLeft = 1)
        top_proxy_grid.setField(self.proxyport, 3, 0, anchorLeft = 1, padding = (0, 0, 0, 0))
        bot_proxy_grid.setField(Label("Username: "), 0, 0, anchorLeft = 1)
        bot_proxy_grid.setField(self.proxyuser, 1, 0, padding =(0,0,1,0))
        bot_proxy_grid.setField(Label("Password: "), 2, 0, anchorLeft = 1)
        bot_proxy_grid.setField(self.proxypass, 3, 0, padding = (0, 0, 0, 0))
        elements.setField(top_proxy_grid, 0, 10, anchorLeft = 1, padding = (0, 0, 0, 0))
        elements.setField(bot_proxy_grid, 0, 11, anchorLeft = 1, padding = (0, 0, 0, 0))
        self.proxyhost.setCallback(self.proxyhost_callback)
        self.proxyport.setCallback(self.proxyport_callback)

        # optional: profilename, proxyhost, proxyuser, proxypass
        self.get_rhn_config()
        if not "https://xmlrpc.rhn.redhat.com/XMLRPC" in self.rv("serverURL"):
            self.rhn_url.set(self.rv("serverURL"))
            self.rhn_ca.set(self.rv("sslCACert"))
        self.proxyhost.set(self.rv("httpProxy"))
        self.proxyuser.set(self.rv("proxyUser"))
        self.proxypass.set(self.rv("proxyPassword"))
        self.rhn_actkey = Entry(40, "")
        if self.rhn_url.value() == "https://xmlrpc.rhn.redhat.com/XMLRPC" or len(self.rhn_url.value()) == 0:
            self.public_rhn.setValue("*")
            self.rhn_url.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
            self.rhn_ca.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
        else:
            self.rhn_satellite.setValue(" 0")
            self.rhn_url.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_RESET)
            self.rhn_ca.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_RESET)
        if network_up():
            elements.setField(Textbox(62,3,"Register with Red Hat Network"), 0, 2, anchorLeft = 1)
        else:
            elements.setField(Textbox(62,3,"Network Down, Red Hat Network Registration Disabled"), 0, 2, anchorLeft = 1)
            for i in self.rhn_user, self.rhn_pass, self.profilename, self.public_rhn, self.rhn_satellite, self.rhn_url, self.rhn_ca, self.proxyhost, self.proxyport, self.proxyuser, self.proxypass:
                i.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
        return [Label(""), elements]

    def action(self):
        self.ncs.screen.setColor("BUTTON", "black", "red")
        self.ncs.screen.setColor("ACTBUTTON", "blue", "white")
        if not network_up():
            return False
        if self.rhn_satellite.value() == 1 and self.rhn_ca.value() == "":
            ButtonChoiceWindow(self.ncs.screen, "RHN Configuration", "Please input a CA certificate URL", buttons = ['Ok'])
            return False
        if len(self.rhn_user.value()) < 1 or len(self.rhn_pass.value()) < 1:
            ButtonChoiceWindow(self.ncs.screen, "RHN Configuration", "Login/Password must not be empty\n", buttons = ['Ok'])
            return False
        reg_rc = run_rhnreg(  serverurl=self.rhn_url.value(),
            cacert=self.rhn_ca.value(),
            activationkey=self.rhn_actkey.value(),
            username=self.rhn_user.value(),
            password=self.rhn_pass.value(),
            profilename=self.profilename.value(),
            proxyhost=self.proxyhost.value()+ ":" + self.proxyport.value(),
            proxyuser=self.proxyuser.value(),
            proxypass=self.proxypass.value())
        if reg_rc == 0 and not False:
            ButtonChoiceWindow(self.ncs.screen, "RHN Configuration", "RHN Registration Successful", buttons = ['Ok'])
            self.ncs.reset_screen_colors()
            return True
        elif reg_rc > 0:
            if reg_rc == 2:
                msg = "Invalid Username / Password "
            elif reg_rc == 3:
                msg = "Unable to retreive satellite certificate"
            else:
                msg = "Check ovirt.log for details"
            ButtonChoiceWindow(self.ncs.screen, "RHN Configuration", "RHN Configuration Failed\n\n" + msg, buttons = ['Ok'])
            return False

    def rhn_url_callback(self):
        # TODO URL validation
        if not is_valid_url(self.rhn_url.value()):
            self.ncs.screen.setColor("BUTTON", "black", "red")
            self.ncs.screen.setColor("ACTBUTTON", "blue", "white")
            ButtonChoiceWindow(self.ncs.screen, "Configuration Check", "Invalid Hostname or Address", buttons = ['Ok'])
        if self.rhn_satellite.value() == 1:
            host = self.rhn_url.value().replace("/XMLRPC","")

    def rhn_ca_callback(self):
        # TODO URL validation
        msg = ""
        if not self.rhn_ca.value() == "":
            if not is_valid_url(self.rhn_ca.value()):
                msg = "Invalid URL"
        elif self.rhn_ca.value() == "":
            msg = "Please input a CA certificate URL"
        if not msg == "":
            self.ncs.screen.setColor("BUTTON", "black", "red")
            self.ncs.screen.setColor("ACTBUTTON", "blue", "white")
            ButtonChoiceWindow(self.ncs.screen, "Configuration Check", msg, buttons = ['Ok'])

    def get_rhn_config(self):
        if os.path.exists(RHN_CONFIG_FILE):
            rhn_config = open(RHN_CONFIG_FILE)
            try:
                for line in rhn_config:
                    if "=" in line and "[comment]" not in line:
                        item, value = line.split("=")
                        self.rhn_conf[item] = value.strip()
            except:
                pass
            log(self.rhn_conf)
        else:
            log("RHN Config does not exist")
            return

    def rv(self, var):
        if self.rhn_conf.has_key(var):
            return self.rhn_conf[var]
        else:
            return ""

    def public_rhn_callback(self):
        self.rhn_satellite.setValue(" 0")
        self.rhn_url.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
        self.rhn_ca.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)

    def rhn_satellite_callback(self):
        self.public_rhn.setValue(" 0")
        self.rhn_url.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_RESET)
        self.rhn_ca.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_RESET)

    def proxyhost_callback(self):
        if len(self.proxyhost.value()) > 0:
            if not is_valid_hostname(self.proxyhost.value()):
                self.ncs.screen.setColor("BUTTON", "black", "red")
                self.ncs.screen.setColor("ACTBUTTON", "blue", "white")
                ButtonChoiceWindow(self.ncs.screen, "Configuration Check", "Invalid Proxy Host", buttons = ['Ok'])

    def proxyport_callback(self):
        if len(self.proxyport.value()) > 0:
            if not is_valid_port(self.proxyport.value()):
                self.ncs.screen.setColor("BUTTON", "black", "red")
                self.ncs.screen.setColor("ACTBUTTON", "blue", "white")
                ButtonChoiceWindow(self.ncs.screen, "Configuration Check", "Invalid Proxy Port", buttons = ['Ok'])

def get_plugin(ncs):
    return Plugin(ncs)
