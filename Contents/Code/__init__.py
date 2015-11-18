#-*- encoding: utf-8 -*-
# Twitch.tv Plugin
# v0.1 by Marshall Thornton <marshallthornton@gmail.com>
# Code inspired by Justin.tv plugin by Trevor Cortez and John Roberts
# v0.2 by Nicolas Aravena <mhobbit@gmail.com>
# Adaptation of v0.1 for new Plex Media Server.
# v0.3 by Cory <babylonstudio@gmail.com>
# added followed streams, vod support, quality options

import calendar
from datetime import datetime, timedelta
from updater import Updater
from DumbKeyboard import DumbKeyboard
from DumbPrefs import DumbPrefs
####################################################################################################
TWITCH_API_BASE      = 'https://api.twitch.tv/kraken'
TWTICH_API_VERSION   = 3
TWITCH_API_MIME_TYPE = "application/vnd.twitchtv.v{0}+json".format(TWTICH_API_VERSION)

TWITCH_FEATURED_STREAMS = TWITCH_API_BASE + '/streams/featured'
TWITCH_TOP_GAMES        = TWITCH_API_BASE + '/games/top'
TWITCH_SEARCH_STREAMS   = TWITCH_API_BASE + '/search/streams'
TWITCH_SEARCH_CHANNELS  = TWITCH_API_BASE + '/search/channels'
TWITCH_SEARCH_GAMES     = TWITCH_API_BASE + '/search/games'
TWITCH_FOLLOWED_STREAMS = TWITCH_API_BASE + '/users/{0}/follows/channels'
TWITCH_STREAMS          = TWITCH_API_BASE + '/streams'
TWITCH_STREAMS_CHANNEL  = TWITCH_API_BASE + '/streams/{0}'
TWITCH_STREAMS_CHANNELS = TWITCH_API_BASE + '/streams?channel={0}'
TWITCH_CHANNELS         = TWITCH_API_BASE + '/channels/{0}'
TWITCH_CHANNELS_VODS    = TWITCH_API_BASE + '/channels/{0}/videos'

PAGE_LIMIT = 20
NAME = 'TwitchMod'
PATH = '/video/twitchmod'

ICONS = {
        'art':       R('art-default.jpg'),
        'search':    R('ic_search_c.png'),
        'following': R('ic_following_c.png'),
        'games':     R('ic_games_c.png'),
        'videos':    R('ic_videos_c.png'),
        'channels':  R('ic_channels_c.png'),
        'more':      R('ic_more_c.png'),
        'settings':  R('ic_settings_c.png'),
}

####################################################################################################
# Shared Functions
####################################################################################################
# twitch gives utc timestamps. convert them to local time so we can get delta
def utc_to_local(utc_dt):
        timestamp = calendar.timegm(utc_dt.timetuple())
        local_dt = datetime.fromtimestamp(timestamp)
        assert utc_dt.resolution >= timedelta(microseconds=1)
        return local_dt.replace(microsecond=utc_dt.microsecond)

def TimeSince(dt, pretty=False):

        delta = Datetime.Now() - utc_to_local(dt)
        seconds = delta.total_seconds()

        m, s = divmod(seconds,60)
        h, m = divmod(m, 60)
        
        if not pretty:
                return "%d:%02d:%02d" % (h,m,s)

        d, h = divmod(h, 24)
        if d > 0:
                return "%d days ago" % d if d > 1 else "%d day ago" % d
        elif h > 0:
                return "%d hours ago" % h if h > 1 else "%d hour ago" % h
        elif m > 0:
                return "%d minutes ago" % m if m > 1 else "%d minute ago" % m
        return "now"    

def ErrorMessage(error, message):

        return ObjectContainer(
                header  = u'%s' % error,
                message = u'%s' % message, 
        )

def xstr(s):

        return '' if s is None else str(s)

