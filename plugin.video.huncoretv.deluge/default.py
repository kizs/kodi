#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import HTMLParser
import base64
import os
import requests, requests.utils, pickle
import shutil
import time
import urllib
import urlparse

import xbmcaddon
import xbmcgui
import xbmcplugin

import xbmc

import sys
import json
import re

from resources.lib.client import DelugeRPCClient


addon = xbmcaddon.Addon(id='plugin.video.huncoretv.deluge')
thisAddonDir = xbmc.translatePath(addon.getAddonInfo('path')).decode('utf-8')
sys.path.append(os.path.join(thisAddonDir, 'resources', 'lib'))

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

tags = ["minden","vígjáték","dráma","életrajz","akció","romantikus","dokumentumfilm","kaland","animáció","thriller","családi","bűnügyi","rövidfilm","musical","sci-fi","misztikus","háborús","western","horror","történelmi","sport","zene","ismeretterjesztő","valóságshow","3D","fantasy"]
appName = 'HUNCoreTV'
logined = False

xbmcplugin.setContent(addon_handle, 'movies')
baseUrl = 'https://ncore.cc'

felhasznalo = addon.getSetting('felhasznalonev')
jelszo = addon.getSetting('jelszo')
torrentPath = addon.getSetting('torrentPath')
deluge_url = addon.getSetting('deluge_url')
deluge_port = int(addon.getSetting('deluge_port'))
deluge_username = addon.getSetting('deluge_username')
deluge_password = addon.getSetting('deluge_password')
delugePath = addon.getSetting('delugePath')

if (felhasznalo == "" or jelszo == "" or torrentPath == "" or deluge_url == "" or delugePath == ""):
    dialog = xbmcgui.Dialog()
    dialog.ok("Hiba!", "Nem végezted el a beállításokat!", "", "")
    addon.openSettings()
    sys.exit()


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

    torrentFileContent = open(torrentPath + 'mytorrent.torrent')
    paths = getTorrentFiles(torrentFileContent)
    torrentFileContent.close();

    for x in range(0, len(paths)):
        file_entry = paths[x]
        localurl = sys.argv[0]+'?mode=playTorrent&videoName=' + videoname + '&movieURL=' + video_url + '&fileToPlay=' + file_entry
        li = xbmcgui.ListItem(os.path.basename(file_entry).decode('utf-8'))
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

def tokenize(text, match=re.compile("([idel])|(\d+):|(-?\d+)").match):
    i = 0
    while i < len(text):
        m = match(text, i)
        s = m.group(m.lastindex)
        i = m.end()
        if m.lastindex == 2:
            yield "s"
            yield text[i:i+int(s)]
            i = i + int(s)
        else:
            yield s

def decode_item(next, token):
    if token == "i":
        # integer: "i" value "e"
        data = int(next())
        if next() != "e":
            raise ValueError
    elif token == "s":
        # string: "s" value (virtual tokens)
        data = next()
    elif token == "l" or token == "d":
        # container: "l" (or "d") values "e"
        data = []
        tok = next()
        while tok != "e":
            data.append(decode_item(next, tok))
            tok = next()
        if token == "d":
            data = dict(zip(data[0::2], data[1::2]))
    else:
        raise ValueError
    return data

def decodeTorrent(text):
    try:
        src = tokenize(text)
        data = decode_item(src.next, src.next())
        for token in src: # look for more tokens
            raise SyntaxError("trailing junk")
    except (AttributeError, ValueError, StopIteration):
        raise SyntaxError("syntax error")
    return data

def getTorrentFiles(torrentFileContent):
    filePaths = []
    eredmeny = decodeTorrent(torrentFileContent.read())
    if "files" in eredmeny["info"]:
        for x in range (0, len(eredmeny["info"]["files"])):
            filePath = ""
            for y in range (0, len(eredmeny["info"]["files"][x]["path"])):
                filePath = filePath + eredmeny["info"]["files"][x]["path"][y] + "/"
            filePaths.append(filePath[0:len(filePath)-1]);
    if eredmeny["info"]["name"]:
        filePaths.append(eredmeny["info"]["name"]);
    
    return filePaths

