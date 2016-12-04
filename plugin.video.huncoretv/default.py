#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import HTMLParser
import base64
from json import dumps
import os
import re
import requests, requests.utils, pickle
import shutil
import sys
import threading
from time import sleep
import time
import urllib
import urllib2
import urlparse

import xbmcaddon
import xbmcgui
import xbmcplugin

import sqlite3
import datetime
from kizstorrent import play_torrenturl

from python_libtorrent import get_libtorrent
import xbmc

torrentAddon = xbmcaddon.Addon(id='service.kizstorrent')
addon = xbmcaddon.Addon(id='plugin.video.huncoretv')
thisAddonDir = xbmc.translatePath(addon.getAddonInfo('path')).decode('utf-8')
sys.path.append(os.path.join(thisAddonDir, 'resources', 'lib'))

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

tags = ["minden","vígjáték","dráma","életrajz","akció","romantikus","dokumentumfilm","kaland","animáció","thriller","családi","bűnügyi","rövidfilm","musical","sci-fi","misztikus","háborús","western","horror","történelmi","sport","zene","ismeretterjesztő","valóságshow","3D","fantasy"]
appName = 'HUNCoreTV'
libtorrent=get_libtorrent()

logined = False

xbmcplugin.setContent(addon_handle, 'movies')
baseUrl = 'https://ncore.cc'

felhasznalo = addon.getSetting('felhasznalonev')
jelszo = addon.getSetting('jelszo')
torrentPath = addon.getSetting('torrentPath')
torrentFullDownload = addon.getSetting('torrentFullDownload')
tmptorles = addon.getSetting('tmptorlesido')
elonySzazalek = int(addon.getSetting('elonySzazalek'))

if (felhasznalo == "" or jelszo == "" or torrentPath == ""):
    dialog = xbmcgui.Dialog()
    dialog.ok("Hiba!", "Nem végezted el a beállításokat!", "", "")
    addon.openSettings()
    sys.exit()

transmission_send = addon.getSetting('send_to_transmission')
transmission_url = addon.getSetting('transmission_url')
transmission_username = addon.getSetting('transmission_username')
transmission_password = addon.getSetting('transmission_password')
transmission_paused = addon.getSetting('transmission_paused')

utorrent_send =  addon.getSetting('utorrent_send')
utorrent_url = addon.getSetting('utorrent_url')
if not utorrent_url.endswith("/"):
    utorrent_url = utorrent_url + "/"
utorrent_username = addon.getSetting('utorrent_username')
utorrent_password = addon.getSetting('utorrent_password')

filmHUNtipus=''
if addon.getSetting('xvid_hun') == 'true':
    filmHUNtipus = filmHUNtipus + ',xvid_hun'
if addon.getSetting('dvd_hun') == 'true':
    filmHUNtipus = filmHUNtipus + ',dvd_hun'
if addon.getSetting('dvd9_hun') == 'true':
    filmHUNtipus = filmHUNtipus + ',dvd9_hun'
if addon.getSetting('hd_hun') == 'true':
    filmHUNtipus = filmHUNtipus + ',hd_hun'
filmHUNtipus= filmHUNtipus[1:]

filmENGtipus=""
if addon.getSetting('xvid') == 'true':
    filmENGtipus = filmENGtipus + ',xvid'
if addon.getSetting('dvd') == 'true':
    filmENGtipus = filmENGtipus + ',dvd'
if addon.getSetting('dvd9') == 'true':
    filmENGtipus = filmENGtipus + ',dvd9'
if addon.getSetting('hd') == 'true':
    filmENGtipus = filmENGtipus + ',hd'
filmENGtipus= filmENGtipus[1:]

filmXXXtipus=""
if addon.getSetting('xxx_xvid') == 'true':
    filmXXXtipus = filmXXXtipus + ',xxx_xvid'
if addon.getSetting('xxx_dvd') == 'true':
    filmXXXtipus = filmXXXtipus + ',xxx_dvd'
if addon.getSetting('xxx_hd') == 'true':
    filmXXXtipus = filmXXXtipus + ',xxx_hd'
filmXXXtipus= filmXXXtipus[1:]

sorozatHUNtipus=""
if addon.getSetting('xvidser_hun') == 'true':
    sorozatHUNtipus = sorozatHUNtipus + ',xvidser_hun'
if addon.getSetting('dvdser_hun') == 'true':
    sorozatHUNtipus = sorozatHUNtipus + ',dvdser_hun'