# workaround to keep preview images fresh. If the URL to the image for a thumb is different, it will reload it.
# so this appends a "#" and a timestamp. the timestamp will change if 2 minutes have passed since the last time.
def GetPreviewImage(url, cacheTime=120):

        now = Datetime.TimestampFromDatetime(Datetime.Now())

        if 'last_update' not in Dict:
                Dict['last_update'] = 0

        if now - Dict['last_update'] > cacheTime:
                Dict['last_update'] = now
                Dict.Save()

        return "%s#%d" % (url,Dict['last_update'])

# get the streamObjects for the given list of channel names
# returns a dict, key is stream name, value is the 'stream object' json string
def GetStreamObjects(channels, cacheTime=0):

        streamObjects = {}

        try:
                url     = TWITCH_STREAMS_CHANNELS.format(','.join(channels))
                streams = JSON.ObjectFromURL(url, cacheTime=cacheTime)
        except:
                return streamObjects

        for streamObject in streams['streams']:
                streamObjects[streamObject['channel']['name']] = streamObject

        return streamObjects

# consistent string formatting for a stream object
def StringsFromStreamObject(streamObject, titleLayout=None, titleSeparator='-'):

        titleLayout  = titleLayout if titleLayout else Prefs['title_layout']

        name         = streamObject['channel']['name']
        display_name = streamObject['channel']['display_name']
        status       = xstr(streamObject['channel']['status'] if 'status' in streamObject['channel'] else '?')
        game         = xstr(streamObject['channel']['game'] if 'game' in streamObject['channel'] else '?')
        start_time   = Datetime.ParseDate(streamObject['created_at'])
        quality      = "%dp%d" % (streamObject['video_height'], round(streamObject['average_fps']))

        viewers        = "{:,}".format(int(streamObject['viewers']))
        viewers_string = "{0} {1}".format(viewers, L('viewers'))
      
        title_elements = {
                'name':    display_name,
                'views':   viewers_string,
                'status':  status,
                'game':    game,
                'time':    TimeSince(start_time),
                'quality': quality
        }

        title   = [title_elements[element] for element in [x.strip() for x in titleLayout.split(',')] if element in title_elements]
        summary = "%s\nStarted %s\n%s\n\n%s" % (viewers_string, TimeSince(start_time, pretty=True), quality, status)
       
        separator = ' %s ' % titleSeparator

        return (separator.join(title), summary)

# given a streamObject (dict), return a DirectoryObject
# titleLayout is a comma separated string. possible items are the contents of title_elements
def DirectoryObjectFromStreamObject(streamObject, titleLayout=None, titleSeparator='-'):

        title,summary = StringsFromStreamObject(streamObject, titleLayout=titleLayout, titleSeparator=titleSeparator)

        return DirectoryObject(
                key     = Callback(ChannelMenu, channelName=streamObject['channel']['name'], streamObject=streamObject),
                title   = u'%s' % title,
                summary = u'%s' % summary,
                tagline = '%s,%d' % (streamObject['channel']['display_name'], streamObject['viewers']),
                thumb   = Resource.ContentsOfURLWithFallback(GetPreviewImage(streamObject['preview']['medium']), fallback=ICONS['videos'])
        )

# given a streamObject, return a VideoClipObject that will play the stream
def VideoClipObjectFromStreamObject(streamObject, titleLayout=None, titleSeparator='-'):

        title,summary = StringsFromStreamObject(streamObject, titleLayout=titleLayout, titleSeparator=titleSeparator)

        return VideoClipObject(
                url     = "1" + streamObject['channel']['url'],
                title   = u'%s' % title,
                summary = u'%s' % summary,
                thumb   = Resource.ContentsOfURLWithFallback(GetPreviewImage(streamObject['preview']['medium']), fallback=ICONS['videos'])
        )

def DirectoryObjectFromChannelObject(channelObject, offline=False):

        name         = channelObject['name']
        display_name = channelObject['display_name']
        status       = channelObject['status'] if 'status' in channelObject else '?'
        logo_img     = channelObject['logo']

        title = "{0} - {1}".format(display_name, L('offline')) if offline else display_name

        return DirectoryObject(
                key     = Callback(ChannelMenu, channelName=name),
                title   = u'%s' % title,
                summary = u'%s' % status,
                tagline = '%s,0' % display_name,
                thumb   = Resource.ContentsOfURLWithFallback(logo_img, fallback=ICONS['videos'])
        )

