#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import time
import xbmc
import sqlite3
import os
import datetime
import sys
import xbmcaddon
import xbmcgui

from python_libtorrent import get_libtorrent
libtorrent=get_libtorrent()
try:
    torrentSession
except NameError:
    torrentSession = libtorrent.session()
    torrentSession.listen_on(6881, 6889)

addon = xbmcaddon.Addon(id='service.kizstorrent')
tmpdir = addon.getSetting('tmpdir')
tmpTorrentdir = addon.getSetting('tmptorrentdir')
speedLimit = addon.getSetting('speedLimit')
downloadLimit = addon.getSetting('downloadLimit')
uploadLimit = addon.getSetting('uploadLimit')

try:
    torrent_pool
except:
    torrent_pool = dict()
    
if ((tmpdir == "") or (tmpTorrentdir == "")):
    dialog = xbmcgui.Dialog()
    dialog.ok("Hiba!", "KizsTorrent: Nem végezted el a beállításokat!", "", "")
    addon.openSettings()
    sys.exit()
    
dbConn = sqlite3.connect(tmpdir + 'torrents.db' )
dbConn.isolation_level = 'DEFERRED'

state_str = ['queued', 'checking', 'downloading metadata', 'downloading', 'finished', 'seeding', 'allocating', 'checking fastresume']            

def play_torrent(videoname, thumbnail, filePath):
    videoitem = xbmcgui.ListItem(label=videoname, thumbnailImage=thumbnail)
    videoitem.setInfo(type='Video', infoLabels={'Title': videoname})
    xbmc.Player().play(filePath, videoitem)
    return

def play_torrenturl(fileToPlay, video_url, videoname, thumbnail, tmptorles, elonySzazalek, torrentFullDownload):
    global dbConn
    global state_str
    
    if sys.platform.startswith('win'):
        fileToPlay = fileToPlay.replace('/','\\')
        
    torrentHandler = None
    dbOk = False
    while (not dbOk):
        try:
            c = dbConn.cursor()
            try:
                c.execute('SELECT count(*) FROM torrents')
            except:
                c.execute('CREATE TABLE torrents(torrents_id INTEGER PRIMARY KEY AUTOINCREMENT, torrentInfo BLOB, file_to_play TEXT, donwload_info TEXT, client_name TEXT, download_dir TEXT, savetime TIMESTAMP, download_percent INTEGER, seedable INTEGER, delete_date TIMESTAMP, mark_for_delete INTEGER)')
                sys.stderr.write('CREATE TABLE torrents(torrents_id INTEGER PRIMARY KEY AUTOINCREMENT, torrentInfo BLOB, file_to_play TEXT, client_name TEXT, download_dir TEXT, savetime TIMESTAMP, download_percent INTEGER, seedable INTEGER, delete_date TIMESTAMP, mark_for_delete INTEGER)')
        
            f = open(tmpdir + 'mytorrent.torrent', 'rb')
            blob = f.read()
            f.close()
            nowDate = datetime.datetime.now()
            row = c.execute('SELECT count(*) FROM torrents where torrentInfo=?', (buffer(blob), )).fetchone()
            if (row[0] == 0):
                c.execute('INSERT INTO torrents(torrentInfo, file_to_play, client_name, download_dir, savetime, download_percent, seedable, delete_date, mark_for_delete) VALUES(?,?,?,?,?,?,?,?,?)', (buffer(blob), fileToPlay, 'BHTV', tmpTorrentdir, nowDate, 0, 1, nowDate + datetime.timedelta(days=int(tmptorles)), 0))
            dbConn.commit()
            std = start_torrent_download(c.lastrowid, tmpTorrentdir, buffer(blob), fileToPlay, 0)
            torrentHandler = std[1]
            dbOk = True
        except:
            sys.stderr.write("NAGYON NEM JO - 1!")
            for x in range (0, len(sys.exc_info()) - 1):
                sys.stderr.write(str(sys.exc_info()[x]))
            dbOk = False
    
    xbmc.Player().stop()
    progress = xbmcgui.DialogProgress()
    progress.create('Progress: ' + fileToPlay)
    download_percent = 0
    while (torrentHandler):
        try:
            s = torrentHandler.status()
            download_percent = int(s.progress * 100)
            progress.update(download_percent, 'Download rate: ' + str(s.download_rate / 1000) + ' kB/s Peers: ' + str(s.num_peers) + ' State: ' + state_str[s.state], str(int(s.progress * 100)) + '%')
   
            if ((download_percent >= elonySzazalek) & (torrentFullDownload == 'false')):
                play_torrent(videoname, thumbnail, tmpTorrentdir + fileToPlay)
                progress.close()
                break
                #elonySzazalek = min(99, elonySzazalek + 2)

            #if (xbmc.Player().isPlaying()):
                
            if download_percent>=100:
                break
            time.sleep(1)
        except:
            sys.stderr.write("NAGYON NEM JO - 2!")
            for x in range (0, len(sys.exc_info()) - 1):
                sys.stderr.write(str(sys.exc_info()[x]))
    
    if ((torrentFullDownload == 'true') and (download_percent >= 99)):
        play_torrent(videoname, thumbnail, tmpTorrentdir + fileToPlay)
       
    return

