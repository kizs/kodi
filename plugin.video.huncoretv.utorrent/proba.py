#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import sys
import json
import re
import requests, requests.utils
import pickle


torrentPath = "/home/kizs/tmp/"
utorrent_url = "http://192.168.0.17:8080/gui/"
utorrent_username='admin'
utorrent_password='aaa'

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

def getToken():
    uDatas = []
    auth = requests.auth.HTTPBasicAuth(utorrent_username, utorrent_password)
    sessionid_request = requests.get(utorrent_url + 'token.html', auth=auth, verify=False)
        
    token = re.search('<div[^>]*id=[\"\']token[\"\'][^>]*>([^<]*)</div>', sessionid_request.text).group(1)
    guid = sessionid_request.cookies['GUID']
    cookies = dict(GUID = guid)

    uDatas.append(token)
    uDatas.append(cookies)

    output = open(torrentPath + 'utorrent.data', 'wb')
    json.dump(uDatas, output)
    output.close()
    
    return uDatas

def getuTorrentTorrentList(uDatas):
    auth = requests.auth.HTTPBasicAuth(utorrent_username, utorrent_password)
    try:
        session_request = requests.get(utorrent_url + '?list=1&token=' + uDatas[0], cookies=uDatas[1], auth=auth, verify=False)
    except:
        return None
    
    if session_request.text.encode('utf-8').find('invalid request') > -1:
        return None
    
    return session_request
    

def getTorrentFileStatus(torrent_file):
    retVal=[]
    retVal.append("")
    retVal.append(int(-1))
    auth = requests.auth.HTTPBasicAuth(utorrent_username, utorrent_password)

    try:
        input = open(torrentPath + 'utorrent.data', 'rb')
        uDatas = json.load(input)
        input.close()
    except:
        uDatas = getToken()
    
    session_request = getuTorrentTorrentList(uDatas)
    if (session_request is None):
        uDatas = getToken()
        session_request = getuTorrentTorrentList(uDatas)
    
        if (session_request is None):
            dialog = xbmcgui.Dialog().ok(appName, u"Hiba történt a \u00b5Torrent megszólításakor!", str(sys.exc_info()[0]), "(Esetleg hibás beállítások?)");
            return
    
    ize = json.loads(session_request.text)
    
    torrents = ize['torrents']
    for x in range(0, len(torrents)) :
        torrentHash = torrents[x][0]
        torrentName = torrents[x][2]
        sys.stderr.write('Files\n')
        session_request2 = requests.get(utorrent_url + '?action=getfiles&hash=' + torrentHash + '&token=' + uDatas[0], cookies=uDatas[1], auth=auth, verify=False)

        sys.stderr.write(session_request2.text + "\n")
        ize2 = json.loads(session_request2.text)
        files = ize2["files"][1]
      
        retVal[0] = ""
        for y in range(0, len(files)) :
            fileName = files[y][0]
            sys.stderr.write('File: ' + fileName.encode('utf-8') + "\n")
            fileLength = files[y][1]
            fileBytesCompleted = files[y][2]
            if (torrentName + '/' + fileName.encode('utf-8').replace('\\','/') == torrent_file.replace('\\','/')):
                if (fileLength == fileBytesCompleted):
                    retVal[1]=int(100)
                else:
                    retVal[1]=int(fileBytesCompleted/(fileLength/100))
                return retVal
              
    return retVal


#torrentFileContent = open("/home/kizs/mytorrent.torrent")
#getTorrentFiles(torrentFileContent)
sys.stderr.write(str(getTorrentFileStatus("jack.reacher.never.go.back.bdrip-trinity.mkv")[1]))
#torrentFileContent.close()