####################################################################################################
def Start():

        ObjectContainer.title1 = NAME
        ObjectContainer.art    = ICONS['art']
        
        HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.117 Safari/537.36'
        HTTP.Headers['Accept']     = TWITCH_API_MIME_TYPE
        HTTP.CacheTime = CACHE_1MINUTE

        if 'last_update' not in Dict:
                Dict['last_update'] = 0
                Dict.Save()

####################################################################################################
@handler(PATH, NAME, art=ICONS['art'])
def MainMenu():

        oc = ObjectContainer(no_cache=True)
        Updater(PATH + '/updater', oc)

        oc.add(DirectoryObject(
                key   = Callback(FeaturedStreamsList),
                title = u'%s' % L('featured_streams'),
                thumb = ICONS['channels'],
        ))

        oc.add(DirectoryObject(
                key   = Callback(TopStreamsList),
                title = u'%s' % L('top_streams'),
                thumb = ICONS['channels'],
        ))

        oc.add(DirectoryObject(
                key     = Callback(TopGamesList),
                title   = u'%s' % L('games'),
                summary = u'%s' % L('browse_summary'),
                thumb   = ICONS['games'],
        ))

        oc.add(DirectoryObject(
                key     = Callback(SearchMenu),
                title   = u'%s' % L('search'),
                summary = u'%s' % L('search_prompt'),
                thumb   = ICONS['search'],
        ))

        oc.add(DirectoryObject(
                key   = Callback(FollowedChannelsList),
                title = u'%s' % (L('followed_channels')),
                thumb = ICONS['following'],
        ))

        if Prefs['favourite_games']:
                oc.add(DirectoryObject(
                        key   = Callback(FavGames),
                        title = u'%s' % (L('favourite_games')),
                        thumb = ICONS['following'],
                ))       

        if Client.Product in DumbPrefs.clients:
                DumbPrefs(PATH, oc,
                        title = u'%s' % L('Preferences'),
                        thumb = ICONS['settings'])
        else:
                oc.add(PrefsObject(
                        title   = u'%s' % L('Preferences'),
                        tagline = u'%s' % L('Preferences'),
                        summary = u'%s' % L('Preferences'),
                        thumb   = ICONS['settings'],
                ))

        return oc

####################################################################################################
@route(PATH + '/favourite/games')
def FavGames():

        oc = ObjectContainer()

        try:
                games = Prefs['favourite_games'].split(',')
        except:
                games = []

        for game in games:
                oc.add(DirectoryObject(
                        key = Callback(SearchStreams, query=game.strip(), titleLayout=Prefs['title_layout2']),
                        title = u'%s' % game,
                        thumb = ICONS['games']
                ))

        return oc

####################################################################################################
@route(PATH + '/channel/{channelName}/menu', refresh=bool, streamObject=dict)
def ChannelMenu(channelName, refresh=True, streamObject=None):
        
        oc = ObjectContainer(title2=u'%s' % channelName)

        # get a stream object if needed
        if refresh and not streamObject:
                url = TWITCH_STREAMS_CHANNEL.format(channelName)
                streamObject = JSON.ObjectFromURL(url, cacheTime=0)['stream']

        # Watch Live (streamObject is only true when a channel is Live)
        if streamObject:
                oc.add(VideoClipObjectFromStreamObject(streamObject))

        # List Highlights
        oc.add(DirectoryObject(
                key   = Callback(ChannelVodsList, channel=channelName, broadcasts=False),
                title = u'%s' % L('highlights'),
                thumb = ICONS['videos'],
        ))

        # List Past Broadcasts
        oc.add(DirectoryObject(
                key   = Callback(ChannelVodsList, channel=channelName, broadcasts=True),
                title = u'%s' % L('past_broadcasts'),
                thumb = ICONS['videos'],
        ))

        return oc

