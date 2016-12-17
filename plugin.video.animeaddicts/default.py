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

try:
    from sqlite3 import dbapi2 as sqlite
except:
    from pysqlite2 import dbapi2 as sqlite


dbProjectCompleted='ProjectCompleted'
dbProjectActual='ProjectActual'

addon = xbmcaddon.Addon(id='plugin.video.animeaddicts')
thisAddonDir = xbmc.translatePath(addon.getAddonInfo('path')).decode('utf-8')
sys.path.append(os.path.join(thisAddonDir, 'resources', 'lib'))

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

appName = 'Animeaddicts'
logined = False

xbmcplugin.setContent(addon_handle, 'movies')
baseUrl = 'http://animeaddicts.hu/'

felhasznalo = addon.getSetting('felhasznalonev')
jelszo = addon.getSetting('jelszo')
tmpDir = addon.getSetting('tmpdir')
hdVideo = addon.getSetting('hdVideo')
forceDownload = addon.getSetting('forceDownload')
if (felhasznalo == "" or jelszo == "" or tmpDir == ""):
    dialog = xbmcgui.Dialog()
    dialog.ok("Hiba!", "Nem végezted el a beállításokat!", "", "")
    addon.openSettings()
    sys.exit()

dbConn = sqlite.connect(tmpDir + 'animeaddicts.db')


def newSession():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.6 Safari/537.36',
    })

    if os.path.isfile(tmpDir + 'animeaddicts.cookies'): 
        cookieFile = open(tmpDir + 'animeaddicts.cookies')
        cookies = requests.utils.cookiejar_from_dict(pickle.load(cookieFile))
        s.cookies = cookies
        cookieFile.close()

    return s

session = newSession()

def doLogin():
    global session
    postdata = {'login_name':addon.getSetting('felhasznalonev'),
                'login_submit':'BELÉPÉS',
                'login_password':addon.getSetting('jelszo')
                }

    content = session.post(baseUrl + 'project.php?ongoing').text
    
    sikeres = re.compile("vagy jelentkezz be", re.MULTILINE|re.DOTALL).findall(content.encode('utf-8'))
    if (len(sikeres) > 0):
        content = session.post(baseUrl + 'log.php?login', data=postdata).text

        sikeres = re.compile("Bejelentkezve", re.MULTILINE|re.DOTALL).findall(content.encode('utf-8'))
        if (len(sikeres) == 0):
            logined = False
            dialog = xbmcgui.Dialog()
            dialog.ok("Hiba!", "Helytelen felhasználónév, vagy jelszó!", "Esetleg megjelent az I'm not a robot captcha.", "Várj egy ideig, esetleg próbáld meg böngészőből!")
            sys.exit()
        else:
            logined = True
            cookieFile = open(tmpDir + 'animeaddicts.cookies', 'w')
            pickle.dump(requests.utils.dict_from_cookiejar(session.cookies), cookieFile)
            cookieFile.close();

    return

def load(url, post = None, referer = None):
    global session
    doLogin()

    if referer:
        session.headers.update({
        'Host': 'animeaddicts.hu',
        'Referer': referer
    })     

    #sys.stderr.write('Header start:')
    #for key in session.headers.keys():
    #    sys.stderr.write(key + ": " + session.headers.get(key, '***'))
    #sys.stderr.write('Header end.')
    
    r = ""
    try:
        if post:
            r = session.post(url, data=post, timeout=10).text
        else:
            if referer:
                contentFile = open(tmpDir + 'videocontent', 'wb')
                with closing(session.get(url, stream = True)) as r2:
                    contentLength = int(r2.headers['content-length'])
                    progress = xbmcgui.DialogProgress()
                    progress.create('Film letöltése')

                    numberOfChunk = 0
                    for chunk in r2.iter_content(chunk_size=(4*1024*1024)):
                        numberOfChunk = numberOfChunk + (4*1024*1024)
                        if chunk:
                            contentFile.write(chunk)
                        if (progress.iscanceled()):
                            return None
                        progress.update((numberOfChunk/(contentLength/100)), 'Fájl hossza: ' + str(contentLength/(1024*1024)) + 'MB')
                contentFile.close();
                return "DONE"
            else:
               r = session.get(url).text
            
    except AttributeError:
        xbmc.executebuiltin("HIBA: {0}".format(AttributeError.message))
        if post:
            r = session.post(url, data=post, verify=False, timeout=10).text
        else:
            r = session.get(url, verify=False).text

    if referer:
