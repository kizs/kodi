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
libtorrent=get_libtorrent()

torrentAddon = xbmcaddon.Addon(id='service.kizstorrent')
addon = xbmcaddon.Addon(id='plugin.video.bithumentv')
thisAddonDir = xbmc.translatePath(addon.getAddonInfo('path')).decode('utf-8')
sys.path.append(os.path.join(thisAddonDir, 'resources', 'lib'))

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

appName = 'BHTV'
logined = False

xbmcplugin.setContent(addon_handle, 'movies')
baseUrl = 'http://bithumen.be'

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

def newSession():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.6 Safari/537.36',
    })
    return s

session = newSession()

def doLogin():
    global session
    postdata = {'username':addon.getSetting('felhasznalonev'),
                'password':addon.getSetting('jelszo'),
                'megjegyez':'on'}

    if os.path.isfile(torrentPath + 'my.cookies'): 
        #sys.stderr.write("load Session")
        cookieFile = open(torrentPath + 'my.cookies')
        cookies = requests.utils.cookiejar_from_dict(pickle.load(cookieFile))
        session.cookies = cookies

    content = session.post(baseUrl + '/userdetails.php').text
    sikeres = re.compile("Nem vagy bejelentkezve", re.MULTILINE|re.DOTALL).findall(content.encode('utf-8'))
    if (len(sikeres) > 0):
        #sys.stderr.write("doLogin")
        content = session.post(baseUrl + '/takelogin.php', data=postdata).text
        sikeres = re.compile("Helytelen felhasználónév, vagy jelszó", re.MULTILINE|re.DOTALL).findall(content.encode('utf-8'))
        if (len(sikeres) > 0):
            logined = False
            dialog = xbmcgui.Dialog()
            dialog.ok("Hiba!", "Helytelen felhasználónév, vagy jelszó!", "Esetleg megjelent az I'm not a robot captcha.", "Várj egy ideig, esetleg próbáld meg böngészőből!")
            sys.exit()
        else:
            logined = True
            cookieFile = open(torrentPath + 'my.cookies', 'w')
            pickle.dump(requests.utils.dict_from_cookiejar(session.cookies), cookieFile)

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
        if post:
            r = session.post(url, data=post, verify=False, timeout=10).text
        else:
            r = session.get(url, verify=False).text

    return r.encode('utf-8')

def send_to_downloader():
    if transmission_send == 'true':
        progress = xbmcgui.DialogProgress()
        progress.create(appName, 'Calling Transmission...')

        #sys.stderr.write('Torrent send to Transmission (' + transmission_username + ":" + transmission_password + "@" + transmission_url + ')')
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
        #sys.stderr.write('Torrent send to uTorrent')
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

def play_videourl(video_url, videoname, thumbnail):
    #sys.stderr.write('play_videourl - video_url: ' + video_url + ', videoname: ' + videoname + '\n')
    content = load(video_url);
    embeded_url = re.compile('file:.*?"(.*?)"', re.MULTILINE|re.DOTALL).findall(content)
    
    if (len(embeded_url) == 0):
        embeded_url = re.compile('<source src="(.*?)"', re.MULTILINE|re.DOTALL).findall(content)

    videoitem = xbmcgui.ListItem(label=videoname, thumbnailImage=thumbnail)
    videoitem.setInfo(type='Video', infoLabels={'Title': videoname})
    xbmc.Player().play(embeded_url[0], videoitem)
    return

def build_main_directory():
    localurl = sys.argv[0]+'?mode=changeDir&dirName=Ajanlo'
    li = xbmcgui.ListItem('Ajánló')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=Kereses'
    li = xbmcgui.ListItem('Keresés')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=OnlineTV'
    li = xbmcgui.ListItem('Online TV')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
    
    localurl = sys.argv[0]+'?mode=changeDir&dirName=RSSFeed'
    li = xbmcgui.ListItem('RSSFeed')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
    
    localurl = sys.argv[0]+'?mode=openSetup'
    li = xbmcgui.ListItem('Beállítások')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=False)

    localurl = sys.argv[0]+'?mode=openSetupTorrent'
    li = xbmcgui.ListItem('Torrent beállítások')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(addon_handle)
    return