def start_torrent_download(torrent_id, download_dir, torrentInfo, file_to_play, downloadedPercent):
    global torrent_pool
    global torrentSession
    
    updateRows=[]
    decoded = libtorrent.bdecode(str(torrentInfo))
    info = libtorrent.torrent_info(decoded)
    torrentHandler = None
    if torrent_pool.has_key(torrent_id):
        torrentHandler = torrent_pool.get(torrent_id)

    ujvagyregi = 'new '
    if (torrentHandler is None):
        torrentHandler = torrentSession.add_torrent({'ti': info, 'save_path': download_dir})
        torrent_pool[torrent_id] = torrentHandler
        first_piece = 1
        for x in range(0, info.num_files()):
            file_entry = info.file_at(x)
    
            if file_entry.path == file_to_play:
                pr = info.map_file(x, 0, 1)
                first_piece = pr.piece
                break

        elonyMB = 300 *1024 * 1024
        elonyPiece = int(elonyMB/info.piece_length()) + 1
        n_pieces = file_entry.size / info.piece_length() + 1
        x = int(n_pieces / 6) + 1
        for i in range(0, info.num_pieces()):
            if i in range(first_piece, first_piece+n_pieces):
                y = int(int(i-first_piece)/x)
                if (i < first_piece + elonyPiece):
                    torrentHandler.piece_priority(i, 7)
                else:
                    torrentHandler.piece_priority(i, 6 - y)
            else:
                torrentHandler.piece_priority(i, 1)
    else:
        ujvagyregi = ''
        
    if (speedLimit == 'true'):
        torrentHandler.set_download_limit(downloadLimit)
        torrentHandler.set_download_limit(uploadLimit)
                
    s = torrentHandler.status()
    sys.stderr.write(ujvagyregi + 'torrent download: ' + file_to_play + ' Download rate: ' + str(s.download_rate / 1000) + ' kB/s Peers: ' + str(s.num_peers) + ' State: ' + state_str[s.state] + ', ' + str(int(s.progress * 100)) + '%')
    if (downloadedPercent < 100):
        oneRow=[]
        oneRow.append(int(s.progress * 100))
        oneRow.append('Download rate: ' + str(s.download_rate / 1000) + ' kB/s Peers: ' + str(s.num_peers) + ' State: ' + state_str[s.state] + ', ' + str(int(s.progress * 100)) + '%')
        oneRow.append(str(info))
        updateRows.append(oneRow)
    else:
        if seed == 'false':
            torrentHandler.pause()
        oneRow=[]
        oneRow.append(100)
        oneRow.append('')
        oneRow.append(str(info))
        updateRows.append(oneRow)
    
    return (updateRows, torrentHandler)

