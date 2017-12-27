#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import time
import os
import sys
import HTMLParser
import requests, requests.utils, pickle
import re
import xbmc
import xbmcaddon
import logging
import urllib

import json
from resources.lib.moviedb import Moviedb
from resources.lib.movie import Movie
from sets import Set

addon = xbmcaddon.Addon(id='plugin.video.riczroninfactories')
thisAddonDir = xbmc.translatePath(addon.getAddonInfo('path')).decode('utf-8')

baseUrl = 'http://riczroninfactories.eu/'
dbProjectCompleted='ProjectCompleted'
dbProjectActual='ProjectActual'
hParser = HTMLParser.HTMLParser()
moviePerPage = int(18)
tmpDir = ''

def newSession():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.6 Safari/537.36',
    })

    if os.path.isfile(tmpDir + 'riczroninfactories.cookies'): 
        cookieFile = open(tmpDir + 'riczroninfactories.cookies')
        cookies = requests.utils.cookiejar_from_dict(pickle.load(cookieFile))
        s.cookies = cookies
        cookieFile.close()

    return s


def update_movie_db(myMoviedb, url, projectStatus, index, hParser):
    global moviePerPage

    #regExp = "<div class='projekt_title'>(.*?)</div>.*?<img class='projektimg' src='(.*?)'>.*?Kategória</td><td class='projekt_right'>(.*?)</td>.*?<td class='projekt_left'>Év.*?class='projekt_right'>(.*?)</td>.*?<a href='(.*?)'><.*?title='Ismertető'></a>.*?<a href='(.*?)'><.*?title='Fórum'></a>.*?<a href='(.*?)'><.*?title='Letöltés'></a>(.*?)icon_online"
    regExp = "<td valign='top'><div id='projektbox'>(.*?)\n\n</td>"
    
    #sys.stderr.write(url + str(index))
    url_content = load(url + str(index))
    completedList = re.compile(regExp, re.MULTILINE|re.DOTALL).findall(url_content)
    del url_content
    
    if len(completedList) > 0:
        for x in range(0, len(completedList)):
            if "title='Online'" in completedList[x]:
                myMoviedb.addMovie(createMovie([completedList[x], hParser, projectStatus]))
    else:
        del completedList
        return False

    del completedList
    return True

def createMovie(parameters):
    try:
        if (len(parameters) == 3):
            movieProperties = parameters[0]
            hParser = parameters[1]
            projectStatus = parameters[2]
            
            name = re.compile("<div class='projekt_title.*?'>(.*?)</div>").findall(movieProperties)
            thumburl = re.compile("<div class=\"projektimgthumb\"><img class='projektimg' src='(.*?)'>").findall(movieProperties)
            year = re.compile("<td class='projekt_left'>Év</td>.*?<td class='projekt_right'>(.*?)</td></tr>", re.MULTILINE|re.DOTALL).findall(movieProperties)
            genreURL = re.compile("<a href='(.*?)'><img src='themes/rrfs4/images/info/icon_encyclopedia.png' title='Ismertető'></a>").findall(movieProperties)
            if (len(genreURL) == 0):
                genreURL=['']
            
            videourl = re.compile("<a href='infusions(.*?)'><img src='themes/rrfs4/images/info/icon_online.png' title='Online'></a>").findall(movieProperties)
            if (len(videourl) == 0):
                return None

            videourl[0] = 'infusions' + videourl[0]
            #sys.stderr.write("videourl: " + videourl)            
            videourl[0] = "?mode=listMovieParts&" + urllib.urlencode({'urlToPlay' : videourl[0]})
            videourl[0] = sys.argv[0] + videourl[0]
            
            genre=''
            if 'encyclopedia' in genreURL[0]:
                genreurl_content = load(baseUrl + genreURL[0])
                genreArray = re.compile("<td class='encyc_left'>Műfaj</td><td class='encyc_right' valign='top'>(.*?)</td></tr>", re.MULTILINE|re.DOTALL).findall(genreurl_content)
                del genreurl_content
                if len(genreArray) > 0:
                    genre = genreArray[0]
                del genreArray
            
            #sys.stderr.write('name[0]: ' + str(name[0]))
            #sys.stderr.write('videourl[0]: ' + str(videourl[0]))
            #sys.stderr.write('genre: ' + str(genre))
            #sys.stderr.write('year[0]: ' + str(year[0]))
            #sys.stderr.write('thumburl[0]: ' + str(thumburl[0]))
            #sys.stderr.write('projectStatus: ' + str(projectStatus))
            myMovie = Movie(name[0], videourl[0], genre, year[0], '', thumburl[0], projectStatus) 
            
            categories = genre.split(',')
            if (len(categories) > 0):
                for y in range(0, len(categories)):
                    category = categories[y].strip()
                    if (len(category) > 0):
                        myMovie.addCategory(category)
            
            return myMovie
        else:
            return None
        
    except:
        sys.stderr.write('Unexpected error: ' + str(sys.exc_info()[0]))
        logging.exception("Something awful happened!")
        return None
        
def fetch_movie_db(myMoviedb, dbName):
    #sys.stderr.write('Refresh Ricz/Ronin Factories database...')

    try:
        os.remove(tmpDir + dbName)
    except:
        pass
    
    try:
        dbFile = open(tmpDir + dbName, 'w')
        pickle.dump(myMoviedb, dbFile)
        dbFile.close()
    except:
        pass

def load(url, post = None):
    global session

    r = ""
    callHttp = True
    while callHttp:
        #sys.stderr.write('load: ' + url.encode('utf-8'))
        try:
            if post:
                r = session.post(url, data=post, verify=False, timeout=10).text
            else:
                r = session.get(url, verify=False, timeout=5).text
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


session = newSession()

if __name__ == '__main__':
    monitor = xbmc.Monitor()
    #sys.stderr.write('########### dbrefresh start')

    while not monitor.abortRequested():
        if monitor.waitForAbort(5):
            break

        tmpDir = addon.getSetting('tmpdir')
        if (tmpDir != ""):
            myMoviedb = Moviedb()
            myMoviedb_old = Moviedb()
            try:
                dbFile = open(tmpDir + 'riczroninfactories.db', 'r')
                myMoviedb_old = pickle.load(dbFile)
                dbFile.close()
            except:
                pass
            
            if myMoviedb_old.isSyncNeed():
                hasNext = True
                index = 0
                while hasNext:
                    sys.stderr.write('Refresh Ricz/Ronin Factories database, count of Befejezett: ' + str(index))
                    hasNext = update_movie_db(myMoviedb, baseUrl + 'projects.php?type=anime&medium=all&status=7&rowstart=', dbProjectCompleted, index, hParser)
                    index = index + moviePerPage
                    fetch_movie_db(myMoviedb, 'riczroninfactories_tmp.db')
                    if monitor.waitForAbort(1):
                        break
    
                hasNext = True
                index = 0
                while hasNext:
                    sys.stderr.write('Refresh Ricz/Ronin Factories database, count of Aktualis: ' + str(index))
                    hasNext = update_movie_db(myMoviedb, baseUrl + 'projects.php?type=anime&medium=all&status=13&rowstart=', dbProjectActual, index, hParser)
                    index = index + moviePerPage
                    fetch_movie_db(myMoviedb, 'riczroninfactories_tmp.db')
                    if monitor.waitForAbort(1):
                        break

    
            if len(myMoviedb_old.movies) <= len(myMoviedb.movies):
                fetch_movie_db(myMoviedb, 'riczroninfactories.db')
    
            #sys.stderr.write('Refresh Ricz/Ronin Factories database finished')
    
            del myMoviedb
            del myMoviedb_old