#        sys.stderr.write('return binary')
        return r
    else:
#        sys.stderr.write('return text')
        return r.encode('utf-8')

def play_videourl(video_url, videoname, thumbnail, referedUrl):
    global session

    if (forceDownload == 'true'):
        retVal = load(baseUrl + video_url, None, referedUrl)
        if retVal:
            videoitem = xbmcgui.ListItem(label=videoname, thumbnailImage=baseUrl + thumbnail)
            videoitem.setInfo(type='Video', infoLabels={'Title': videoname})
            xbmc.Player().play(tmpDir + 'videocontent', videoitem)
    else:
        doLogin()
        
        cookieFile = open(tmpDir + 'animeaddicts.cookies')
        tmpCookies = requests.utils.cookiejar_from_dict(pickle.load(cookieFile))
        cookieFile.close()
    
        cookie = {'AnimeAddicts': tmpCookies.get('AnimeAddicts', ''), 'AnimeAddictsCookieExpire': tmpCookies.get('AnimeAddictsCookieExpire', ''), 'PHPSESSID': tmpCookies.get('PHPSESSID', '')}
        tmpString = "AnimeAddicts=" + tmpCookies.get('AnimeAddicts', '') + ";AnimeAddictsCookieExpire=" + tmpCookies.get('AnimeAddictsCookieExpire', '') + ";PHPSESSID=" + tmpCookies.get('PHPSESSID', '')
        video_url = video_url + "|Cookie=" + urllib.quote_plus(tmpString)
        video_url = video_url + "&" + urllib.urlencode({'Host' : 'animeaddicts.hu', 'Referer' : referedUrl})
        videoitem = xbmcgui.ListItem(label=videoname, thumbnailImage=baseUrl + thumbnail)
        videoitem.setInfo(type='Video', infoLabels={'Title': videoname})
        xbmc.Player().play(baseUrl + video_url, videoitem)
    
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

    localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista'
    li = xbmcgui.ListItem('Saját listák')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=Kereses'
    li = xbmcgui.ListItem('Keresés')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=ClearDB'
    li = xbmcgui.ListItem('Adatbázis frissítése')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
    

    xbmcplugin.endOfDirectory(addon_handle)
    return

