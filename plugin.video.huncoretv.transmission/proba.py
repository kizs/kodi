#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import sys
import json
import re
import requests


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
    transmission_url = "http://192.168.0.16:9091/transmission/rpc"
    transmission_username = ""
    transmission_password = ""
    retVal=[]
    retVal.append("")
    retVal.append(int(-1))
    
    try:
        if len(transmission_username) > 0:
            sessionid_request = requests.get(transmission_url, auth=(transmission_username, transmission_password), verify=False)
        else:
            sessionid_request = requests.get(transmission_url, verify=False)
            
        sessionid = sessionid_request.headers['x-transmission-session-id']
        if sessionid:
            headers = {"X-Transmission-Session-Id": sessionid}
            body = json.dumps({"method": "torrent-get", "arguments": {"fields": ("id","files", "rateDownload")}})
            if len(transmission_username) > 0:
                post_request = requests.post(transmission_url, data=body, headers=headers, auth=(transmission_username, transmission_password), verify=False)
            else:
                post_request = requests.post(transmission_url, data=body, headers=headers, verify=False)
            ize = json.loads(post_request.text)
            
            torrents = ize['arguments']['torrents']
            for x in range(0, len(torrents)) :
              files = torrents[x]['files']
              retVal[0] = str(int(torrents[x]['rateDownload'])/1000) + " KB/s"
              for y in range(0, len(files)) :
                  fileName = files[y]['name'].encode('utf-8')
                  fileLength = files[y]['length']
                  fileBytesCompleted = files[y]['bytesCompleted']
                  fileBytesCompleted = files[y]['bytesCompleted']
                  if (fileName == torrent_file):
                      if (fileLength == fileBytesCompleted):
                          retVal[1]=int(100)
                      else:
                          retVal[1]=int(fileBytesCompleted/(fileLength/100))
                      return retVal
                  
        return retVal
    except:
        sys.stderr.write(sys.exc_info()[0])

    return retVal


torrentFileContent = open("/home/kizs/mytorrent.torrent")
#getTorrentFiles(torrentFileContent)
sys.stderr.write(str(getTorrentFileStatus("Inferno.2016.BDRiP.x264.HuN-HyperX/sample/sample.mkv")[1]))
torrentFileContent.close()