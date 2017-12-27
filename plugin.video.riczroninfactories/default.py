#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import HTMLParser
import os
import re
import requests, requests.utils, pickle
import sys
import time
import urllib
import urlparse
from contextlib import closing

import xbmcaddon
import xbmcgui
import xbmcplugin

import logging
from multiprocessing.dummy import Pool as ThreadPool

import urlresolver

import json
from resources.lib.moviedb import Moviedb
from resources.lib.movie import Movie
from sets import Set

dbProjectCompleted='ProjectCompleted'
dbProjectActual='ProjectActual'

addon = xbmcaddon.Addon(id='plugin.video.riczroninfactories')

appName = 'riczroninfactories'
logined = False
hParser = HTMLParser.HTMLParser()

baseUrl = 'http://riczroninfactories.eu/'

felhasznalo = addon.getSetting('felhasznalonev')
jelszo = addon.getSetting('jelszo')
tmpDir = addon.getSetting('tmpdir')
if (felhasznalo == "" or jelszo == "" or tmpDir == ""):
    pgdialog = xbmcgui.Dialog()
    pgdialog.ok("Hiba!", "Nem végezted el a beállításokat!", "", "")
    addon.openSettings()
    sys.exit()

def newSession():
    s = requests.Session()
    s.headers.update({#'Host': 's4.histats.com',
              'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0',
              'Accept': '*/*',
              'Accept-Language': 'hu-HU,hu;q=0.8,en-US;q=0.5,en;q=0.3',
              'Accept-Encoding': 'gzip, deflate',
              'Connection': 'keep-alive'})
    
    if os.path.isfile(tmpDir + 'riczroninfactories.cookies'): 
        cookieFile = open(tmpDir + 'riczroninfactories.cookies')
        cookies = requests.utils.cookiejar_from_dict(pickle.load(cookieFile))
        s.cookies = cookies
        cookieFile.close()
    
    s.max_redirects = 120
    return s

session = newSession()

def doLogin():
    #sys.stderr.write('doLogin()')
    global session
    postdata = {'user_name':addon.getSetting('felhasznalonev'),
                'user_pass':addon.getSetting('jelszo'),
                'login':addon.getSetting('Bejelentkezés')
                }

    if os.path.isfile(tmpDir + 'riczroninfactories.cookies'): 
        cookieFile = open(tmpDir + 'riczroninfactories.cookies')
        cookies = requests.utils.cookiejar_from_dict(pickle.load(cookieFile))
        session.cookies = cookies
        cookieFile.close()

    content = session.post(baseUrl + 'news.php', data = postdata).text
    
    if 'LoginForm' in content:
        logined = False
        cookieFile = open(tmpDir + 'riczroninfactories.cookies', 'w')
        pickle.dump(requests.utils.dict_from_cookiejar(session.cookies), cookieFile)
        cookieFile.close();
        pgdialog = xbmcgui.Dialog()
        pgdialog.ok("Hiba!", "Helytelen felhasználónév, vagy jelszó!", "Esetleg megjelent az I'm not a robot captcha.", "Várj egy ideig, esetleg próbáld meg böngészőből!")
        sys.exit()
    else:
        logined = True
        cookieFile = open(tmpDir + 'riczroninfactories.cookies', 'w')
        pickle.dump(requests.utils.dict_from_cookiejar(session.cookies), cookieFile)
        cookieFile.close();

    return

def load(url, post = None):
    global session
    myHeader = {#'Host': 's4.histats.com',
              'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0',
              'Accept': '*/*',
              'Accept-Language': 'hu-HU,hu;q=0.8,en-US;q=0.5,en;q=0.3',
              'Accept-Encoding': 'gzip, deflate',
              'Referer': url,
              'Connection': 'keep-alive'}

    callHttp = True
    while callHttp:
        #sys.stderr.write('load: ' + url.encode('utf-8'))
        try:
            if post:
                r = session.post(url, data=post, verify=False, timeout=10).text
            else:
                r = session.get(url, verify=False).text
            callHttp = False
            if 'LoginForm' in r:
                #sys.stderr.write('Hibás bejelentkezés?')
                #sys.stderr.write(r.encode('utf-8'))
                doLogin()
                if post:
                    r = session.post(url, data=post, verify=False, timeout=10).text
                else:
                    r = session.get(url, verify=False).text
                callHttp = False
        except (requests.exceptions.ReadTimeout) as e:
            sys.stderr.write('load: ReadTimeout')
            time.sleep(3)
            callHttp = True
        except (requests.exceptions.ChunkedEncodingError) as e:
            sys.stderr.write('load: ChunkedEncodingError')
            time.sleep(3)
            callHttp = True
        except (requests.exceptions.ConnectionError) as e:
            sys.stderr.write('load: ConnectionError')
            time.sleep(3)
            callHttp = True
        except AttributeError:
            xbmc.executebuiltin("HIBA: {0}".format(AttributeError.message))
            callHttp = False

    return r.encode('utf-8')