def build_ajanlo_to_subdir(torrentUrl):
    #sys.stderr.write('url: ' + baseUrl + torrentUrl)
    url_content = load(baseUrl + torrentUrl)
    
    torrentHTML = re.compile('<a href="(.*?)".*?>Letöltés.*?\n.*?<div style=.*?>(.*?)<', re.MULTILINE).findall(url_content)
    if (len(torrentHTML) == 0):
        torrentHTML = re.compile('href="download.php(.*?)">(.*?)<', re.MULTILINE).findall(url_content)

    # torrent file: torrentHTML[0]
    # leírás: torrentHTML[1]
    torrentKep = re.compile("class='magpic' style=''><img src='(.*?)'", re.MULTILINE).findall(url_content)
    torrentNeve = re.compile("</div>(.*?)</h1>", re.MULTILINE).findall(url_content)
    torrentMeret = re.compile('Méret</td><td valign="top" align=left >(.*?) \(', re.MULTILINE).findall(url_content)

    if (len(torrentHTML) > 0):
        #sys.stderr.write('torrentNeve[0][0]: ' + torrentNeve[0])
        localurl = sys.argv[0]+'?mode=listTorrent&videoName=' + torrentNeve[0] + '&movieURL=' + baseUrl + "/" + torrentHTML[0][0]
        if len(torrentKep) > 0:
            li = xbmcgui.ListItem("(" + torrentMeret[0].decode('utf-8') + ") " + torrentNeve[0].decode('utf-8'), iconImage=torrentKep[0])
        else:
            li = xbmcgui.ListItem("(" + torrentMeret[0].decode('utf-8') + ") " + torrentNeve[0].decode('utf-8'), iconImage=None)
        infoLabels={'plot':torrentHTML[0][1]}
        li.setInfo(type="Video", infoLabels=infoLabels)
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
        
                    
#    torrentHTML = re.compile('<a href="(.*?)".*?>Letöltés.*?\n.*?<div style=.*?>(.*?)<', re.MULTILINE).findall(url_content)
#    if (len(torrentHTML) > 0):
#        localurl = sys.argv[0]+'?mode=listTorrent&videoName=' + ajanloList[2] + '&movieURL=' + baseUrl + "/" + torrentHTML[0][0]
#        li = xbmcgui.ListItem(ajanloList[2].decode('utf-8') + ajanloList[3].decode('utf-8'), iconImage=ajanloList[1])
#        infoLabels={'plot':torrentHTML[0][1]}
#        li.setInfo(type="Video", infoLabels=infoLabels)
#        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
    
    return

def build_kereso_to_subdir(keresoUrl):
    if (keresoUrl is None):
        return
    
    if ('search=' not in keresoUrl):
        kb=xbmc.Keyboard('', 'Keresés', False)
        kb.doModal()
        if (kb.isConfirmed()):
            searchText = kb.getText()
            #sys.stderr.write('kereő URL: ' + baseUrl + keresoUrl + '&search=' + urllib.quote(searchText))
            url_content = load(baseUrl + keresoUrl + '&search=' + searchText.replace(' ', '+'))
        else:
            return
    else:
        #sys.stderr.write('keresoUrl: ' + baseUrl + '/' + keresoUrl)
        url_content = load(baseUrl + '/' + keresoUrl)
        
    torrentURL = re.compile('<a href="details.php(.*?)".*?<b>').findall(url_content)
    visszaURL = re.compile('<a href="(.*?)"><b>&lt;&lt;&nbsp;Vissza</b>').findall(url_content)
    tovabbURL = re.compile('&nbsp;<a href="(.*?)"><b>Tovább&nbsp;&gt;&gt;</b>').findall(url_content)
    
    #sys.stderr.write('len(torrentURL): ' + str(len(torrentURL)))
    if (len(torrentURL) > 0):
        for x in range(0, len(torrentURL)):
            #sys.stderr.write('x: ' + str(x))
            build_ajanlo_to_subdir('/details.php' + torrentURL[x])
            #myThread = threading.Thread(target=build_ajanlo_to_subdir, args=('/details.php' + torrentURL[x], ))
            #myThread.start()
            #myThread.join(60)

    hParser = HTMLParser.HTMLParser()
    
    if (len(visszaURL) > 0):
        localurl = sys.argv[0]+'?mode=nextPrev&' + urllib.urlencode({'nextPrevURL' : base64.b64encode(hParser.unescape(visszaURL[0]))})
        li = xbmcgui.ListItem('<< Vissza'.decode('utf-8'))
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    if (len(tovabbURL) > 0):
        #sys.stderr.write('tovabbURL[0]: ' + tovabbURL[0])
        localurl = sys.argv[0]+'?mode=nextPrev&' + urllib.urlencode({'nextPrevURL' : base64.b64encode(hParser.unescape(tovabbURL[0]))})
        li = xbmcgui.ListItem('Tovább >>'.decode('utf-8'))
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(addon_handle)

    return