if addon.getSetting('hdser_hun') == 'true':
    sorozatHUNtipus = sorozatHUNtipus + ',hdser_hun'
sorozatHUNtipus= sorozatHUNtipus[1:]

sorozatENGtipus=""
if addon.getSetting('xvidser') == 'true':
    sorozatENGtipus = sorozatENGtipus + ',xvidser'
if addon.getSetting('dvdser') == 'true':
    sorozatENGtipus = sorozatENGtipus + ',dvdser'
if addon.getSetting('hdser') == 'true':
    sorozatENGtipus = sorozatENGtipus + ',hdser'
sorozatENGtipus= sorozatENGtipus[1:]


try:
    torrentSession
except NameError:
    torrentSession = libtorrent.session()
    torrentSession.listen_on(6881, 6889)

def newSession():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.6 Safari/537.36',
    })
    return s

session = newSession()

def doLogin():
    global session
    if os.path.isfile(torrentPath + 'my.cookies'): 
        #sys.stderr.write("load Session")
        cookieFile = open(torrentPath + 'my.cookies')
        cookies = requests.utils.cookiejar_from_dict(pickle.load(cookieFile))
        session.cookies = cookies
    
    if felhasznalo != "":
        response = session.get(baseUrl + '/profile.php')
        if (felhasznalo + ' profilja') not in response.content:
            #sys.stderr.write("doLogin")
            payload = {'nev': felhasznalo, 'pass': jelszo, 'ne_leptessen_ki' : True}
            session.post(baseUrl + '/login.php',data = payload)
            response = session.get(baseUrl + '/profile.php')
            if (felhasznalo + ' profilja') in response.content:
                logined = True
                cookieFile = open(torrentPath + 'my.cookies', 'w')
                pickle.dump(requests.utils.dict_from_cookiejar(session.cookies), cookieFile)
            else:
                logined = False
                dialog = xbmcgui.Dialog()
                dialog.ok("Hiba!", "Helytelen felhasználónév, vagy jelszó!", "Esetleg megjelent az I'm not a robot captcha.", "Várj egy ideig, esetleg próbáld meg böngészőből!")
                sys.exit()
    return

def load(url, post = None):
    global session
    doLogin()
        
    r = ""
    try:
        if post:
            r = session.post(url, data=post, timeout=10).text
        else:
            r = session.get(url).text
    except AttributeError:
        xbmc.executebuiltin("HIBA: {0}".format(AttributeError.message))
        session = newSession()
        doLogin()
        if post:
            r = session.post(url, data=post, verify=False, timeout=10).text
        else:
            r = session.get(url, verify=False).text

    return r.encode('utf-8')

def send_to_downloader():
    if transmission_send == 'true':
        progress = xbmcgui.DialogProgress()
        progress.create(appName, 'Calling Transmission...')
        try:
            torrentFileContent = open(torrentPath + 'mytorrent.torrent', 'rb')
            torrent_content = base64.b64encode(torrentFileContent.read())
            torrentFileContent.close()
            
            if len(transmission_username) > 0:
                sessionid_request = requests.get(transmission_url, auth=(transmission_username, transmission_password), verify=False)
            else:
                sessionid_request = requests.get(transmission_url, verify=False)
                
            sessionid = sessionid_request.headers['x-transmission-session-id']
            if sessionid:
                headers = {"X-Transmission-Session-Id": sessionid}
                body = dumps({"method": "torrent-add", "arguments": {"metainfo": torrent_content, "paused":transmission_paused}})
                post_request = requests.post(transmission_url, data=body, headers=headers, auth=(transmission_username, transmission_password), verify=False)
                if str(post_request.text).find("success") == -1:
                    dialog = xbmcgui.Dialog().ok(appName, "Hiba történt a Transmission megszólításakor!", post_request.text, "");
                else:
                    progress.close()
                    return True
        except:
            dialog = xbmcgui.Dialog().ok(appName, "Hiba történt a Transmission megszólításakor!", str(sys.exc_info()[0]), "(Esetleg hibás beállítások?)");
        
        progress.close()
        return False
    elif utorrent_send == 'true':
        progress = xbmcgui.DialogProgress()
        progress.create(appName, u'Calling \u00b5Torrent...')
        utorrent_url_token = utorrent_url + 'token.html'
        
        try:
            auth = requests.auth.HTTPBasicAuth(utorrent_username, utorrent_password)
            sys.stderr.write('utorrent_url_token: ' + utorrent_url_token)
            content = requests.get(utorrent_url_token, auth=auth)
            sys.stderr.write('content: ' + content.text)
            token = re.search('<div[^>]*id=[\"\']token[\"\'][^>]*>([^<]*)</div>', content.text).group(1)
            guid = content.cookies['GUID']
            cookies = dict(GUID = guid)
            
            params = {'action':'add-file','token': token}
            files = {'torrent_file': open(torrentPath + 'mytorrent.torrent', 'rb')}
            requests.post(url=utorrent_url, auth=auth, cookies=cookies, params=params, files=files)
            progress.close()
            return True
        except:
            dialog = xbmcgui.Dialog().ok(appName, u"Hiba történt a \u00b5Torrent megszólításakor!", str(sys.exc_info()[0]), "(Esetleg hibás beállítások?)");

        progress.close()
        return False
    else:
        return True