def build_sub_directory(subDir, category):
    global dbConn

    hParser = HTMLParser.HTMLParser()
    if (subDir[0].startswith('Sajatlista_')):
        url_content = load(baseUrl + '/news.php?news')
        completedList = re.compile("<a href='encyclopedia.php\?mylist.(.*?).anime.saw'", re.MULTILINE|re.DOTALL).findall(url_content)
        if (len(completedList) > 0):
            userID = str(completedList[0])
            
            if (subDir[0].endswith('Befejezett')):
                url_content = load(baseUrl + 'encyclopedia.php?mylist.' + userID + '.anime.saw')

            if (subDir[0].endswith('Aktualis')):
                url_content = load(baseUrl + 'encyclopedia.php?mylist.' + userID + '.anime.watch')

            if (subDir[0].endswith('Tervezett')):
                url_content = load(baseUrl + 'encyclopedia.php?mylist.' + userID + '.anime.towatch')

            if (subDir[0].endswith('Felfuggesztett')):
                url_content = load(baseUrl + 'encyclopedia.php?mylist.' + userID + '.anime.stalled')

            if (subDir[0].endswith('Dobott')):
                url_content = load(baseUrl + 'encyclopedia.php?mylist.' + userID + '.anime.dropped')

            if (subDir[0].endswith('Kedvenc')):
                url_content = load(baseUrl + 'encyclopedia.php?mylist.' + userID + '.anime.favourite')

            if (subDir[0].endswith('Utalt')):
                url_content = load(baseUrl + 'encyclopedia.php?mylist.' + userID + '.anime.hated')
                
            completedList = re.compile("<td  style='width:58px;'>.*?<a href='(.*?)'>.*?<img src='(.*?)' alt='(.*?)'", re.MULTILINE|re.DOTALL).findall(url_content)
            for x in range(0, len(completedList)):
                name = hParser.unescape(completedList[x][1].decode('utf-8'))
                localurl = completedList[x][0];
                localurl = "?mode=listMovieParts&" + urllib.urlencode({'urlToPlay' : localurl})
                localurl = sys.argv[0] + localurl
                
                thumbnail = str(completedList[x][1])
                thumbnail = thumbnail.replace('_thumb', '')
                thumbnail = baseUrl + thumbnail
                li = xbmcgui.ListItem(completedList[x][2], iconImage=thumbnail)
                li.setArt({'thumb': thumbnail, 'poster': thumbnail, 'fanart': thumbnail})                
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
                
        xbmcplugin.endOfDirectory(addon_handle)
        return 

    if (subDir[0] == 'Sajatlista'):
        localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista_Befejezett'
        li = xbmcgui.ListItem('Befejezett', iconImage=thisAddonDir + '/resources/ok_gray_32.png')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista_Aktualis'
        li = xbmcgui.ListItem('Aktuális', iconImage=thisAddonDir + '/resources/watch_48.png')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
        
        localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista_Tervezett'
        li = xbmcgui.ListItem('Tervezett', iconImage=thisAddonDir + '/resources/towatch_48.png')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
        
        localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista_Felfuggesztett'
        li = xbmcgui.ListItem('Felfüggesztett', iconImage=thisAddonDir + '/resources/stalled_48.png')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
        
        localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista_Dobott'
        li = xbmcgui.ListItem('Dobott', iconImage=thisAddonDir + '/resources/dropped_48.png')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
        
        localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista_Kedvenc'
        li = xbmcgui.ListItem('Kedvenc', iconImage=thisAddonDir + '/resources/favourite_48.png')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
        
        localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista_Utalt'
        li = xbmcgui.ListItem('Utált', iconImage=thisAddonDir + '/resources/hated_48.png')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(addon_handle)
        return 

    if (subDir[0] == 'Kereses'):
        kb=xbmc.Keyboard('', 'Keresés', False)
        kb.doModal()
        if (kb.isConfirmed()):
            searchText = "%" + kb.getText() + "%"
            
            c = dbConn.cursor()
            for row in c.execute("SELECT movieseries.movieseries_id, movieseries.name, url, genre, year, title, thumbnailurl FROM movieseries WHERE name like (?) ORDER BY name", (searchText.decode('utf-8'),)):
                li = xbmcgui.ListItem(row[1], iconImage=baseUrl + row[6], thumbnailImage = baseUrl + row[6], )
                info = {
                    'genre': row[3],
                    'year': row[4],
                    'title': row[5],
                }
                li.setInfo('video', info)
                li.setArt({'thumb': baseUrl + row[6], 'poster': baseUrl + row[6], 'fanart': baseUrl + row[6]})
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+row[2], listitem=li, isFolder=True)
            
            xbmcplugin.endOfDirectory(addon_handle)
        return 

    if (subDir[0] == 'Kategoria'):
        c = dbConn.cursor()
        for row in c.execute("SELECT DISTINCT name FROM category ORDER BY name"):
            localurl = sys.argv[0]+'?mode=changeDir&dirName=KategorianBelul&' + urllib.urlencode({'category' : row[0].encode('utf-8')}) 
            li = xbmcgui.ListItem(row[0])
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)
    
        xbmcplugin.endOfDirectory(addon_handle)
        return 

    if (subDir[0] == 'KategorianBelul'):
        c = dbConn.cursor()  #       0                           1                 2    3      4     5      6
        for row in c.execute("SELECT movieseries.movieseries_id, movieseries.name, url, genre, year, title, thumbnailurl FROM movieseries JOIN category ON category.movieseries_id=movieseries.movieseries_id AND category.name=(?) ORDER BY movieseries.name", (category[0].decode('utf-8'),)):
            li = xbmcgui.ListItem(row[1], iconImage=baseUrl + row[6], thumbnailImage = baseUrl + row[6], )
            info = {
                'genre': row[3],
                'year': row[4],
                'title': row[5],
            }
            li.setInfo('video', info)
            li.setArt({'thumb': baseUrl + row[6], 'poster': baseUrl + row[6], 'fanart': baseUrl + row[6]})
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+row[2], listitem=li, isFolder=True)
            
        xbmcplugin.endOfDirectory(addon_handle)
        return

    if (subDir[0] == 'ClearDB'):
        check_db()
        c = dbConn.cursor()
        c.execute('DELETE FROM movieseries')
        c.execute('DELETE FROM category')
        c.execute('DELETE FROM mysequence')
        c.execute('INSERT INTO mysequence VALUES(0)')
        try:
            c.execute('CREATE INDEX movieseries_name ON movieseries(name)')
        except:
            sys.stderr.write('movieseries_name index már létezik')

        try:
            c.execute('CREATE INDEX category_movieseries_1 ON category (name, movieseries_id)')
            c.execute('CREATE INDEX category_movieseries_2 ON category (name)')
        except:
            sys.stderr.write('category_movieseries index már létezik')

        dbConn.commit()
        update_movie_db(baseUrl + 'project.php?completed.jap', dbProjectCompleted)
        update_movie_db(baseUrl + 'project.php?ongoing.jap', dbProjectActual)
        return
    
    if (subDir[0] == 'Befejezett'):
