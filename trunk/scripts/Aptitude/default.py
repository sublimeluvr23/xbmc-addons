#!/usr/bin/python
# Aptitude script for XBMC
#
# LICENSE - See the LICENSE file that came with this module
#
# Copyright 2008 by Tobias Arrskog <topfs2@xbmc.org>

__version__ = "0.01"
__license__ = "GPL"
__url__     = "http://xbmc.org/"
__author__  = "topfs2@xbmc.org"

import sys, os
sys.path.append("/usr/lib/python2.5/site-packages") 
from apt.progress import *
import apt_pkg
import apt
import xbmc, xbmcgui
import time

class XBMCInstallProgress(InstallProgress):
    def __init__(self):
        InstallProgress.__init__(self)
        self.progress = xbmcgui.DialogProgress()
        self.progress.create("Installing", "Installing")
        self.last = 0
        self.progress.update(0)
    def updateInterface(self):
        InstallProgress.updateInterface(self)
        if self.last >= self.percent:
            return
        self.progress.update(self.percent)
        self.last = self.percent
    def close(self):
        self.progress.close()

class XBMCTextProgress(FetchProgress):
    """ A simple text based cache open reporting class """
    def __init__(self):
        FetchProgress.__init__(self)
        self.progress = xbmcgui.DialogProgress()
        self.progress.create("Initialize", "Reading the packagecache")
        self.progress.update(0)
    def update(self, percent):
        self.progress.update(percent)
    def done(self):
        self.progress.close()
apt_pkg.init()

c = apt.Cache(XBMCTextProgress())
#c.upgrade()
p = c.__getitem__("audacity")
if p.isInstalled:
    p.markDelete()
else:
    p.markInstall()
changes = c.getChanges()

dialog = xbmcgui.Dialog()
if len(changes) == 0:
    dialog.ok("Info", "No new packages available")
else:
    downloadSize = 0
    for p in changes:
        downloadSize += p.packageSize

    downloadString = str(len(changes)) + " packages to install, needs to download " + str(downloadSize / 1024 / 1024) + " mb. Continue?"

    if dialog.yesno("Info", downloadString):
        pathToInstallScript = '/home/topfs/XBMC-Default/BUILD/scripts/Aptitude/install.py'
        tmp = xbmc.translatePath('special://temp/') + 'workfile'
        install = 'sudo python ' + pathToInstallScript + ' > ' + tmp
        os.system(install)
        f = open(tmp, 'r')
        progress = xbmcgui.DialogProgress()
        res = False
        line1 = ""
        line2 = ""
        line3 = ""
        progress.create("Installing")
        for line in f.readlines():
            tokens = line.strip('\n').split(';')
            if "Start" in tokens:
                line1 = tokens[1]
                line2 = tokens[2]
                line3 = tokens[3]
                progress.update(0)
            elif "Finish" in tokens:
                pass
            elif "Progress" in tokens:
                line1 = tokens[2]
                line2 = tokens[3]
                line3 = tokens[4]
                progress.update(float(tokens[1]), line1, line2, line3)
            elif "Complete" in tokens:
                res = bool(tokens[1])
                progress.close()
                break
            time.sleep(0.001)
            if progress.iscanceled():
                progress.close()
                break
        
        if res:
            dialog.ok("Info", "Upgraded completed sucessfully")
        else:
            dialog.ok("Error", "Failed to upgraded")