def torrent(seed):
    global dbConn
    global torrent_pool
    global torrentSession
    
    try:
        c = dbConn.cursor()
        try:
            c.execute('SELECT count(*) FROM torrents')
        except:
            c.execute('CREATE TABLE torrents(torrents_id INTEGER PRIMARY KEY AUTOINCREMENT, torrentInfo BLOB, file_to_play TEXT, donwload_info TEXT, client_name TEXT, download_dir TEXT, savetime TIMESTAMP, download_percent INTEGER, seedable INTEGER, delete_date TIMESTAMP, mark_for_delete INTEGER)')
            sys.stderr.write('CREATE TABLE torrents(torrents_id INTEGER PRIMARY KEY AUTOINCREMENT, torrentInfo BLOB, file_to_play TEXT, client_name TEXT, download_dir TEXT, savetime TIMESTAMP, download_percent INTEGER, seedable INTEGER, delete_date TIMESTAMP, mark_for_delete INTEGER)')
    except:
        sys.stderr.write("NAGYON NEM JO - 3!")
        for x in range (0, len(sys.exc_info()) - 1):
            sys.stderr.write(str(sys.exc_info()[x]))
        pass
    
    deleteRows=[]
    nowDate = datetime.datetime.now()
    for row in c.execute('SELECT torrents_id, torrentInfo FROM torrents WHERE delete_date<=?', (nowDate, )):
        decoded = libtorrent.bdecode(str(row[1]))
        info = libtorrent.torrent_info(decoded)
        try:
            try:
                torrentHandler = torrent_pool.get(row[0])
            except:
                torrentHandler = None
            
            sys.stderr.write('Torlunk?')
            if not torrentHandler is None:
                sys.stderr.write('Torlunk!')
                torrentSession.remove_torrent(torrentHandler, True)
                for x in range(0, info.num_files()):
                    file_entry = info.file_at(x)
                    try:
                        os.unlink(file_entry.path)
                    except:
                        pass
                del torrent_pool[row[0]]
                try:
                    c.execute('DELETE FROM torrents WHERE delete_date<=?', (nowDate, ))
                    dbConn.commit()
                except:
                    sys.stderr.write("NAGYON NEM JO - 4!")
                    for x in range (0, len(sys.exc_info()) - 1):
                        sys.stderr.write(str(sys.exc_info()[x]))
                    pass
                #del torrents_pool[row[0]]
        except KeyError:
            raise TorrenterError('Hiba a torrent törlésekor!'.decode('utf-8'))
    
    updateRows=[]
    for row in c.execute('SELECT torrents_id, torrentInfo, download_dir, file_to_play, download_percent FROM torrents'):
        std = start_torrent_download(row[0], row[2], row[1], row[3], row[4])
        updateRows = std[0];
    
    try:
        c.executemany('UPDATE torrents SET download_percent=?, donwload_info=? where torrentInfo=?', updateRows)
        dbConn.commit()
    except:
        raise TorrenterError('Hiba az adatbázis frissítésekor!'.decode('utf-8'))

    return

if __name__ == '__main__':
    global tmpdir
    global tmpTorrentdir
    global speedLimit
    global downloadLimit
    global uploadLimit

    monitor = xbmc.Monitor()

    counter = 0
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break
        
        counter = counter + 1
        if (counter >= 60) :
            seed = addon.getSetting('seed')
            tmpdir = addon.getSetting('tmpdir')
            tmpTorrentdir = addon.getSetting('tmptorrentdir')
            speedLimit = addon.getSetting('speedLimit')
            downloadLimit = addon.getSetting('downloadLimit')
            uploadLimit = addon.getSetting('uploadLimit')
            torrent(seed)
            counter = 0
        
    dbConn.close()
