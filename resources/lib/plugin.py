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

_addon = xbmcaddon.Addon()

plugin = routing.Plugin()

_baseurl = 'https://tv.idnes.cz/'
_videourl = 'https://servix.idnes.cz/media/video.aspx'

@plugin.route('/list_shows/')
def list_shows():
    xbmcplugin.setContent(plugin.handle, 'tvshows')
    soup = BeautifulSoup(get_page(_baseurl+'porady'), 'html.parser')
    porady = soup.find('div', {'class': 'entry-list'}).find_all('div', {'class': 'entry entry-square'})

    listing = []
    for porad in porady:
        title = porad.find('h3').get_text()
        url = porad.find('a', {'class': 'art-link'})['href']
        thumb = normalize_url(re.search('url\(\'(.+)\'\)', porad.find('div', {'class': 'art-img'})['style']).group(1))

        list_item = xbmcgui.ListItem(label=title)
        list_item.setInfo('video', {'mediatype': 'tvshow', 'title': title})
        list_item.setArt({'poster': thumb})
        listing.append((plugin.url_for(get_list, category_id = 'list', show_url = url), list_item, True))

    xbmcplugin.addDirectoryItems(plugin.handle, listing, len(listing))
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/list_news/')
def list_news():
    xbmcplugin.setContent(plugin.handle, 'tvshows')
    soup = BeautifulSoup(get_page(_baseurl), 'html.parser')
    porady = soup.find('menu', {'id': 'menu'}).find('ul').find_all('li')

    listing = []
    for porad in porady:
        title = porad.find('a').get_text()
        url = normalize_url(porad.find('a')['href'])
        list_item = xbmcgui.ListItem(label=title)
        list_item.setInfo('video', {'mediatype': 'tvshow', 'tvshowtitle': title})
        listing.append((plugin.url_for(get_list, show_url = url, category = 0), list_item, True))

    xbmcplugin.addDirectoryItems(plugin.handle, listing, len(listing))
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/get_list/')
def get_list():
    xbmcplugin.setContent(plugin.handle, 'episodes')
    url = plugin.args['show_url'][0]
    category = int(plugin.args['category'][0] if 'category' in plugin.args else 0)
    soup = BeautifulSoup(get_page(url), 'html.parser')
    items = soup.find('div', {'class': 'entry-list'}).find_all('div', {'class': 'entry'})
    listing = []
    for item in items:
        menuitems = []
        title = item.find('h3').get_text().encode('utf-8')
        video_id = item.find('a', {'class': 'art-link'})['data-id']
        date = datetime.datetime(*(time.strptime(item.find('span', {'class': 'time'})['datetime'], "%Y-%m-%dT%H:%M:%S")[:6])).strftime("%Y-%m-%d")
        title_label = title
        thumb = (re.search('url\(\'(.+)\'\)', item.find('div', {'class': 'art-img'})['style'])).group(1)
        dur = item.find('span', {'class': 'length'}).get_text()
        show_title = soup.find('div', {'class': 'opener-in'})
        if show_title:
            show_title = show_title.find('h1').get_text().encode('utf-8')
        if category == 1:
            show_id = normalize_url(item.find('a', {'class': 'isle-link'})['href'])
            show_title = item.find('a', {'class': 'isle-link'}).get_text().encode('utf-8')
            title_label = '[COLOR blue]{0}[/COLOR] · {1}'.format(show_title, title)
            menuitems.append(( _addon.getLocalizedString(30005), 'XBMC.Container.Update('+plugin.url_for(get_list, show_url = show_id, category = 0)+')' ))
        if dur:
            l = dur.strip().split(':')
            duration = 0
            for pos, value in enumerate(l[::-1]):
                duration += int(value) * 60 ** pos

        list_item = xbmcgui.ListItem(title_label)
        list_item.setInfo('video', {'mediatype': 'episode', 'tvshowtitle': show_title, 'title': title, 'duration': duration, 'premiered': date})
        list_item.setArt({'icon': normalize_url(thumb)})
        list_item.setProperty('IsPlayable', 'true')
        list_item.addContextMenuItems(menuitems)
        listing.append((plugin.url_for(get_video, video_id), list_item, False))
    #hack pro Rozstrel
    next_url = soup.find('a', {'class': 'btn btn-on'})['href'] 
    if 'strana' in next_url:
        next_url = url+next_url
    if next_url:
        list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30003))
        list_item.setArt({'icon': 'DefaultFolder.png'})
        listing.append((plugin.url_for(get_list,  show_url = next_url, category = category), list_item, True))

    xbmcplugin.addDirectoryItems(plugin.handle, listing, len(listing))
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/get_video/<video_id>')
def get_video(video_id):
    xml = BeautifulSoup(get_page(_videourl+"?idvideo="+video_id), 'html.parser')
    server = xml.find("server").get_text()
    videofile = xml.find("linkvideo").find("file", {'quality': 'high'}).get_text()
    stream_url = 'https://'+server + "/" + videofile

    list_item = xbmcgui.ListItem(path=stream_url)
    xbmcplugin.setResolvedUrl(plugin.handle, True, list_item)

def normalize_url(url):
    url = url.replace("http://","https://")
    if url.startswith('//'):
        return 'https:' + url
    if not url.startswith('https://'):
        return _baseurl + url
    return url

def get_page(url):
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.68 Safari/537.36'})
    return r.content

@plugin.route('/')
def root():
    listing = []
    list_item = xbmcgui.ListItem(_addon.getLocalizedString(30001))
    list_item.setArt({'icon': 'DefaultRecentlyAddedEpisodes.png'})
    listing.append((plugin.url_for(get_list, show_url = _baseurl+'archiv', category = 1), list_item, True))

    list_item = xbmcgui.ListItem(_addon.getLocalizedString(30002))
    list_item.setArt({'icon': 'DefaultTVShows.png'})
    listing.append((plugin.url_for(list_shows), list_item, True))

    list_item = xbmcgui.ListItem(_addon.getLocalizedString(30004))
    list_item.setArt({'icon': 'DefaultTVShows.png'})
    listing.append((plugin.url_for(list_news), list_item, True))

    xbmcplugin.addDirectoryItems(plugin.handle, listing, len(listing))
    xbmcplugin.endOfDirectory(plugin.handle)

def run():
    plugin.run()
