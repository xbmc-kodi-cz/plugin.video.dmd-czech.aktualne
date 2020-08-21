# -*- coding: utf-8 -*-

import routing

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

import re
import time
import datetime
import json
from bs4 import BeautifulSoup
import requests
import xml.etree.ElementTree as ET
import json

_addon = xbmcaddon.Addon()

plugin = routing.Plugin()

_baseurl = 'https://video.aktualne.cz/'
   
@plugin.route('/list_shows/')
def list_shows():
    xbmcplugin.setContent(plugin.handle, 'tvshows')
    soup = BeautifulSoup(get_page(_baseurl), 'html.parser')
    listing = []
    for porad in soup.select('h2.section-title a'):
        title = porad.text.encode('utf-8')            
        list_item = xbmcgui.ListItem(title)
        list_item.setInfo('video', {'mediatype': 'tvshow', 'title': title})
        listing.append((plugin.url_for(get_list, porad['href'], 2, 0), list_item, True))
        
    xbmcplugin.addDirectoryItems(plugin.handle, listing, len(listing))
    xbmcplugin.endOfDirectory(plugin.handle)
    
@plugin.route('/get_list/<path:show_id>/<category>/<page>')
def get_list(show_id, category, page):
    xbmcplugin.setContent(plugin.handle, 'episodes')
    url = _baseurl+'rss{0}?offset={1}'.format(show_id, page)
    listing = []
    count = 0
    root = ET.fromstring(get_page(url))
    for item in root.find('channel').findall('item'):
        duration = 0
        menuitems = []
        title = item.find('title').text.encode('utf-8')
        title_label = title
        show_title = re.compile('(.+?) -').search(root.find('.//channel/title').text).group(1)
        if category == '1':
            show_title = item.find('category').text.encode('utf-8')
            title_label = '[COLOR blue]{0}[/COLOR] · {1}'.format(show_title, title)
            show_id = re.compile('\/\/.+?(\/.+?)\/').search(item.find('link').text).group(1)
            menuitems.append(( _addon.getLocalizedString(30004), 'XBMC.Container.Update('+plugin.url_for(get_list, show_id, 0, 0)+')' )) #get_list, '', 'recent', 0)
        thumb = re.compile('<img.+?src="([^"]*?)"').search(item.find('{http://purl.org/rss/1.0/modules/content/}encoded').text).group(1)
        desc = item.find('description').text
        date = datetime.datetime(*(time.strptime(item.find('pubDate').text.strip()[:16], '%a, %d %b %Y')[:6])).strftime("%Y-%m-%d")
        dur = item.find('{http://i0.cz/bbx/rss/}extra').get('duration')
        if dur and ':' in dur:
            l = dur.strip().split(':')
            for pos, value in enumerate(l[::-1]):
                duration += int(value) * 60 ** pos
        list_item = xbmcgui.ListItem(title_label)
        list_item.setInfo('video', {'mediatype': 'episode', 'tvshowtitle': show_title, 'title': title, 'plot': desc, 'duration': duration, 'premiered': date})
        list_item.setArt({'thumb': thumb})
        list_item.setProperty('IsPlayable', 'true')
        list_item.addContextMenuItems(menuitems)
        listing.append((plugin.url_for(get_video, item.find('link').text), list_item, False))
        count +=1

    if count>=30:
        list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30003))
        list_item.setArt({'icon': 'DefaultFolder.png'})
        listing.append((plugin.url_for(get_list, show_id, category, int(page) + 30), list_item, True))
            
    xbmcplugin.addDirectoryItems(plugin.handle, listing, len(listing))
    xbmcplugin.endOfDirectory(plugin.handle)
    
@plugin.route('/get_video/<path:slug_url>')
def get_video(slug_url):
    soup = BeautifulSoup(get_page(slug_url), 'html.parser')
    data = json.loads(re.compile('\"tracks\":(.+?),\"adverttime').findall(soup.get_text())[0])
    if(data['HLS']):
        stream_url = data['HLS'][0]['src']
    else:
        stream_url = data['MP4'][0]['src']
        
    list_item = xbmcgui.ListItem(path=stream_url)
    xbmcplugin.setResolvedUrl(plugin.handle, True, list_item)

@plugin.route('/')
def root():
    listing = []
    list_item = xbmcgui.ListItem(_addon.getLocalizedString(30001))
    list_item.setArt({'icon': 'DefaultRecentlyAddedEpisodes.png'})
    listing.append((plugin.url_for(get_list, '', 1, 0), list_item, True))
    
    list_item = xbmcgui.ListItem(_addon.getLocalizedString(30002))
    list_item.setArt({'icon': 'DefaultTVShows.png'})
    listing.append((plugin.url_for(list_shows), list_item, True))
    
    xbmcplugin.addDirectoryItems(plugin.handle, listing, len(listing))
    xbmcplugin.endOfDirectory(plugin.handle)
    
def get_page(url):
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:80.0) Gecko/20100101 Firefox/80.0'})
    return r.content
    
def run():
    plugin.run()
    