#        url_content = load(baseUrl + 'project.php?completed.jap')
        c = dbConn.cursor()
        for row in c.execute("SELECT movieseries.movieseries_id, movieseries.name, url, genre, year, title, thumbnailurl FROM movieseries WHERE projectstatus = (?) ORDER BY name", (dbProjectCompleted.decode('utf-8'),)):
            li = xbmcgui.ListItem(row[1], iconImage=baseUrl + row[6], thumbnailImage = baseUrl + row[6], )
            info = {
                'genre': row[3],
                'year': row[4],
                'title': row[5],
            }
            li.setInfo('video', info)
            li.setArt({'thumb': baseUrl + row[6], 'poster': baseUrl + row[6], 'fanart': baseUrl + row[6]})
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+row[2], listitem=li, isFolder=True)
        
        xbmcplugin.endOfDirectory(addon_handle)
        return 

    if (subDir[0] == 'Aktualis'):
#        url_content = load(baseUrl + 'project.php?ongoing.jap')
        c = dbConn.cursor()
        for row in c.execute("SELECT movieseries.movieseries_id, movieseries.name, url, genre, year, title, thumbnailurl FROM movieseries WHERE projectstatus = (?) ORDER BY name", (dbProjectActual.decode('utf-8'),)):
            li = xbmcgui.ListItem(row[1], iconImage=baseUrl + row[6], thumbnailImage = baseUrl + row[6], )
            info = {
                'genre': row[3],
                'year': row[4],
                'title': row[5],
            }
            li.setInfo('video', info)
            li.setArt({'thumb': baseUrl + row[6], 'poster': baseUrl + row[6], 'fanart': baseUrl + row[6]})
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+row[2], listitem=li, isFolder=True)
        
        xbmcplugin.endOfDirectory(addon_handle)
        return 

#    completedList = re.compile("<h1><a href='(.*?)'>(.*?)</a></h1>.*?<img src='(.*?)'.*?<strong>(Frissítve|Befejezve):</strong>(.*?)<.*?<span style='font-size:10px;'>(.*?)<", re.MULTILINE|re.DOTALL).findall(url_content)
#    hParser = HTMLParser.HTMLParser()
#    if (len(completedList) > 0):
#        for x in range(0, len(completedList)):
#            li = xbmcgui.ListItem(hParser.unescape(completedList[x][1].decode('utf-8')), iconImage=baseUrl + completedList[x][2], thumbnailImage = baseUrl + completedList[x][2], )
#            info = {
#                'genre': completedList[x][5],
#                'year': completedList[x][4].strip()[:4],
#                'title': hParser.unescape(completedList[x][1].decode('utf-8')),
#            }
#            li.setInfo('video', info)
#            li.setArt({'thumb': baseUrl + completedList[x][2], 'poster': baseUrl + completedList[x][2], 'fanart': baseUrl + completedList[x][2]})
#            li.setProperty('befejezve', completedList[x][3])
#            xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+"?mode=listMovieParts&" + urllib.urlencode({'urlToPlay' : completedList[x][0]}), listitem=li, isFolder=True)
#        
#    xbmcplugin.endOfDirectory(addon_handle)
    return