def build_torrent_sub_directory(video_url, videoname):
    video_url = base64.b64decode(video_url)
    #sys.stderr.write('build_torrent_sub_directory: ' + video_url)
    video_url = video_url.replace('action=details', 'action=download')
    video_url = video_url.replace('https', 'http')
    #sys.stderr.write('torrent file url: ' + video_url)
    
    torrentData = load(video_url)
    content = session.get(video_url, stream=True)
    content.raw.decode_content = True
    output = open(torrentPath + 'mytorrent.torrent', 'wb')
    shutil.copyfileobj(content.raw, output) 
    output.close()

    info = libtorrent.torrent_info(torrentPath + 'mytorrent.torrent')
    
    for x in range(0, info.num_files()):
        file_entry = info.file_at(x)
        localurl = sys.argv[0]+'?mode=playTorrent&videoName=' + videoname + '&movieURL=' + video_url + '&fileToPlay=' + file_entry.path
        li = xbmcgui.ListItem(os.path.basename(file_entry.path).decode('utf-8'))
        #sys.stderr.write('file_entry.path: ' + file_entry.path)
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=False)
        
    xbmcplugin.endOfDirectory(addon_handle)
    return 

def build_main_directory():
    localurl = sys.argv[0]+'?mode=changeDir&dirName=Ajanlo'
    li = xbmcgui.ListItem('Ajánló')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=Kereses'
    li = xbmcgui.ListItem('Keresés')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=openSetup'
    li = xbmcgui.ListItem('Beállítások')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=False)

    localurl = sys.argv[0]+'?mode=openSetupTorrent'
    li = xbmcgui.ListItem('Torrent beállítások')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(addon_handle)
    return

def build_kereso_to_subdir(keresoUrl):
    if (keresoUrl is None):
        return
    
    if ('mire=' not in keresoUrl):
        kb=xbmc.Keyboard('', 'Keresés, ha mindent szeretnél látni hagy üresen!', False)
        kb.doModal()
        if (kb.isConfirmed()):
            searchText = kb.getText()
            searchText = urllib.quote_plus(searchText)
            #sys.stderr.write('kereő URL: ' + baseUrl + keresoUrl + '&mire=' + searchText)
            url_content = load(baseUrl + keresoUrl + '&mire=' + searchText.replace(' ', '+'))
        else:
            return
    else:
        url_content = load(baseUrl + '/' + keresoUrl)
        
    torrentURL = re.compile('<div class="box_nev2">(.*?)<div style="clear:both;">', re.MULTILINE | re.DOTALL).findall(url_content)
    
    hParser = HTMLParser.HTMLParser()
    if (len(torrentURL) > 0):
        for x in range(0, len(torrentURL)):
            #sys.stderr.write('torrentURL[x]: ' + torrentURL[x])
            egyTorrent = re.compile('href="torrents.php.*?id=(.*?)" onclick.*?title="(.*?)".*?mutat\(\'(.*?)\'.*?class="box_meret2">(.*?)<', re.MULTILINE | re.DOTALL).findall(torrentURL[x])
            if (len(egyTorrent) > 0):
                localurl = sys.argv[0]+'?mode=listTorrent&videoName=' + egyTorrent[0][1] + '&movieURL=' + base64.b64encode(hParser.unescape(baseUrl + "/torrents.php?action=details&id=" + egyTorrent[0][0]))
                urllib.urlretrieve(egyTorrent[0][2].replace("'",""), torrentPath + "/" + egyTorrent[0][1] + ".png")
                li = xbmcgui.ListItem("(" + egyTorrent[0][3].decode('utf-8') + ") " + egyTorrent[0][1].decode('utf-8'), thumbnailImage=torrentPath + "/" + egyTorrent[0][1] + ".png")
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(addon_handle)

    return