####################################################################################################
# Two requests are made in this route
# 1. get a list of 'follow' objects, which contains the information for the channels
# 2. get a list of 'stream' objects, which contains info about the stream if its live
@route(PATH + '/following', limit=int)
def FollowedChannelsList(apiurl=None, limit=100):

        oc = ObjectContainer(title2=L('followed_channels'))

        username = Prefs['username']

        # twitch apis provide the 'next' urls for paging, so we only need to construct ours once
        if not apiurl:
                params = "?limit={0}&sortby=last_broadcast&direction=desc".format(limit)
                apiurl = TWITCH_FOLLOWED_STREAMS.format(username) + params

        # get a list of follows objects
        try:
                following = JSON.ObjectFromURL(apiurl, cacheTime=0)
        except:
                return ErrorMessage(L('followed_channels'), L('followed_streams_list_error'))            

        # gather all the channel names that the user is following
        followed_channels = [channel['channel']['name'] for channel in following['follows']]

        # get a list of stream objects for followed streams so we can add Live status to the title
        # an offline stream wont return a stream object
        streamObjects = GetStreamObjects(followed_channels)

        # listing all the followed channels, both live and offline
        for channel in following['follows']:
                channelObject = channel['channel']
                channel_name  = channelObject['name']

                if channel_name in streamObjects:
                        # live, has a stream object
                        oc.add(DirectoryObjectFromStreamObject(streamObjects[channel_name]))
                else:
                        # not live, doesnt have a streamobject, use channel info
                        oc.add(DirectoryObjectFromChannelObject(channelObject, offline=True))

        # Sort the items
        if Prefs['following_order'] == 'view_count':
                # viewers desc
                oc.objects.sort(key=lambda obj: int(obj.tagline.split(',')[-1]), reverse=True)
        else:
                # name asc
                oc.objects.sort(key=lambda obj: obj.tagline.split(',')[0], reverse=False)

        if len(oc) >= limit:
                oc.add(NextPageObject(
                        key   = Callback(FollowedChannelsList, apiurl=following['_links']['next'], limit=limit),
                        title = u'%s' % L('more'),
                        thumb = ICONS['more'],
                ))

        return oc

####################################################################################################
@route(PATH + '/channel/vods', broadcasts=bool, limit=int)
def ChannelVodsList(channel=None, apiurl=None, broadcasts=True, limit=PAGE_LIMIT):
     
        oc = ObjectContainer(title2=L('past_broadcasts') if broadcasts else L('highlights'))
        
        if not apiurl:
                params = "?limit={0}&broadcasts={1}".format(limit, str(broadcasts).lower())
                apiurl = TWITCH_CHANNELS_VODS.format(channel) + params

        videos = JSON.ObjectFromURL(apiurl)

        ignored = 0
        for video in videos['videos']:
                url      = video['url']
                vod_type = url.split('/')[-2]
                
                if vod_type == "v":
                        vod_date    = Datetime.ParseDate(video['recorded_at'])
                        vod_title   = video['title'] if video['title'] else L('untitled_broadcast')
                        description = video['description']
                        length      = int(video['length']) * 1000

                        title       = "{0} - {1}".format(vod_date.strftime('%a %b %d, %Y'), vod_title)

                        oc.add(VideoClipObject(
                                url      = "1" + url,
                                title    = u'%s' % title,
                                summary  = u'%s' % description,
                                duration = length,
                                thumb    = Resource.ContentsOfURLWithFallback(video['preview'], fallback=ICONS['videos']),
                        ))
                else: 
                        ignored += 1

        if len(oc) + ignored >= limit:
                oc.add(NextPageObject(
                        key   = Callback(ChannelVodsList, apiurl=videos['_links']['next'], broadcasts=broadcasts, limit=limit),
                        title = u'%s' % L('more'),
                        thumb = ICONS['more'],
                ))

        return oc