def build_url_sub_directory(urlToPlay):
    global session

    sys.stderr.write('build_url_sub_directory(urlToPlay): ' + str(urlToPlay))
    sys.stderr.write('urlToPlay.find(encyclopedia.php): ' + str(urlToPlay.find('encyclopedia.php')))
    if (urlToPlay.find('encyclopedia.php') > -1):
        url_content = load(urlToPlay)
        completedList = re.compile("<a href='(.*?)'.*?>videó").findall(url_content)
        if (len(completedList) > 0):
            urlToPlay = str(completedList[0])
            sys.stderr.write('build_url_sub_directory(urlToPlay): ' + str(urlToPlay))

    url_content = load(baseUrl + urlToPlay)
    completedList = re.compile("<div style='width:100px;height:75px;background:#000 url[(](.*?)[)].*?<h1 style='margin-bottom:5px;'>(.*?)</h1>.*?<a href='(.*?)'><img src=.*?<a href='(.*?)'.*?<a href='(.*?)'", re.MULTILINE|re.DOTALL).findall(url_content)
    
    hParser = HTMLParser.HTMLParser()

    if (len(completedList) > 0):
        for x in range(0, len(completedList)):
            li = xbmcgui.ListItem(hParser.unescape(completedList[x][1].decode('utf-8')), iconImage=baseUrl + completedList[x][0])
            a = completedList[x][2].find('.html5')
           
            movieUrl = completedList[x][2]
            movieUrl = movieUrl[:a]
            movieUrl = movieUrl.replace('view', 'request')
            if (hdVideo == 'FHD'):
                fhdUrl = completedList[x][3]
                sys.stderr.write('fhdUrl: ' + fhdUrl)                                      
                if (fhdUrl.find('.FD') > -1):
                    movieUrl = movieUrl + '.FD'
            if (hdVideo == 'SD'):
                movieUrl = movieUrl + '.SD'

            xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+"?mode=playUrl&" + urllib.urlencode({'urlToPlay' : movieUrl}) + "&" + urllib.urlencode({'referedUrl' : baseUrl + urlToPlay}) + "&" + urllib.urlencode({'videoName' : completedList[x][1]}) + "&" + urllib.urlencode({'videoThumbnail' : completedList[x][0]}), listitem=li, isFolder=True)
        
    xbmcplugin.endOfDirectory(addon_handle)

    return


def check_db():
    global dbConn
    
    c = dbConn.cursor()
    try:
        c.execute('SELECT dbversion FROM version')
    except:
        c.execute('CREATE TABLE version(dbversion integer)')
        c.execute('INSERT INTO version VALUES(1)')
        try:
            c.execute('DROP TABLE movieseries')
        except:
            sys.stderr.write('Első indulás')
    
    try:
        c.execute('SELECT COUNT(*) FROM mysequence')
    except:
        c.execute('CREATE TABLE mysequence(number integer)')
        c.execute('INSERT INTO mysequence VALUES(0)')

    try:
        c.execute('SELECT COUNT(*) FROM movieseries')
    except:
        c.execute('CREATE TABLE movieseries(movieseries_id INTEGER PRIMARY KEY, name TEXT, url TEXT, genre TEXT, year TEXT, title TEXT, thumbnailurl TEXT, projectstatus TEXT)')
        c.execute('CREATE INDEX movieseries_name ON movieseries (name)')

    c.execute('DELETE FROM movieseries where projectstatus=(?)', (dbProjectActual,)) #Az aktuálisakat mindig frissítnei kell!

    try:
        c.execute('SELECT COUNT(*) FROM category')
    except:
        c.execute('CREATE TABLE category(category_id INTEGER PRIMARY KEY, movieseries_id INTEGER, name TEXT)')
        c.execute('CREATE INDEX category_movieseries_1 ON category (name, movieseries_id)')
        c.execute('CREATE INDEX category_movieseries_2 ON category (name)')
        
    c.close()
    return