def build_sub_directory(subDir, tag):
    #RSS torrent
    hParser = HTMLParser.HTMLParser()
    
    if (subDir[0] == 'Ajanlo'):
        localurl = sys.argv[0]+'?mode=changeDir&dirName=AjanloFilm'
        li = xbmcgui.ListItem('Film ajánló')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        localurl = sys.argv[0]+'?mode=changeDir&dirName=AjanloSorozat'
        li = xbmcgui.ListItem('Sorozat ajánló')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
        
        xbmcplugin.endOfDirectory(addon_handle)

    if (subDir[0] == 'AjanloFilm'):
        url_content = load(baseUrl + '/recommended.php')
        filmSorozat = re.compile('<a name="film">&nbsp;</a>(.*?)<a name="sorozat">&nbsp;</a>', re.MULTILINE | re.DOTALL).findall(url_content)
        ajanloList = re.compile('<a href="(.*?)".*?<img src="(.*?)".*?title="(.*?)"', re.MULTILINE).findall(filmSorozat[0])

        if (len(ajanloList) > 0):
            for x in range(0, len(ajanloList)):
                #sys.stderr.write("thumbnailImage: " + torrentPath + "/" + ajanloList[x][2] + ".png")
                urllib.urlretrieve(ajanloList[x][1], torrentPath + "/" + ajanloList[x][2] + ".png")

                localurl = sys.argv[0]+'?mode=listTorrent&videoName=' + ajanloList[x][2] + '&movieURL=' + base64.b64encode(hParser.unescape(baseUrl + "/" + ajanloList[x][0]))
                li = xbmcgui.ListItem(ajanloList[x][2].decode('utf-8'), thumbnailImage=torrentPath + "/" + ajanloList[x][2] + ".png")
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle)

    if (subDir[0] == 'AjanloSorozat'):
        url_content = load(baseUrl + '/recommended.php')
        filmSorozat = re.compile('<a name="sorozat">&nbsp;</a>(.*?)<a name="jatek">&nbsp;</a>', re.MULTILINE | re.DOTALL).findall(url_content)
        ajanloList = re.compile('<a href="(.*?)".*?<img src="(.*?)".*?title="(.*?)"', re.MULTILINE).findall(filmSorozat[0])

        if (len(ajanloList) > 0):
            for x in range(0, len(ajanloList)):
                #sys.stderr.write("thumbnailImage: " + torrentPath + "/" + ajanloList[x][2] + ".png")
                urllib.urlretrieve(ajanloList[x][1], torrentPath + "/" + ajanloList[x][2] + ".png")

                localurl = sys.argv[0]+'?mode=listTorrent&videoName=' + ajanloList[x][2] + '&movieURL=' + base64.b64encode(hParser.unescape(baseUrl + "/" + ajanloList[x][0]))
                li = xbmcgui.ListItem(ajanloList[x][2].decode('utf-8'), thumbnailImage=torrentPath + "/" + ajanloList[x][2] + ".png")
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle)

    if (subDir[0] == 'Kereses'):
        localurl = sys.argv[0]+'?mode=changeDir&dirName=FilmHUN'
        li = xbmcgui.ListItem('Film - HUN')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        localurl = sys.argv[0]+'?mode=changeDir&dirName=SorozatHUN'
        li = xbmcgui.ListItem('Sorozat - HUN')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        localurl = sys.argv[0]+'?mode=changeDir&dirName=FilmENG'
        li = xbmcgui.ListItem('Film - ENG')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        localurl = sys.argv[0]+'?mode=changeDir&dirName=SorozatENG'
        li = xbmcgui.ListItem('Sorozat - ENG')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        localurl = sys.argv[0]+'?mode=changeDir&dirName=XXX'
        li = xbmcgui.ListItem('XXX')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle)

    if (subDir[0] == 'FilmHUN'):
        if (tag == None):
            for x in range(0, len(tags)):
                localurl = sys.argv[0]+'?mode=changeDir&dirName=FilmHUN&tag=' + tags[x]
                li = xbmcgui.ListItem(tags[x])
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
            xbmcplugin.endOfDirectory(addon_handle)
        else:
            if (tag[0] == 'minden'):
                build_kereso_to_subdir('/torrents.php?tipus=kivalasztottak_kozott&kivalasztott_tipus=' + filmHUNtipus) #xvid_hun,dvd_hun,dvd9_hun,hd_hun')
            else:
                build_kereso_to_subdir('/torrents.php?tipus=kivalasztottak_kozott&tags=' + tag[0] + '&kivalasztott_tipus=' + filmHUNtipus) #xvid_hun,dvd_hun,dvd9_hun,hd_hun')
            xbmcplugin.endOfDirectory(addon_handle)

    if (subDir[0] == 'SorozatHUN'):
        if (tag == None):
            for x in range(0, len(tags)):
                localurl = sys.argv[0]+'?mode=changeDir&dirName=SorozatHUN&tag=' + tags[x]
                li = xbmcgui.ListItem(tags[x])
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
            xbmcplugin.endOfDirectory(addon_handle)
        else:
            if (tag[0] == 'minden'):
                build_kereso_to_subdir('/torrents.php?tipus=kivalasztottak_kozott&kivalasztott_tipus=' + sorozatHUNtipus) #xvid_hun,dvd_hun,dvd9_hun,hd_hun')
            else:
                build_kereso_to_subdir('/torrents.php?tipus=kivalasztottak_kozott&tags=' + tag[0] + '&kivalasztott_tipus=' + sorozatHUNtipus) #xvid_hun,dvd_hun,dvd9_hun,hd_hun')
            xbmcplugin.endOfDirectory(addon_handle)

    if (subDir[0] == 'FilmENG'):
        if (tag == None):
            for x in range(0, len(tags)):
                localurl = sys.argv[0]+'?mode=changeDir&dirName=FilmENG&tag=' + tags[x]
                li = xbmcgui.ListItem(tags[x])
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
            xbmcplugin.endOfDirectory(addon_handle)
        else:
            if (tag[0] == 'minden'):
                build_kereso_to_subdir('/torrents.php?tipus=kivalasztottak_kozott&kivalasztott_tipus=' + filmENGtipus) #xvid_hun,dvd_hun,dvd9_hun,hd_hun')
            else:
                build_kereso_to_subdir('/torrents.php?tipus=kivalasztottak_kozott&tags=' + tag[0] + '&kivalasztott_tipus=' + filmENGtipus) #xvid_hun,dvd_hun,dvd9_hun,hd_hun')
            xbmcplugin.endOfDirectory(addon_handle)

    if (subDir[0] == 'SorozatENG'):
        if (tag == None):
            for x in range(0, len(tags)):
                localurl = sys.argv[0]+'?mode=changeDir&dirName=SorozatENG&tag=' + tags[x]
                li = xbmcgui.ListItem(tags[x])
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
            xbmcplugin.endOfDirectory(addon_handle)
        else:
            if (tag[0] == 'minden'):
                build_kereso_to_subdir('/torrents.php?tipus=kivalasztottak_kozott&kivalasztott_tipus=' + sorozatENGtipus) #xvid_hun,dvd_hun,dvd9_hun,hd_hun')
            else:
                build_kereso_to_subdir('/torrents.php?tipus=kivalasztottak_kozott&tags=' + tag[0] + '&kivalasztott_tipus=' + sorozatENGtipus) #xvid_hun,dvd_hun,dvd9_hun,hd_hun')
            xbmcplugin.endOfDirectory(addon_handle)

    if (subDir[0] == 'XXX'):
        build_kereso_to_subdir('/torrents.php?tipus=kivalasztottak_kozott&kivalasztott_tipus=' + filmXXXtipus) #xxx_xvid,xxx_dvd,xxx_hd')
        xbmcplugin.endOfDirectory(addon_handle)

    return

# main...
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(addon_handle, 'movies')

mode = args.get('mode', None)
subDir = args.get('dirName', None)
tag = args.get('tag', None)
movieURL = args.get('movieURL', None)
videoName = args.get('videoName', None)
fileToPlay = args.get('fileToPlay', None)
thumbnail = args.get('thumbnail', None)
stype = args.get('stype', None)

if mode is None:
    ##sys.stderr.write('mode: NONE \n')
    build_main_directory()
elif mode[0] == 'changeDir':
    ##sys.stderr.write('mode: ' + mode[0] + ', subDir: ' + subDir[0] + '\n')
    build_sub_directory(subDir, tag)
elif mode[0] == 'playTorrent':
    send_to_downloader()
    play_torrenturl(fileToPlay[0], movieURL[0], videoName[0], None, tmptorles, elonySzazalek, torrentFullDownload)
elif mode[0] == 'listTorrent':
    build_torrent_sub_directory(movieURL[0], videoName[0])
elif mode[0] == 'openSetup':
    addon.openSettings()
elif mode[0] == 'openSetupTorrent':
    torrentAddon.openSettings()