####################################################################################################
@route(PATH + '/topstreams', limit=int)
def TopStreamsList(apiurl=None, limit=PAGE_LIMIT):
        oc = ObjectContainer(title2=L('top_streams'), no_cache=True)

        if not apiurl:
               params = "?limit={0}".format(limit)
               apiurl = TWITCH_STREAMS + params

        top = JSON.ObjectFromURL(apiurl)

        for stream in top['streams']:
                oc.add(DirectoryObjectFromStreamObject(stream))

        # featured streams doesnt provide a total
        if len(oc) >= limit:
                oc.add(NextPageObject(
                        key   = Callback(TopStreamsList, apiurl=top['_links']['next']),
                        title = u'%s' % L('more'),
                        thumb = ICONS['more'],
                ))

        return oc

####################################################################################################
@route(PATH + '/featured', limit=int)
def FeaturedStreamsList(apiurl=None, limit=PAGE_LIMIT):

        oc = ObjectContainer(title2=L('featured_streams'), no_cache=True)

        if not apiurl:
               params = "?limit={0}".format(limit)
               apiurl = TWITCH_FEATURED_STREAMS + params

        featured = JSON.ObjectFromURL(apiurl)

        for featured_stream in featured['featured']:
                streamObject = featured_stream['stream']
                oc.add(DirectoryObjectFromStreamObject(streamObject))

        # featured streams doesnt provide a total
        if len(oc) >= limit:
                oc.add(NextPageObject(
                        key   = Callback(FeaturedStreamsList, apiurl=featured['_links']['next']),
                        title = u'%s' % L('more'),
                        thumb = ICONS['more'],
                ))

        return oc

####################################################################################################
@route(PATH + '/games', limit=int)
def TopGamesList(apiurl=None, limit=PAGE_LIMIT):

        oc = ObjectContainer(title2=L('top_games'), no_cache=True)

        if not apiurl:
                params = "?limit={0}".format(limit)
                apiurl = TWITCH_TOP_GAMES + params

        games = JSON.ObjectFromURL(apiurl)

        for game in games['top']:
                game_name    = game['game']['name']
                game_summary = "{0} {1}\n{2} {3}".format(game['channels'], L('channels'), game['viewers'], L('viewers'))
                thumb        = game['game']['box']['medium']

                oc.add(DirectoryObject(
                        key     = Callback(ChannelsForGameList, game=game_name),
                        title   = u'%s' % game_name,
                        summary = u'%s' % game_summary,
                        thumb   = Resource.ContentsOfURLWithFallback(thumb, fallback=ICONS['videos']),
                ))

        if len(oc) >= limit:
                oc.add(NextPageObject(
                        key   = Callback(TopGamesList, apiurl=games['_links']['next']),
                        title = u'%s' % L('more'),
                        thumb = ICONS['more'],
                ))

        return oc

####################################################################################################
@route(PATH + '/channel', limit=int)
def ChannelsForGameList(game, apiurl=None, limit=PAGE_LIMIT):

        oc = ObjectContainer(title2=u'%s' % game, no_cache=True)
                
        if not apiurl:
                params = "?game={0}&limit={1}".format(String.Quote(game, usePlus=True), limit)
                apiurl = TWITCH_STREAMS + params

        streams = JSON.ObjectFromURL(apiurl)

        for streamObject in streams['streams']:
                oc.add(DirectoryObjectFromStreamObject(streamObject, titleLayout=Prefs['title_layout2']))            

        if len(oc) >= limit:
                oc.add(NextPageObject(
                        key   = Callback(ChannelsForGameList, game=game, apiurl=streams['_links']['next'], limit=limit),
                        title = u'%s' % L('more'),
                        thumb = ICONS['more'],
                ))

        return oc