def getnewid_db():
    global dbConn
    c = dbConn.cursor()
    c.execute('SELECT number FROM mysequence')
    number = c.fetchone()[0]
    c.execute('UPDATE mysequence SET number=number+1')
    c.close()
    dbConn.commit()
    
    return str(number).decode('utf-8')


def update_movie_db(url, projectStatus):
    global dbConn
    insertMovieRowNum = -1
    insertMovieRows=[]
    insertCategoryRowNum = -1
    insertCategoryRows=[]

    c = dbConn.cursor()
    
    url_content = load(url)
    completedList = re.compile("<h1><a href='(.*?)'>(.*?)</a></h1>.*?<img src='(.*?)'.*?<strong>(Frissítve|Befejezve):</strong>(.*?)<.*?<span style='font-size:10px;'>(.*?)<", re.MULTILINE|re.DOTALL).findall(url_content)
    hParser = HTMLParser.HTMLParser()
        
    if (len(completedList) > 0):
        for x in range(0, len(completedList)):
            name = hParser.unescape(completedList[x][1].decode('utf-8'))
            url = completedList[x][0];
            a = url.find('\'')            
            if (a > -1):
                url = url[:a]
            
            url = "?mode=listMovieParts&" + urllib.urlencode({'urlToPlay' : url})
            url = sys.argv[0] + url
            
            genre = completedList[x][5].decode('utf-8')
            year = completedList[x][4].strip()[:4].decode('utf-8')
            thumburl = completedList[x][2]
            
            c.execute("SELECT COUNT(*) FROM movieseries WHERE name=(?)", (name,))
            number = c.fetchone()[0]
            
            
            if (number == 0):
                insertMovieRowNum = insertMovieRowNum + 1
                movideID = getnewid_db()
                #c.execute("INSERT INTO movieseries VALUES(?,?,?,?,?,?,?)", (movideID, name, url, genre, year, name, thumburl))

                movie=[]
                movie.append(movideID)
                movie.append(name)
                movie.append(url)
                movie.append(genre)
                movie.append(year)
                movie.append(name)
                movie.append(thumburl)
                movie.append(projectStatus)
                insertMovieRows.append(movie)
                
                categories = genre.split(',')
                if (len(categories) > 0):
                    for y in range(0, len(categories)):
                        category = categories[y].strip()
                        if (len(category) > 0):
                            insertCategoryRowNum = insertCategoryRowNum + 1
                            category=[]
                            category.append(getnewid_db())
                            category.append(movideID)
                            category.append(categories[y].strip())
                            insertCategoryRows.append(category)
                            #category(category_id integer, movieseries_id integer, name text)
                            #c.execute("INSERT INTO category VALUES(?,?,?)", (getnewid_db(), movideID, categories[y].strip()))
            
    
    if (insertMovieRowNum > -1):
        c.executemany("INSERT INTO movieseries VALUES(?,?,?,?,?,?,?,?)", insertMovieRows)

    if (insertCategoryRowNum > -1):
        c.executemany("INSERT INTO category VALUES(?,?,?)", insertCategoryRows)
    
    c.close()
    dbConn.commit()
    return



# main...
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(addon_handle, 'movies')
check_db()
update_movie_db(baseUrl + 'project.php?completed.jap', dbProjectCompleted)
update_movie_db(baseUrl + 'project.php?ongoing.jap', dbProjectActual)

mode = args.get('mode', None)
subDir = args.get('dirName', None)
category = args.get('category', None)
urlToPlay = args.get('urlToPlay', None)
referedUrl = args.get('referedUrl', None)
videoName = args.get('videoName', None)
videoThumbnail = args.get('videoThumbnail', None)

if mode is None:
    doLogin()
    build_main_directory()
elif mode[0] == 'changeDir':
    build_sub_directory(subDir, category)
elif mode[0] == 'listMovieParts':
    build_url_sub_directory(urlToPlay[0])
elif mode[0] == 'openSetup':
    addon.openSettings()
elif mode[0] == 'playUrl':
    play_videourl(urlToPlay[0], videoName[0], videoThumbnail[0], referedUrl[0])

dbConn.close()