def play_videourl(video_url, videoname, referedUrl):
    global session
    sys.stderr.write('play_videourl: ' + video_url.encode('utf-8'))
    video_url = baseUrl + "infusions/video/video.php" + video_url
    
    #urlresolver.HostedMediaFile(url=hoster_url)
    
    url_content = load(video_url)
    completedList = re.compile('class="indavideo-player".*? src="(.*?)" frameborder').findall(url_content)
    #del url_content
    
    playable_url=''
    if (len(completedList) > 0):
        #sys.stderr.write('vegso video: ' + completedList[0].encode('utf-8'))
        playable_url=completedList[0]
    else:
        #Flash video?
        completedList = re.compile('flashvars="(.*?)".*?src="(.*?)".*?type="application/x-shockwave-flash"').findall(url_content)
        if (len(completedList) > 0):
            playable_url=completedList[0][1] + "?" + completedList[0][0]
        else:
            sys.stderr.write('vegso video: NINCS?')
            #sys.stderr.write(url_content)
            #sys.stderr.write('vegso video: NINCS?')

    if (len(playable_url) > 0):
        hmf = urlresolver.HostedMediaFile(url=playable_url, include_disabled=True, include_universal=False)
        if not hmf:
            sys.stderr.write('Indirect hoster_url not supported by urlresolver: %s' % (playable_url))
        else:
            try:
                stream_url = hmf.resolve()
                #sys.stderr.write('stream_url: ' + stream_url.encode('utf-8'))
                if not stream_url or not isinstance(stream_url, basestring):
                    try: msg = stream_url.msg
                    except: msg = playable_url
                    raise Exception(msg)
            except Exception as e:
                try: msg = str(e)
                except: msg = playable_url
                kodi.notify(msg=i18n('resolve_failed') % (msg), duration=7500)
                return False
    
        videoitem = xbmcgui.ListItem(label=videoname)
        videoitem.setInfo(type='Video', infoLabels={'Title': videoname})
        if not hmf:
            xbmc.Player().play(playable_url, videoitem)
        else:
            xbmc.Player().play(hmf.resolve(), videoitem)
    return

def build_main_directory():
    localurl = sys.argv[0]+'?mode=changeDir&dirName=Befejezett'
    li = xbmcgui.ListItem('Befejezett')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=Aktualis'
    li = xbmcgui.ListItem('Aktuális')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=Kategoria'
    li = xbmcgui.ListItem('Kategóriák')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=Kereses'
    li = xbmcgui.ListItem('Keresés')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=ClearDB'
    li = xbmcgui.ListItem('Adatbázis frissítése')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
    

    xbmcplugin.endOfDirectory(addon_handle)
    return

def build_sub_directory(subDir, category, animeUrl):
    global myMoviedb
    global hParser
    
    if (subDir[0] == 'Kereses'):
        kb=xbmc.Keyboard('', 'Keresés', False)
        kb.doModal()
        if (kb.isConfirmed()):
            searchText = kb.getText()
            for movie in myMoviedb.movies:
                if movie.name.find(searchText.decode('utf-8')) > 0:
                    li = xbmcgui.ListItem(movie.name, iconImage=baseUrl + movie.thumbnailurl, thumbnailImage = baseUrl + movie.thumbnailurl, )
                    info = {
                        'genre': movie.genre,
                        'year': movie.year,
                        'title': movie.title,
                    }
                    li.setInfo('video', info)
                    li.setArt({'thumb': baseUrl + movie.thumbnailurl, 'poster': baseUrl + movie.thumbnailurl, 'fanart': baseUrl + movie.thumbnailurl})
                    xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+movie.url, listitem=li, isFolder=True)            
            xbmcplugin.endOfDirectory(addon_handle)
        return 

    if (subDir[0] == 'Kategoria'):
        categories = Set()
        for movie in myMoviedb.movies:
            for cat in movie.categories:
                categories.add(cat)
        
        categories = sorted(categories)
        
        for cat in categories:
            localurl = sys.argv[0]+'?mode=changeDir&dirName=KategorianBelul&' + urllib.urlencode({'category' : cat}) #.encode('utf-8') 
            li = xbmcgui.ListItem(cat)
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
    
        xbmcplugin.endOfDirectory(addon_handle)
        return 

    if (subDir[0] == 'KategorianBelul'):
        for movie in myMoviedb.movies:
            for cat in movie.categories:
                if cat == category[0]:
                    li = xbmcgui.ListItem(movie.name, iconImage=baseUrl + movie.thumbnailurl, thumbnailImage = baseUrl + movie.thumbnailurl, )
                    info = {
                        'genre': movie.genre,
                        'year': movie.year,
                        'title': movie.title,
                    }
                    li.setInfo('video', info)
                    li.setArt({'thumb': baseUrl + movie.thumbnailurl, 'poster': baseUrl + movie.thumbnailurl, 'fanart': baseUrl + movie.thumbnailurl})
                    xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+movie.url, listitem=li, isFolder=True)            
        xbmcplugin.endOfDirectory(addon_handle)
        return

    if (subDir[0] == 'ClearDB'):
        try:
            os.remove(tmpDir + 'riczroninfactories.db')
        except:
            pass
    
    if (subDir[0] == 'Befejezett'):
        for movie in myMoviedb.movies:
            if movie.projectstatus == dbProjectCompleted.decode('utf-8'):
                li = xbmcgui.ListItem(movie.name, iconImage=baseUrl + movie.thumbnailurl, thumbnailImage = baseUrl + movie.thumbnailurl, )
                info = {
                    'genre': movie.genre,
                    'year': movie.year,
                    'title': movie.title,
                }
                li.setInfo('video', info)
                li.setArt({'thumb': baseUrl + movie.thumbnailurl, 'poster': baseUrl + movie.thumbnailurl, 'fanart': baseUrl + movie.thumbnailurl})
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+movie.url, listitem=li, isFolder=True)            
        
        xbmcplugin.endOfDirectory(addon_handle)
        return 

    if (subDir[0] == 'Aktualis'):
        for movie in myMoviedb.movies:
            if movie.projectstatus == dbProjectActual.decode('utf-8'):
                li = xbmcgui.ListItem(movie.name, iconImage=baseUrl + movie.thumbnailurl, thumbnailImage = baseUrl + movie.thumbnailurl, )
                info = {
                    'genre': movie.genre,
                    'year': movie.year,
                    'title': movie.title,
                }
                li.setInfo('video', info)
                li.setArt({'thumb': baseUrl + movie.thumbnailurl, 'poster': baseUrl + movie.thumbnailurl, 'fanart': baseUrl + movie.thumbnailurl})
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+movie.url, listitem=li, isFolder=True)            

        xbmcplugin.endOfDirectory(addon_handle)
        return 
    return

