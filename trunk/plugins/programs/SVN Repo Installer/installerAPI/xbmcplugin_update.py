"""

    Programs/Plugin to check for SVN Repo updates of your installed scripts and Plugins

    This version as part of "SVN Repo installer" Programs/Plugin

    Written by BigBellyBilly
    Contact me at BigBellyBilly at gmail dot com - Bugs reports and suggestions welcome.

""" 

import sys, os
import os.path
import xbmc, xbmcgui, xbmcplugin
import urllib, urlparse
import re
import traceback
from string import find
#from pprint import pprint

# Script constants
__plugin__ = "xbmcplugin_update"
__author__ = 'BigBellyBilly [BigBellyBilly@gmail.com]'
__date__ = '04-04-2009'
xbmc.log( "[PLUGIN]: %s Dated: %s started!" % (__plugin__, __date__))

def log(msg):
    try:
        xbmc.log("[%s]: %s" % (__plugin__, msg), xbmc.LOGDEBUG)
    except: pass

# check if build is special:// aware - set roots paths accordingly
XBMC_HOME = 'special://home'
if not os.path.isdir(xbmc.translatePath(XBMC_HOME)):    # if fails to convert to Q:, old builds
    XBMC_HOME = 'Q:'
log("XBMC_HOME=%s" % XBMC_HOME)

class Main:

    URL_BASE_SVN_SCRIPTING = "http://xbmc-scripting.googlecode.com/svn"
    URL_BASE_SVN_ADDONS = "http://xbmc-addons.googlecode.com/svn"

    def __init__( self ):
        log("__init__()")
        ok = False

        # load settings
        self.showNoSVN = bool(xbmcplugin.getSetting( "show_no_svn" ) == "true")
        self.showNoVer = bool(xbmcplugin.getSetting( "show_no_ver" ) == "true")
        
        self.XBMC_REVISION = re.search("r([0-9]+)",  xbmc.getInfoLabel( "System.BuildVersion" ), re.IGNORECASE).group(1)
        log("XBMC_REVISION-%s" % self.XBMC_REVISION)
        self.SVN_URL_LIST = [ "xbmc-addons", "xbmc-scripting" ]
        #['plugin://programs/SVN Repo Installer/', '-1', '?download_url="%2Ftrunk%2Fplugins%2Fmusic/iTunes%2F"&repo=\'xbmc-addons\'&install=""&ioffset=2&voffset=0']
        # create all XBMC script/plugin paths
        paths = ("plugins/programs","plugins/video","plugins/music","plugins/pictures","scripts")
        self.XBMC_PATHS = []
        for p in paths:
            self.XBMC_PATHS.append( xbmc.translatePath( "/".join( [XBMC_HOME, p] ) ) )

        self.dialogProgress = xbmcgui.DialogProgress()
        self.dialogProgress.create(__plugin__)
        self.findInstalled()
        if self.INSTALLED:
            self.checkUpdates() 
            ok = self.showUpdates()
        else:
            xbmcgui.Dialog.ok(__plugin__, "No installed Addons found!")
        self.dialogProgress.close()

        xbmcplugin.endOfDirectory( int( sys.argv[ 1 ] ), ok)

    def findInstalled(self):
        log("> findInstalled()")
        
        self.INSTALLED = []
        ignoreList = (".","..",".backups")
        self.dialogProgress.update(0, xbmc.getLocalizedString( 30009 )) # Looking for installed addons
        TOTAL_PATHS = len(self.XBMC_PATHS)
        for count, p in enumerate(self.XBMC_PATHS):
            if not os.path.isdir(p): continue

            files = os.listdir(p)
            for f in files:
                # ignore parent dirs
                if f in ignoreList: continue

                percent = int( count * 100.0 / TOTAL_PATHS )
                self.dialogProgress.update(percent)

                # extract version
                try:
                    filepath = os.path.join( p, f )
                    doc = open( os.path.join(filepath, "default.py"), "r" ).read()
                    ver = self.parseVersion(doc)
                    xbmc_rev = self.parseXBMCRevision(doc)
                    thumb = ""
                    if os.path.isfile( os.path.join(filepath, "default.tbn") ):
                        thumb = os.path.join(filepath, "default.tbn")
                    if ver or self.showNoVer:
                        self.INSTALLED.append({"filepath": filepath, "ver": ver, "thumb": thumb, "xbmc_rev": xbmc_rev })
                except:
                    pass#traceback.print_exc()