def getTorrentFileStatus(torrent_file):
    retVal=[]
    retVal.append("")
    retVal.append(int(-1))

    try:
        delugeClient = DelugeRPCClient(deluge_url, deluge_port, deluge_username, deluge_password)
        delugeClient.connect()
        eredmeny = delugeClient.call('core.get_torrents_status', {}, ['name', 'total_size', 'total_done', 'progress', 'files', 'download_payload_rate'])
    except:
        dialog = xbmcgui.Dialog().ok(appName, "Hiba történt a Deluge megszólításakor!", str(sys.exc_info()[0]) + "-" + str(sys.exc_info()[1]), "(Esetleg hibás beállítások?)");
        return retVal
    
    for key in eredmeny:
        retVal[0]=str(int(eredmeny[key]['download_payload_rate'])/1000) + ' KB/s'
        fileLength = eredmeny[key]['total_size']
        fileBytesCompleted = eredmeny[key]['total_done']
        files=eredmeny[key]['files']
        for x in range(0, len(files)) :
            fileName = files[x]['path'].encode('utf-8')
            if (fileName.encode('utf-8').replace('\\','/') == torrent_file.replace('\\','/')):
                if (fileLength == fileBytesCompleted):
                    retVal[1]=int(100)
                else:
                    retVal[1]=int(fileBytesCompleted/(fileLength/100))
                return retVal
                  
    return retVal

def play_torrenturl(fileToPlay, blob, thumbnail):
    torrentName = decodeTorrent(blob)["info"]["name"]
    torrent_content = base64.b64encode(blob)
        
    try:
        delugeClient = DelugeRPCClient(deluge_url, deluge_port, deluge_username, deluge_password)
        delugeClient.connect()
        eredmeny = delugeClient.call('core.add_torrent_file', torrentName, torrent_content, [])
    except:
        dialog = xbmcgui.Dialog().ok(appName, "Hiba történt a Deluge megszólításakor!", str(sys.exc_info()[0]) + "-" + str(sys.exc_info()[1]), "(Esetleg hibás beállítások?)");
        return

    
    fullName = torrentName + "/" + fileToPlay
    sys.stderr.write('getTorrentFileStatus ' + torrentName + "/" + fileToPlay + '\n')
    download_percent = getTorrentFileStatus(fullName.encode("utf-8"))[1]
    sys.stderr.write('download_percent ' + str(download_percent) + '\n')
    xbmc.Player().stop()
    progress = xbmcgui.DialogProgress()
    progress.create('Progress: ' + fileToPlay)
    while (download_percent < 100):
        s = getTorrentFileStatus(fullName)
        download_percent = s[1]
        progress.update(download_percent, 'Download rate: ' + str(s[0]), str(download_percent) + '%')

        if (progress.iscanceled()):
            break
        
        time.sleep(1)

    progress.close()
    if (download_percent >= 100):
        sys.stderr.write('Playing ' + delugePath + '/' + torrentName + "/" + fileToPlay + '\n')
        play_torrent(torrentName, thumbnail, delugePath + '/' + torrentName + "/" + fileToPlay)
    return

def play_torrent(videoname, thumbnail, filePath):
    videoitem = xbmcgui.ListItem(label=videoname, thumbnailImage=thumbnail)
    videoitem.setInfo(type='Video', infoLabels={'Title': videoname})
    xbmc.Player().play(filePath, videoitem)
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
    f = open(torrentPath + 'mytorrent.torrent', 'rb')
    blob = f.read()
    f.close()
    play_torrenturl(fileToPlay[0], blob, None)
elif mode[0] == 'listTorrent':
    build_torrent_sub_directory(movieURL[0], videoName[0])
elif mode[0] == 'openSetup':
    addon.openSettings()