def build_url_sub_directory(urlToPlay):
    global session

    #sys.stderr.write('build_url_sub_directory: ' + baseUrl + urlToPlay)
    url_content = load(baseUrl + urlToPlay)
    #sys.stderr.write('-----------------')
    #sys.stderr.write(url_content)
    #sys.stderr.write('-----------------')
    completedList = re.compile("class='forum-caption'><a href='video.php?(.*?)' style='font-size:14px;'>(.*?)</a>").findall(url_content)
    del url_content

    if (len(completedList) > 0):
        for x in range(0, len(completedList)):
            li = xbmcgui.ListItem(hParser.unescape(completedList[x][1].decode('utf-8')))
            movieUrl = completedList[x][0]
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+"?mode=playUrl&" + urllib.urlencode({'urlToPlay' : movieUrl}) + "&" + urllib.urlencode({'referedUrl' : baseUrl + urlToPlay}) + "&" + urllib.urlencode({'videoName' : completedList[x][1]}), listitem=li, isFolder=False)
            #xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+"?mode=playUrl&" + urllib.urlencode({'urlToPlay' : movieUrl}) + "&" + urllib.urlencode({'referedUrl' : baseUrl + urlToPlay}) + "&" + urllib.urlencode({'videoName' : completedList[x][1]}) + "&" + urllib.urlencode({'videoThumbnail' : completedList[x][0]}), listitem=li, isFolder=True)
    
    del completedList     
    xbmcplugin.endOfDirectory(addon_handle)

    return

# main...
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(addon_handle, 'movies')

mode = args.get('mode', None)
subDir = args.get('dirName', None)
category = args.get('category', None)
urlToPlay = args.get('urlToPlay', None)
referedUrl = args.get('referedUrl', None)
videoName = args.get('videoName', None)

myMoviedb = Moviedb()
try:
    dbFile = open(tmpDir + 'riczroninfactories.db', 'r')
    myMoviedb = pickle.load(dbFile)
    dbFile.close()
except:
    pass

if mode is None:
    #doLogin()
    build_main_directory()
elif mode[0] == 'changeDir':
    if (urlToPlay is None):
        build_sub_directory(subDir, category, '')
    else:
        build_sub_directory(subDir, category, urlToPlay[0])        
elif mode[0] == 'listMovieParts':
    build_url_sub_directory(urlToPlay[0])
elif mode[0] == 'openSetup':
    addon.openSettings()
elif mode[0] == 'playUrl':
    #sys.stderr.write('urlToPlay[0]: ' + str(urlToPlay[0]))
    #sys.stderr.write('videoName[0]: ' + str(videoName[0]))
    #sys.stderr.write('referedUrl[0]: ' + str(referedUrl[0]))
    play_videourl(urlToPlay[0], videoName[0], referedUrl[0])
    
del myMoviedb
del hParser
del addon
    