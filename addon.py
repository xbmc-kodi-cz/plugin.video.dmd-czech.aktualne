# -*- coding: utf-8 -*-
import os
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib
import urllib2
import re
import xml.etree.ElementTree as ET
import email.utils as eut
import time
import json

reload(sys)
sys.setdefaultencoding("utf-8")

_homepage_ = 'https://video.aktualne.cz/'
_rssUrl_ = _homepage_+'rss/'

_addon_ = xbmcaddon.Addon('plugin.video.dmd-czech.aktualne')
_lang_  = _addon_.getLocalizedString
_scriptname_ = _addon_.getAddonInfo('name')
_UserAgent_ = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, lkodiazor Gecko) Chrome/52.0.2743.116 Safari/537.36'
_quality_ = _addon_.getSetting('quality')
home = _addon_.getAddonInfo('path')
_icon_ = xbmc.translatePath(os.path.join(home, 'resources/media/ikona-aktualne-57x57.png'))
_mediadir_ = xbmc.translatePath(os.path.join(home, 'resources/media/'))

def log(msg, level=xbmc.LOGDEBUG):
    if type(msg).__name__ == 'unicode':
        msg = msg.encode('utf-8')
    xbmc.log("[%s] %s" % (_scriptname_, msg.__str__()), level)

def logDbg(msg):
    log(msg,level=xbmc.LOGDEBUG)

def logErr(msg):
    log(msg,level=xbmc.LOGERROR)

addon_handle = int(sys.argv[1])

xbmcplugin.setContent(addon_handle, 'episodes')

def showNotification(message, icon):
    xbmcgui.Dialog().notification(_scriptname_, message, icon)

def showErrorNotification(message):
    showNotification(message, 'error')

def fetchUrl(url, label):
    logDbg("fetchUrl " + url + ", label:" + label)
    httpdata = ''
    try:
        request = urllib2.Request(url, headers={'User-Agent': _UserAgent_,})
        resp = urllib2.urlopen(request)
        httpdata = resp.read()
    except:
        httpdata = None
        showErrorNotification(_lang_(30002))
    finally:
        resp.close() 
    return httpdata

def listItems(offset, urladd):
    url = _rssUrl_ + urladd
    if offset > 0:
        url += '?offset=' + str(offset)
    rss = fetchUrl(url, _lang_(30003))
    if (not rss):
        return
    root = ET.fromstring(rss)
    for item in root.find('channel').findall('item'):
        link  = item.find('link').text
        title = item.find('title').text
        description = item.find('description').text
        contentEncoded = item.find('{http://purl.org/rss/1.0/modules/content/}encoded').text
        extra = item.find('{http://i0.cz/bbx/rss/}extra')
        subtype = extra.get('subtype')
        dur = extra.get('duration')
        datetime = eut.parsedate(item.find('pubDate').text.strip())
        date = time.strftime('%d.%m.%Y', datetime)
        image = re.compile('<img.+?src="([^"]*?)"').search(contentEncoded).group(1)
        li = xbmcgui.ListItem(title)
        if dur and ':' in dur:
            l = dur.strip().split(':')
            duration = 0
            for pos, value in enumerate(l[::-1]):
                duration += int(value) * 60 ** pos
            li.addStreamInfo('video', {'duration': duration})
        if subtype == 'playlist':
            li.setLabel2('Playlist')
        li.setThumbnailImage(image)
        li.setIconImage(_icon_)
        li.setInfo('video', {'mediatype': 'episode', 'title': title, 'plot': description, 'premiered': date})       
       
        li.setProperty('fanart_image',image)
        u=sys.argv[0]+'?mode=10&url='+urllib.quote_plus(link.encode('utf-8'))
        if(dur):
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=u, listitem=li)
    o = offset + 30 
    u = sys.argv[0]+'?mode=1&url='+urllib.quote_plus(urladd.encode('utf-8'))+'/&offset='+urllib.quote_plus(str(o))
    liNext = xbmcgui.ListItem(_lang_(30006))
    xbmcplugin.addDirectoryItem(handle=addon_handle,url=u,listitem=liNext,isFolder=True)    
    xbmcplugin.endOfDirectory(addon_handle)

def playUrl(url):
    httpdata = fetchUrl(url, _lang_(30004))
    if (not httpdata):
        return
    if httpdata: 
        title = re.search('<meta property="og:title" content="(.+)">', httpdata).group(1)
        image = re.search('<meta property="og:image" content="(.+)">', httpdata).group(1)
        videos = re.search('"MP4":(.+\])', httpdata).group(1)

    try:
        detail = json.loads(videos)
    except ValueError:
        showErrorNotification(_lang_(30005))
        return
    if detail:
        pl=xbmc.PlayList(1)
        pl.clear()

        for version in detail:
            url = version['src']
            quality = version['label']
            li = xbmcgui.ListItem(title)
            li.setThumbnailImage(image)
            li.addStreamInfo('video', {'language': 'cs'})
            if (quality == _quality_):
                xbmc.PlayList(1).add(url, li)
                xbmc.Player().play(pl)
    else:
        showErrorNotification(_lang_(30005))

def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
        return param

def listShows():
    hdr = {'User-Agent': _UserAgent_,}
    request = urllib2.Request(_homepage_, headers=hdr)
    con = urllib2.urlopen(request)
    data = con.read()
    con.close()

    match = re.compile('<h2 class="section-title"><a href="/(.+?)/">(.+?)</a></h2>', re.DOTALL).findall(data)
    if len(match) > 1:
        for url, name in match:
            addDir(name,url,1)  
    xbmcplugin.endOfDirectory(addon_handle)
    
def addDir(name,url,mode):
    logDbg("addDir(): '"+name+"' url='"+url+"' icon='' mode='"+str(mode)+"'")
    u=sys.argv[0]+"?url="+urllib.quote_plus(url.encode('utf-8'))+"&mode="+str(mode)+"&name="+urllib.quote_plus(name.encode('utf-8'))
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage='')   
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    ok=xbmcplugin.addDirectoryItem(handle=addon_handle,url=u,listitem=liz,isFolder=True)
    return ok

params=get_params()
url=None
name=None
thumb=None
mode=None
offset=0

try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        offset=int(urllib.unquote_plus(params["offset"]))
except:
        pass
        
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass



if mode==None or url==None or len(url)<1:
    listShows()
    logDbg("List Shows end")
elif mode==1:
    listItems(offset, url)
elif mode==10:
    playUrl(url)