####################################################################################################
@route(PATH + '/search')
def SearchMenu():

        oc = ObjectContainer()

        if Client.Product in DumbKeyboard.clients:
                DumbKeyboard(PATH, oc, SearchStreams,
                        dktitle = u'%s %s' % (L('search'), L('streams')),
                        dkthumb = ICONS['search'])
                DumbKeyboard(PATH, oc, SearchChannels,
                        dktitle = u'%s %s' % (L('search'), L('channels')),
                        dkthumb = ICONS['search'])
                DumbKeyboard(PATH, oc, SearchGames,
                        dktitle = u'%s %s' % (L('search'), L('games')),
                        dkthumb = ICONS['search'])
        else:
                oc.add(InputDirectoryObject(
                        key    = Callback(SearchStreams),
                        title  = u'%s %s' % (L('search'), L('streams')),
                        thumb  = ICONS['search'],
                        prompt = u'%s %s' % (L('search_prompt'), L('streams')),
                ))
                oc.add(InputDirectoryObject(
                        key    = Callback(SearchChannels),
                        title  = u'%s %s' % (L('search'), L('channels')),
                        thumb  = ICONS['search'],
                        prompt = u'%s %s' % (L('search_prompt'), L('channels')),
                ))
                oc.add(InputDirectoryObject(
                        key    = Callback(SearchGames),
                        title  = u'%s %s' % (L('search'), L('games')),
                        thumb  = ICONS['search'],
                        prompt = u'%s %s' % (L('search_prompt'), L('games')),
                ))

        return oc

# results are live streams
@route(PATH + '/search/streams', limit=int)
def SearchStreams(query, apiurl=None, limit=PAGE_LIMIT, titleLayout=None):

        oc = ObjectContainer(title2=L('search'), no_cache=True)

        if not apiurl:
                params = "?query={0}&limit={1}".format(String.Quote(query, usePlus=True), limit)
                apiurl = TWITCH_SEARCH_STREAMS + params

        results = JSON.ObjectFromURL(apiurl)

        for streamObject in results['streams']:
                oc.add(DirectoryObjectFromStreamObject(streamObject, titleLayout=titleLayout))

        if len(oc) < 1:
                return ErrorMessage(L('search'), L('search_error'))

        if len(oc) >= limit:
                oc.add(NextPageObject(
                        key   = Callback(SearchStreams, query=query, apiurl=results['_links']['next'], limit=limit, titleLayout=titleLayout),
                        title = u'%s' % L('more'),
                        thumb = ICONS['more'],
                ))                

        return oc

# results are channels, with no indication of being online/offline
@route(PATH + '/search/channels', limit=int)
def SearchChannels(query, apiurl=None, limit=PAGE_LIMIT):

        oc = ObjectContainer(title2=L('search'), no_cache=True)

        if not apiurl:
                params = "?query={0}&limit={1}".format(String.Quote(query, usePlus=True), limit)
                apiurl = TWITCH_SEARCH_CHANNELS + params

        results = JSON.ObjectFromURL(apiurl)

        for channelObject in results['channels']:
                oc.add(DirectoryObjectFromChannelObject(channelObject))

        if len(oc) < 1:
                return ErrorMessage(L('search'), L('search_error'))

        if len(oc) >= limit:
                oc.add(NextPageObject(
                        key   = Callback(SearchChannels, query=query, apiurl=results['_links']['next'], limit=limit),
                        title = u'%s' % L('more'),
                        thumb = ICONS['more'],
                ))                

        return oc

# results are game titles that are similar to the query
@route(PATH + '/search/games')
def SearchGames(query, apiurl=None):

        oc = ObjectContainer(title2=L('search'), no_cache=True)

        if not apiurl:
                params = "?query={0}&type=suggest&live=true".format(String.Quote(query, usePlus=True))
                apiurl = TWITCH_SEARCH_GAMES + params

        results = JSON.ObjectFromURL(apiurl)

        for game in results['games']:
                oc.add(DirectoryObject(
                        key   = Callback(ChannelsForGameList, game=game['name']),
                        title = u'%s' % game['name'],
                        thumb = Resource.ContentsOfURLWithFallback(game['box']['medium'], fallback=ICONS['videos']),
                ))

        if len(oc) < 1:
                return ErrorMessage(L('search'), L('search_error'))

        # no paging on search/games

        return oc