def build_sub_directory(subDir):
    #RSS torrent
    if (subDir[0] == 'RSSFeed'):
        url_content = load(baseUrl + '/wiki/Linkek')
        egyeniRSSUrl = re.compile('Mások által ajánlott torrentek(.*?)<!--right col-->', re.MULTILINE).findall(url_content)
        if (len(egyeniRSSUrl) > 0):
            url_content = load(baseUrl + egyeniRSSUrl[0])
            RSSList = re.compile('<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>', re.MULTILINE|re.DOTALL).findall(url_content)
            if (len(RSSList) > 0):
                for x in range(0, len(RSSList)):
                    localurl = sys.argv[0]+'?mode=listTorrent&videoName=' + RSSList[x][0] + '&movieURL=' + RSSList[x][1]
                    li = xbmcgui.ListItem(RSSList[x][0].decode('utf-8'))
                    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle)
    
    
    
    if (subDir[0] == 'Ajanlo'):
        localurl = sys.argv[0]+'?mode=changeDir&dirName=AjanloFilm'
        li = xbmcgui.ListItem('Film ajánló')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        localurl = sys.argv[0]+'?mode=changeDir&dirName=AjanloSorozat'
        li = xbmcgui.ListItem('Sorozat ajánló')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle)

    if (subDir[0] == 'AjanloFilm'):
        url_content = load(baseUrl + '/community.php?cat=movie')
        ajanloList = re.compile("<a href=.(.*?).><img src='(.*?)' style='margin: 2px.*?\n.*?title=..*>(.*?)</a>(.*?)</h2>", re.MULTILINE).findall(url_content)
        if (len(ajanloList) > 0):
            for x in range(0, len(ajanloList)):
                myThread = threading.Thread(target=build_ajanlo_to_subdir, args=(ajanloList[x][0], ))
                myThread.start()
                #build_ajanlo_to_subdir(baseUrl + AjanloList[x][0])

            for x in range(0, len(ajanloList)):
                myThread.join()
        xbmcplugin.endOfDirectory(addon_handle)

    if (subDir[0] == 'AjanloSorozat'):
        url_content = load(baseUrl + '/community.php?cat=serie')
        ajanloList = re.compile("<a href=.(.*?).><img src='(.*?)' style='margin: 2px.*?\n.*?title=..*>(.*?)</a>(.*?)</h2>", re.MULTILINE).findall(url_content)
        if (len(ajanloList) > 0):
            for x in range(0, len(ajanloList)):
                myThread = threading.Thread(target=build_ajanlo_to_subdir, args=(ajanloList[x][0], ))
                myThread.start()
                #build_ajanlo_to_subdir(baseUrl + AjanloList[x][0])

            for x in range(0, len(ajanloList)):
                myThread.join()
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
        build_kereso_to_subdir('/browse.php?c23=1&c24=1&c25=1&c37=1&c33=1&genre=0')
        xbmcplugin.endOfDirectory(addon_handle)

    if (subDir[0] == 'SorozatHUN'):
        build_kereso_to_subdir('/browse.php?c7=1&c41=1&genre=0')
        xbmcplugin.endOfDirectory(addon_handle)

    if (subDir[0] == 'FilmENG'):
        build_kereso_to_subdir('/browse.php?c19=1&c20=1&c5=1&c39=1&c40=1&genre=0')
        xbmcplugin.endOfDirectory(addon_handle)

    if (subDir[0] == 'SorozatENG'):
        build_kereso_to_subdir('/browse.php?c26=1&c42=1&genre=0')
        xbmcplugin.endOfDirectory(addon_handle)

    if (subDir[0] == 'XXX'):
        build_kereso_to_subdir('/browse.php?c30=1&c34=1&genre=0')
        xbmcplugin.endOfDirectory(addon_handle)

    if (subDir[0] == 'OnlineTV'):
        url_content = load(baseUrl + '/tv.php')
        tv_tablazat = re.compile('<td class=colhead align=left colspan=3>(.*?)</td>', re.MULTILINE|re.DOTALL).findall(url_content)
        if (len(tv_tablazat) > 0):
            for x in range(0, len(tv_tablazat)):
                #sys.stderr.write(tv_tablazat[x] + '\n');
                localurl = sys.argv[0]+"?mode=changeDir&dirName=" + urllib.quote_plus(tv_tablazat[x])
                li = xbmcgui.ListItem(tv_tablazat[x])
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle)

        
    list = ['Ajanlo', 'RSSFeed', 'Kereses', 'FilmHUN', 'SorozatHUN', 'FilmENG', 'SorozatENG', 'XXX', 'OnlineTV'];        
    if (subDir[0] not in list):
        #TV adások
        url_content = load(baseUrl + '/tv.php')
        film_tablazat = re.compile('<td class=colhead align=left colspan=3>' + subDir[0].replace('+', '.') + '</td>(.*?)<td class=colhead align=left colspan=3>', re.MULTILINE|re.DOTALL).findall(url_content)
    
        if (len(film_tablazat) == 0):
            #sys.stderr.write('film_tablazat: NULL\n')
            #sys.stderr.write('<td class=colhead align=left colspan=3>' + subDir[0].replace('+', '.') + '</td>(.*?)</table>')
            film_tablazat = re.compile('<td class=colhead align=left colspan=3>' + subDir[0].replace('+', '.') + '</td>(.*?)</table>', re.MULTILINE|re.DOTALL).findall(url_content)
        
        if (len(film_tablazat) > 0):
            #sys.stderr.write('film_tablazat: ' + film_tablazat[0] + '\n')
            filmek = re.compile('<td align="left" ><b>(.*?)</b></td>.*?<a href="(.*?)">Flash</a>', re.MULTILINE|re.DOTALL).findall(film_tablazat[0])
            ikonTitle = re.compile('<td align="left" ><img src="(.*?)" title="(.*?)".*?<a href="(.*?)">', re.MULTILINE|re.DOTALL).findall(film_tablazat[0])
            
            if (len(filmek) > 0):
                for x in range(0, len(filmek)):
                    localurl = sys.argv[0]+'?mode=playMovie' + '&videoName=' + filmek[x][0] + '&movieURL=' + filmek[x][1]
                    li = xbmcgui.ListItem(filmek[x][0].decode('utf-8'))
                    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=False)
    
            if (len(ikonTitle) > 0):
                for x in range(0, len(ikonTitle)):
                    localurl = sys.argv[0]+'?mode=playMovie&movieURL=' + ikonTitle[x][2] + '&videoName=' + ikonTitle[x][1] + '&thumbnail=' + ikonTitle[x][0]
                    li = xbmcgui.ListItem(label = ikonTitle[x][1].decode('utf-8'), iconImage=ikonTitle[x][0])
                    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=False)
        xbmcplugin.endOfDirectory(addon_handle)

    return