#        pprint (self.INSTALLED)
        log("< findInstalled()  installed count=%d" % len(self.INSTALLED))

    #####################################################################################################
    def checkUpdates(self):
        log("> checkUpdates()")

        actionMsg = xbmc.getLocalizedString( 30010 )        # Checking SVN
        self.dialogProgress.update(0, actionMsg)

        TOTAL_PATHS = len(self.INSTALLED)
        quit = False
        for count, info in enumerate(self.INSTALLED):
            log("%d checking installed=%s" % (count, info))

            if not info['ver']: continue            # ignore installed without version doc tag

            # find installed category from filepath
            installedCategory  = self.parseCategory(info['filepath'])

            for repo in self.SVN_URL_LIST:
                repo_info = self._get_repo_info( repo )
                base_url = repo_info[ 0 ] + repo_info[ 1 ]
                # xbmc-scripting has no 'scripts' in svn path, so remove it from installedCategory
                if base_url.startswith(self.URL_BASE_SVN_SCRIPTING):
                    installedCategory = installedCategory.replace('scripts/','')

                url = "/".join( [base_url, installedCategory, "default.py"] )
                readme_url = "/".join( [base_url, installedCategory, "resources", "readme.txt"] )
                log("url=" + url)

                percent = int( count * 100.0 / TOTAL_PATHS )
                self.dialogProgress.update(percent, actionMsg, installedCategory)
                if self.dialogProgress.iscanceled():
                    quit = True
                    break

                # download default.py
                try:
                    sock = urllib.urlopen( url.replace(' ','%20') )
                    doc = sock.read()
                    sock.close()
                except:
                    traceback.print_exc()
                    xbmcgui.Dialog().ok(__plugin__ + " - ERROR!", str(sys.exc_info()[ 1 ]) )
                    quit = True
                    break
                else:
                    # check __version__ tag
                    svn_ver = self.parseVersion(doc)
                    if svn_ver:
                        self.INSTALLED[count]['svn_ver'] = svn_ver
                        self.INSTALLED[count]['svn_xbmc_rev'] = self.parseXBMCRevision(doc)
                        self.INSTALLED[count]['readme'] = self._check_readme( readme_url.replace(' ','%20') )
                        self.INSTALLED[count]['svn_url'] = url.replace('/default.py','')
                        self.INSTALLED[count]['repo'] = repo
                        self.INSTALLED[count]['install'] = repo_info[ 2 ][ 2 ]
                        self.INSTALLED[count]['ioffset'] = repo_info[ 2 ][ 3 ]
                        self.INSTALLED[count]['voffset'] = repo_info[ 2 ][ 4 ]
                        
                        break # found in svn, move to next installed

            if quit: break

        log("< checkUpdates() updated count=%d" % len(self.INSTALLED))

    #####################################################################################################
    def _get_repo_info( self, repo ):
        # path to info file
        repopath = os.path.join( os.getcwd(), "resources", "repositories", repo, "repo.xml" )
        try:
            # grab a file object
            fileobject = open( repopath, "r" )
            # read the info
            info = fileobject.read()
            # close the file object
            fileobject.close()
            # repo's base url
            REPO_URL = re.findall( '<url>([^<]+)</url>', info )[ 0 ]
            # root of repository
            REPO_ROOT = re.findall( '<root>([^<]*)</root>', info )[ 0 ]
            # structure of repo
            REPO_STRUCTURES = re.findall( '<structure name="([^"]+)" noffset="([^"]+)" install="([^"]*)" ioffset="([^"]+)" voffset="([^"]+)"', info )
            return ( REPO_URL, REPO_ROOT, REPO_STRUCTURES[ 0 ], )
        except:
            traceback.print_exc()
            return None

    #####################################################################################################
    def parseXBMCRevision(self, doc):
        try:
            rev = re.search("__XBMC_Revision__.*?[\"'](.*?)[\"']",  doc, re.IGNORECASE).group(1)
        except:
            rev = ""
        log("parseXBMCRevision() revision=%s" % rev)
        return rev

    #####################################################################################################
    def parseVersion(self, doc):
        try:
            ver = re.search("__version__.*?[\"'](.*?)[\"']",  doc, re.IGNORECASE).group(1)
        except:
            ver = ""
        log("parseVersion() version=%s" % ver)
        return ver

    def _check_readme( self, url ):
        try:
            # open url
            usock = urllib.urlopen( url )
            # read source
            htmlSource = usock.read()
            # close socket
            usock.close()
            # compatible
            if ( "404 Not Found" in htmlSource ):
                return None
            else:
                return url
        except:
            return None

    #####################################################################################################
    def parseCategory(self, filepath):
        try:
            cat = re.search("(plugins.*|scripts.*)$",  filepath, re.IGNORECASE).group(1)
            cat = cat.replace("\\", "/")
        except:
            ver = ""
        log("parseCategory() cat=%s" % cat)
        return cat

    #####################################################################################################
    def showUpdates(self):
        log("> showUpdates()")
        ok = False
        log("showUpdates()")

        try:
            # create display list
            sz = len(self.INSTALLED)
            for info in self.INSTALLED:
                path = ""
                ver = info.get('ver', '')
                rev = info.get('xbmc_rev', '')
                filepath = info.get('filepath', '')
                svn_ver = info.get('svn_ver','')
                svn_xbmc_rev = info.get('svn_xbmc_rev','')
                readme = info.get('readme',None)
                svn_url = info.get('svn_url','')
                category = self.parseCategory(filepath)
                repo = info.get('repo','SVN ?')

                # ignore those not in SVN as per settings
                if (not svn_url or not svn_ver) and not self.showNoSVN:
                    continue

                # make update state according to found information
                if not ver:
                    verState = xbmc.getLocalizedString( 30013 )            # unknown version
                    ver = '?'
                elif not svn_url or not svn_ver:
                    verState = xbmc.getLocalizedString( 30012 )         # not in SVN
                elif ver >= svn_ver:
                    verState = xbmc.getLocalizedString( 30011 )            # OK
                elif (svn_xbmc_rev and self.XBMC_REVISION and self.XBMC_REVISION >= svn_xbmc_rev) or (not svn_xbmc_rev or not self.XBMC_REVISION):
                    # NEW AVAILABLE - setup callback url for plugin SVN Repo Installer
                    verState = "v%s (%s)" % ( svn_ver, xbmc.getLocalizedString( 30014 ) )        # eg. !New! v1.0
                    trunk_url = re.search('(/trunk.*?)$', svn_url, re.IGNORECASE).group(1)
                    #['plugin://programs/SVN Repo Installer/', '-1', '?download_url="%2Ftrunk%2Fplugins%2Fmusic/iTunes%2F"&repo=\'xbmc-addons\'&install=""&ioffset=2&voffset=0']
                    url_args = "download_url=%s&repo=%s&install=%s&ioffset=%s&voffset=%s" % \
                                (repr(urllib.quote_plus(trunk_url + "/")),
                                repr(urllib.quote_plus(repo)),
                                repr(info["install"]),
                                info["ioffset"],
                                info["voffset"],)
                    path = '%s?%s' % ( sys.argv[ 0 ], url_args, )
                else:
                    verState = "v%s (%s)" % ( svn_ver, xbmc.getLocalizedString( 30015 ), )        # eg. Incompatible

                if not path:
                    path = os.path.join(filepath, 'default.tbn')
                log("path=" + path)

                # display text
                text = "[%s] %s v%s" % (repo, category, ver)
                if verState.endswith( "(%s)" % xbmc.getLocalizedString( 30014 ) ):                            # !New! - checking against ! as its constant regardless of lang
                    label2 = "[COLOR=FF00FFFF]%s[/COLOR]" % verState
                elif verState.endswith( "(%s)" % xbmc.getLocalizedString( 30015 ) ):
                    label2 = "[COLOR=FFFF0000]%s[/COLOR]" % verState
                elif verState == xbmc.getLocalizedString( 30011 ):
                    label2 = "[COLOR=FF00FF00]%s[/COLOR]" % verState
                else:
                    label2 = "[COLOR=FFFFFF00]%s[/COLOR]" % verState
                
                # addons thumbnail from svn_url
                icon = ""
                thumbnail = info["thumb"]
                if not thumbnail and svn_url:
                    thumbnail = "/".join( [svn_url.replace(' ','%20'), "default.tbn"] )

                # determine default icon according to addon type
                if find(filepath,'scripts') != -1:
                    icon = "DefaultScriptBig.png"
                elif find(filepath,'programs') != -1:
                    icon = "DefaultProgramBig.png"
                elif find(filepath,'music') != -1:
                    icon = "defaultAudioBig.png"
                elif find(filepath,'pictures') != -1:
                    icon = "defaultPictureBig.png"
                elif find(filepath,'video') != -1:
                    icon = "defaultVideoBig.png"
                # check skin for image, else fallback DefaultFile
                if not icon or not xbmc.skinHasImage(icon):
                    icon = "DefaultFileBig.png"
                if not thumbnail:
                    thumbnail = icon
                log("icon=%s    thumbnail=%s" % (icon, thumbnail))

                li=xbmcgui.ListItem( text, label2, icon, thumbnail)
                li.setInfo( type="Video", infoLabels={ "Title": text, "Genre": label2 } )
                cm = [ ( xbmc.getLocalizedString( 30600 ), "XBMC.RunPlugin(%s?showlog=True&repo=%s&category=%s&revision=None&parse=True)" % ( sys.argv[ 0 ], urllib.quote_plus( repr( repo ) ), urllib.quote_plus( repr( category.split( "/" )[ -1 ] )  ), ), ) ]
                if ( readme is not None ):
                    cm += [ ( xbmc.getLocalizedString( 30610 ), "XBMC.RunPlugin(%s?showreadme=True&repo=None&readme=%s)" % ( sys.argv[ 0 ], urllib.quote_plus( repr( readme ) ), ), ) ]
                li.addContextMenuItems( cm, replaceItems=True )

                xbmcplugin.addDirectoryItem( handle=int( sys.argv[ 1 ] ), url=path, listitem=li, isFolder=False, totalItems=sz )

            xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_GENRE )
#            xbmcplugin.setContent( handle=int( sys.argv[ 1 ] ), content="files")
            ok = True
        except:
            traceback.print_exc()
            xbmcgui.Dialog().ok(__plugin__ + " - ERROR!", str(sys.exc_info()[ 1 ]) )

        log("< showUpdates() ok=%s" % ok)
        return ok
    

if ( __name__ == "__main__" ):
    try:
        Main()
    except:
        traceback.print_exc()

