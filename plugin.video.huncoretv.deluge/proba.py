#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import sys
import json
import re
import requests
from resources.lib.client import DelugeRPCClient


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
        delugeClient = DelugeRPCClient('127.0.0.1', 58846, 'kizs', 'hu1hu')
        delugeClient.connect()
        eredmeny = delugeClient.call('core.get_torrents_status', {}, ['name', 'total_size', 'total_done', 'progress', 'files'])
    except:
        sys.stderr.write("Hiba történt a Deluge megszólításakor!\n"+ str(sys.exc_info()[0]) + "-" + str(sys.exc_info()[1]) + '\n')
        return retVal
    
    for key in eredmeny:
        fileLength = eredmeny[key]['total_size']
        fileBytesCompleted = eredmeny[key]['total_done']
        files=eredmeny[key]['files']
        for x in range(0, len(files)) :
            fileName = files[x]['path'].encode('utf-8')
            if (fileName == torrent_file):
                if (fileLength == fileBytesCompleted):
                    retVal[1]=int(100)
                else:
                    retVal[1]=int(fileBytesCompleted/(fileLength/100))
                return retVal
                  
    return retVal



#getTorrentFiles(torrentFileContent)
sys.stderr.write(str(getTorrentFileStatus("Jack.Reacher.Never.Go.Back.2016.BDRip.x264.HuN-TRiNiTY/jack.reacher.never.go.back.bdrip-trinity.mkv")[1]))
#torrentFileContent.close()