# main...
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(addon_handle, 'movies')

mode = args.get('mode', None)
subDir = args.get('dirName', None)
nextPrevURL = args.get('nextPrevURL', None)
movieURL = args.get('movieURL', None)
videoName = args.get('videoName', None)
fileToPlay = args.get('fileToPlay', None)
thumbnail = args.get('thumbnail', None)
stype = args.get('stype', None)

if mode is None:
    #sys.stderr.write('mode: NONE \n')
    build_main_directory()
elif mode[0] == 'changeDir':
    #sys.stderr.write('mode: ' + mode[0] + ', subDir: ' + subDir[0] + '\n')
    build_sub_directory(subDir)
elif mode[0] == 'nextPrev':
    if (nextPrevURL is not None):
        build_kereso_to_subdir(base64.b64decode(nextPrevURL[0]))
elif mode[0] == 'playTorrent':
    send_to_downloader()
    play_torrenturl(fileToPlay[0], movieURL[0], videoName[0], None, tmptorles, elonySzazalek, torrentFullDownload)
elif mode[0] == 'listTorrent':
    build_torrent_sub_directory(movieURL[0], videoName[0])
elif mode[0] == 'openSetup':
    addon.openSettings()
elif mode[0] == 'openSetupTorrent':
    torrentAddon.openSettings()
elif mode[0] == 'playMovie':
    if (thumbnail is None):
        if (stype is None):
            #sys.stderr.write('stype is None\n')
            play_videourl(baseUrl + '/' + movieURL[0] + '&stype=flash', videoName[0], None)
        else:
            #sys.stderr.write('stype: ' + stype[0] + '\n')
            play_videourl(baseUrl + '/' + movieURL[0] + '&stype=' + stype[0], videoName[0], None)
    else: 
        if (stype is None):
            #sys.stderr.write('stype is None\n')
            play_videourl(baseUrl + '/' + movieURL[0] + '&stype=flash', videoName[0], thumbnail[0])
        else:
            #sys.stderr.write('stype: ' + stype[0] + '\n')
            play_videourl(baseUrl + '/' + movieURL[0] + '&stype=' + stype[0], videoName[0], thumbnail[0])
