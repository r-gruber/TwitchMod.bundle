# TwitchMod by Cory <babylonstudio@gmail.com>
import calendar
from datetime import datetime, timedelta
from updater import Updater
from DumbTools import DumbKeyboard
from DumbTools import DumbPrefs

TWITCH_API_BASE = 'https://api.twitch.tv/kraken'
TWTICH_API_VERSION = 3
TWITCH_API_MIME_TYPE = "application/vnd.twitchtv.v{0}+json".format(TWTICH_API_VERSION)
PAGE_LIMIT = 20
NAME = 'TwitchMod'
PREFIX = '/video/twitchmod'
ICON = 'icon-default.png'
ART = 'art-default.png'
ICONS = {
    'search':    R('ic_search_c.png'),
    'following': R('ic_following_c.png'),
    'games':     R('ic_games_c.png'),
    'videos':    R('ic_videos_c.png'),
    'channels':  R('ic_channels_c.png'),
    'more':      R('ic_more_c.png'),
    'settings':  R('ic_settings_c.png'),
}

####################################################################################################
def api_request(endpoint, method='GET', params=None, cache_time=HTTP.CacheTime):
    url = url_encode(TWITCH_API_BASE+endpoint if endpoint.startswith('/') else endpoint,
                     params=params)
    try:
        data = JSON.ObjectFromURL(url, cacheTime=cache_time)
    except Exception as e:
        Log(e)
        return None
    else:
        return data


def url_encode(url, params=None):
    return url if params is None else \
           '%s?%s' % (url, '&'.join( ["%s=%s"%(String.Quote(str(k), usePlus=True),
                                               String.Quote(str(params[k]), usePlus=True))
                                      for k in params] ))


def utc_to_local(utc_dt):
    """ convert a utc datetime to a local datetime """
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)


def time_since(dt, pretty=False):
    """ return a string of the time since dt """
    delta = Datetime.Now() - utc_to_local(dt)
    seconds = delta.total_seconds()
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if not pretty:
        return "%d:%02d:%02d" % (h, m, s)
    d, h = divmod(h, 24)
    if d > 0:
        return "%d days ago" % d if d > 1 else "%d day ago" % d
    elif h > 0:
        return "%d hours ago" % h if h > 1 else "%d hour ago" % h
    elif m > 0:
        return "%d minutes ago" % m if m > 1 else "%d minute ago" % m
    return "now"


def error_message(error, message):
    return ObjectContainer(header=u'%s'%error, message=u'%s'%message)


def xstr(s):
    return '' if s is None else str(s)


def get_preview_image(url, cache_time=120):
    """
    workaround to keep preview images fresh. If the URL to the image for a thumb is different,
    it will reload it. This appends a "#" and a timestamp.
    The timestamp will change if 2 minutes have passed since the last time.
    """
    now = Datetime.TimestampFromDatetime(Datetime.Now())
    if 'last_update' not in Dict:
        Dict['last_update'] = 0
    if now - Dict['last_update'] > cache_time:
        Dict['last_update'] = now
        Dict.Save()
    return "%s#%d" % (url, Dict['last_update'])


def get_stream_objects(channels, cache_time=0):
    """
    get the streamObjects for the given list of channel names
    returns a dict, key is stream name, value is the 'stream object' json string
    """
    streams = api_request('/streams', params={'channel':','.join(channels)}, cache_time=cache_time)
    return {} if streams is None else {stream_object['channel']['name']: stream_object
                                       for stream_object in streams['streams']}


def stream_object_strings(stream_object, title_layout=None, title_separator='-'):
    """ consistent string formatting for a stream object """
    title_layout = title_layout if title_layout else Prefs['title_layout']
    status = xstr(stream_object['channel']['status'] \
             if 'status' in stream_object['channel'] else '?')
    start_time = Datetime.ParseDate(stream_object['created_at'])
    quality = "%dp%d" % (stream_object['video_height'], round(stream_object['average_fps']))
    viewers = "{:,}".format(int(stream_object['viewers']))
    viewers_string = "{0} {1}".format(viewers, L('viewers'))
    title_elements = {
        'name': stream_object['channel']['display_name'],
        'views': viewers_string,
        'status': status,
        'game': xstr(stream_object['channel']['game'] \
                if 'game' in stream_object['channel'] else '?'),
        'time': time_since(start_time),
        'quality': quality
    }

    title = [
        title_elements[e] for e in [x.strip() for x in title_layout.split(',')]
        if e in title_elements
    ]
    summary = "%s\nStarted %s\n%s\n\n%s" % (viewers_string, time_since(start_time, pretty=True),
                                            quality, status)
    separator = ' %s ' % title_separator
    return (separator.join(title), summary)


def stream_object_dir(stream_object, title_layout=None, title_separator='-'):
    """ turn a twitch stream object into a plex directory object that links to the channel menu """
    title, summary = stream_object_strings(stream_object, title_layout, title_separator)
    return DirectoryObject(
        key=Callback(ChannelMenu, channel_name=stream_object['channel']['name'],
                     stream_object=stream_object, refresh=True),
        title=u'%s'%title,
        summary=u'%s'%summary,
        tagline='%s,%d' % (stream_object['channel']['display_name'], stream_object['viewers']),
        thumb=Resource.ContentsOfURLWithFallback(
            get_preview_image(stream_object['preview']['medium']),
            fallback=ICONS['videos']))


def stream_object_vid(stream_object, title_layout=None, title_separator='-'):
    """ turn a twitch stream object into a plex video clip object """
    title, summary = stream_object_strings(stream_object, title_layout, title_separator)
    return VideoClipObject(
        url="1"+stream_object['channel']['url'],
        title=u'%s'%title,
        summary=u'%s'%summary,
        thumb=Resource.ContentsOfURLWithFallback(
            get_preview_image(stream_object['preview']['medium']), fallback=ICONS['videos']))


def channel_object_dir(channel_object, offline=False):
    """ turn a twitch channel object into a plex directory object that links to the channel menu """
    name = channel_object['name']
    display_name = channel_object['display_name']
    status = channel_object['status'] if 'status' in channel_object else '?'
    logo_img = channel_object['logo']
    title = "{0} - {1}".format(display_name, L('offline')) if offline else display_name
    return DirectoryObject(
        key=Callback(ChannelMenu, channel_name=name, stream_object=None, refresh=True),
        title=u'%s'%title,
        summary=u'%s'%status,
        tagline='%s,0'%display_name,
        thumb=Resource.ContentsOfURLWithFallback(logo_img, fallback=ICONS['videos']))

####################################################################################################
def Start():
    ObjectContainer.title1 = NAME
    ObjectContainer.art = R(ART)
    HTTP.Headers['User-Agent'] = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) '
                                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/33.0.1750.117 Safari/537.36')
    HTTP.Headers['Accept'] = TWITCH_API_MIME_TYPE
    HTTP.CacheTime = CACHE_1MINUTE

    if 'last_update' not in Dict:
        Dict['last_update'] = 0
        Dict.Save()

####################################################################################################
@handler(PREFIX, NAME, ICON, ART)
def MainMenu():
    oc = ObjectContainer(no_cache=True)
    Updater(PREFIX + '/updater', oc)
    oc.add(DirectoryObject(key=Callback(FeaturedStreamsList),
                           title=u'%s'%L('featured_streams'),
                           thumb=ICONS['channels']))
    oc.add(DirectoryObject(key=Callback(TopStreamsList),
                           title=u'%s'%L('top_streams'),
                           thumb=ICONS['channels']))
    oc.add(DirectoryObject(key=Callback(TopGamesList),
                           title=u'%s'%L('games'),
                           summary=u'%s'%L('browse_summary'),
                           thumb=ICONS['games']))
    oc.add(DirectoryObject(key=Callback(SearchMenu),
                           title=u'%s'%L('search'),
                           summary=u'%s'%L('search_prompt'),
                           thumb=ICONS['search']))
    oc.add(DirectoryObject(key=Callback(FollowedChannelsList),
                           title=u'%s'%(L('followed_channels')),
                           thumb=ICONS['following']))
    if Prefs['favourite_games']:
        oc.add(DirectoryObject(key=Callback(FavGames),
                               title=u'%s'%(L('favourite_games')),
                               thumb=ICONS['following']))
    if Client.Product in DumbPrefs.clients:
        DumbPrefs(PREFIX, oc, title=u'%s'%L('Preferences'), thumb=ICONS['settings'])
    else:
        oc.add(PrefsObject(title=u'%s'%L('Preferences'), thumb=ICONS['settings']))
    return oc

####################################################################################################
# ROUTES
####################################################################################################
@route(PREFIX + '/favourite/games')
def FavGames():
    oc = ObjectContainer(title2=u'%s'%L('favourite_games'))

    try:
        games = Prefs['favourite_games'].split(',')
    except Exception:
        return error_message(oc.title2, L('favourite_games_error'))

    for game in games:
        oc.add(DirectoryObject(key=Callback(SearchStreams, query=game.strip(),
                                            title_layout=Prefs['title_layout2']),
                               title=u'%s'%game,
                               thumb=ICONS['games']))
    return oc

####################################################################################################
@route(PREFIX + '/channel/{channel_name}/menu', refresh=bool, stream_object=dict)
def ChannelMenu(channel_name, refresh=True, stream_object=None):
    oc = ObjectContainer(title2=u'%s'%channel_name)

    # get a stream object if needed
    if refresh and stream_object is None:
        data = api_request("/streams/{0}".format(channel_name), cache_time=0)
        if data is not None:
            stream_object = data['stream']
    if stream_object is None:
        return error_message(oc.title2, "Error")

    # Watch Live (stream_object is only true when a channel is Live)
    oc.add(stream_object_vid(stream_object))
    # List Highlights
    oc.add(DirectoryObject(key=Callback(ChannelVodsList, channel=channel_name, broadcasts=False),
                           title=u'%s'%L('highlights'),
                           thumb=ICONS['videos']))
    # List Past Broadcasts
    oc.add(DirectoryObject(key=Callback(ChannelVodsList, channel=channel_name, broadcasts=True),
                           title=u'%s'%L('past_broadcasts'),
                           thumb=ICONS['videos']))
    return oc

####################################################################################################
# Two requests are made in this route
# 1. get a list of 'follow' objects, which contains the information for the channels
# 2. get a list of 'stream' objects, which contains info about the stream if its live
@route(PREFIX + '/following', limit=int)
def FollowedChannelsList(apiurl=None, limit=100):
    oc = ObjectContainer(title2=L('followed_channels'))

    # get a list of follows objects
    following = api_request(apiurl) if apiurl is not None else \
                api_request('/users/{0}/follows/channels'.format(Prefs['username']),
                            params={'limit':limit, 'sortby':'last_broadcast', 'direction':'desc'})
    if following is None:
        return error_message(oc.title2, L('followed_streams_list_error'))

    # gather all the channel names that the user is following
    followed_channels = [channel['channel']['name'] for channel in following['follows']]

    # get a list of stream objects for followed streams so we can add Live status to the title
    # an offline stream wont return a stream object
    stream_objects = get_stream_objects(followed_channels)

    # listing all the followed channels, both live and offline
    for channel in following['follows']:
        channel_object = channel['channel']
        channel_name = channel_object['name']
        if channel_name in stream_objects:
            oc.add(stream_object_dir(stream_objects[channel_name])) # live, has a stream object
        else:
            oc.add(channel_object_dir(channel_object, offline=True)) # not live

    # Sort the items
    if Prefs['following_order'] == 'view_count': # viewers desc
        oc.objects.sort(key=lambda obj: int(obj.tagline.split(',')[-1]), reverse=True)
    else: # name asc
        oc.objects.sort(key=lambda obj: obj.tagline.split(',')[0])

    if len(oc) >= limit:
        oc.add(NextPageObject(key=Callback(FollowedChannelsList,
                                           apiurl=following['_links']['next'], limit=limit),
                              title=u'%s'%L('more'),
                              thumb=ICONS['more']))
    return oc

####################################################################################################
@route(PREFIX + '/channel/vods', broadcasts=bool, limit=int)
def ChannelVodsList(channel=None, apiurl=None, broadcasts=True, limit=PAGE_LIMIT):
    oc = ObjectContainer(title2=L('past_broadcasts') if broadcasts else L('highlights'))

    videos = api_request(apiurl) if apiurl is not None else \
             api_request('/channels/{0}/videos'.format(channel),
                         params={'limit':limit, 'broadcasts':str(broadcasts).lower()})
    if videos is None:
        return error_message(oc.title2, "Error")

    ignored = 0
    for video in videos['videos']:
        url = video['url']
        vod_type = url.split('/')[-2]
        if vod_type != "v":
            ignored += 1
            continue
        vod_date = Datetime.ParseDate(video['recorded_at'])
        vod_title = video['title'] if video['title'] else L('untitled_broadcast')
        title = "{0} - {1}".format(vod_date.strftime('%a %b %d, %Y'), vod_title)
        oc.add(VideoClipObject(url="1"+url,
                               title=u'%s'%title,
                               summary=u'%s'%video['description'],
                               duration=int(video['length'])*1000,
                               thumb=Resource.ContentsOfURLWithFallback(video['preview'],
                                                                        fallback=ICONS['videos'])))

    if len(oc) + ignored >= limit:
        oc.add(NextPageObject(key=Callback(ChannelVodsList, apiurl=videos['_links']['next'],
                                           broadcasts=broadcasts, limit=limit),
                              title=u'%s'%L('more'),
                              thumb=ICONS['more']))
    return oc

####################################################################################################
@route(PREFIX + '/topstreams', limit=int)
def TopStreamsList(apiurl=None, limit=PAGE_LIMIT):
    oc = ObjectContainer(title2=L('top_streams'), no_cache=True)

    top = api_request(apiurl) if apiurl is not None else \
          api_request('/streams', params={'limit': limit})
    if top is None:
        return error_message(oc.title2, "Error")

    for stream in top['streams']:
        oc.add(stream_object_dir(stream))
    if len(oc) >= limit:
        oc.add(NextPageObject(key=Callback(TopStreamsList, apiurl=top['_links']['next']),
                              title=u'%s'%L('more'),
                              thumb=ICONS['more']))
    return oc

####################################################################################################
@route(PREFIX + '/featured', limit=int)
def FeaturedStreamsList(apiurl=None, limit=PAGE_LIMIT):
    oc = ObjectContainer(title2=L('featured_streams'), no_cache=True)

    featured = api_request(apiurl) if apiurl is not None else \
               api_request('/streams/featured', params={'limit': limit})
    if featured is None:
        return error_message(oc.title2, "Error")

    for featured_stream in featured['featured']:
        oc.add(stream_object_dir(featured_stream['stream']))
    if len(oc) >= limit:
        oc.add(NextPageObject(key=Callback(FeaturedStreamsList, apiurl=featured['_links']['next']),
                              title=u'%s'%L('more'),
                              thumb=ICONS['more']))
    return oc

####################################################################################################
@route(PREFIX + '/games', limit=int)
def TopGamesList(apiurl=None, limit=PAGE_LIMIT):
    oc = ObjectContainer(title2=L('top_games'), no_cache=True)

    games = api_request(apiurl) if apiurl is not None else \
            api_request('/games/top', params={'limit': limit})
    if games is None:
        return error_message(oc.title2, "Error")

    for game in games['top']:
        game_name = game['game']['name']
        game_summary = "{0} {1}\n{2} {3}".format(game['channels'], L('channels'),
                                                 game['viewers'], L('viewers'))
        oc.add(DirectoryObject(key=Callback(ChannelsForGameList, game=game_name),
                               title=u'%s'%game_name,
                               summary=u'%s'%game_summary,
                               thumb=Resource.ContentsOfURLWithFallback(
                                   game['game']['box']['medium'], fallback=ICONS['videos'])))
    if len(oc) >= limit:
        oc.add(NextPageObject(key=Callback(TopGamesList,
                                           apiurl=games['_links']['next']),
                              title=u'%s'%L('more'),
                              thumb=ICONS['more']))
    return oc

####################################################################################################
@route(PREFIX + '/channel', limit=int)
def ChannelsForGameList(game, apiurl=None, limit=PAGE_LIMIT):
    oc = ObjectContainer(title2=u'%s'%game, no_cache=True)

    streams = api_request(apiurl) if apiurl is not None else \
              api_request('/streams', params={'limit': limit, 'game': game})
    if streams is None:
        return error_message(oc.title2, "Error")

    for stream_object in streams['streams']:
        oc.add(stream_object_dir(stream_object, title_layout=Prefs['title_layout2']))
    if len(oc) >= limit:
        oc.add(NextPageObject(key=Callback(ChannelsForGameList, game=game,
                                           apiurl=streams['_links']['next'], limit=limit),
                              title=u'%s'%L('more'),
                              thumb=ICONS['more']))
    return oc

####################################################################################################
@route(PREFIX + '/search')
def SearchMenu():
    oc = ObjectContainer(title2=L('search'))

    if Client.Product in DumbKeyboard.clients:
        DumbKeyboard(PREFIX, oc, SearchStreams,
                     dktitle=u'%s %s' % (L('search'), L('streams')),
                     dkthumb=ICONS['search'])
        DumbKeyboard(PREFIX, oc, SearchChannels,
                     dktitle=u'%s %s' % (L('search'), L('channels')),
                     dkthumb=ICONS['search'])
        DumbKeyboard(PREFIX, oc, SearchGames,
                     dktitle=u'%s %s' % (L('search'), L('games')),
                     dkthumb=ICONS['search'])
    else:
        oc.add(InputDirectoryObject(key=Callback(SearchStreams),
                                    title=u'%s %s' % (L('search'), L('streams')),
                                    thumb=ICONS['search'],
                                    prompt=u'%s %s' % (L('search_prompt'), L('streams'))))
        oc.add(InputDirectoryObject(key=Callback(SearchChannels),
                                    title=u'%s %s' % (L('search'), L('channels')),
                                    thumb=ICONS['search'],
                                    prompt=u'%s %s' % (L('search_prompt'), L('channels'))))
        oc.add(InputDirectoryObject(key=Callback(SearchGames),
                                    title=u'%s %s' % (L('search'), L('games')),
                                    thumb=ICONS['search'],
                                    prompt=u'%s %s' % (L('search_prompt'), L('games'))))
    return oc


@route(PREFIX + '/search/streams', limit=int)
def SearchStreams(query, apiurl=None, limit=PAGE_LIMIT, title_layout=None):
    oc = ObjectContainer(title2=L('search'), no_cache=True)

    results = api_request(apiurl) if apiurl is not None else \
              api_request('/search/streams', params={'query':query, 'limit':limit})
    if results is None:
        return error_message(oc.title2, "Error")
    if not results['streams']:
        return error_message(L('search'), L('search_error'))

    for stream_object in results['streams']:
        oc.add(stream_object_dir(stream_object, title_layout=title_layout))
    if len(oc) >= limit:
        oc.add(NextPageObject(key=Callback(SearchStreams, query=query, limit=limit,
                                           apiurl=results['_links']['next'],
                                           title_layout=title_layout),
                              title=u'%s'%L('more'),
                              thumb=ICONS['more']))
    return oc


@route(PREFIX + '/search/channels', limit=int)
def SearchChannels(query, apiurl=None, limit=PAGE_LIMIT):
    oc = ObjectContainer(title2=L('search'), no_cache=True)

    results = api_request(apiurl) if apiurl is not None else \
              api_request('/search/channels', params={'query':query, 'limit':limit})
    if results is None:
        return error_message(oc.title2, "Error")
    if not results['channels']:
        return error_message(L('search'), L('search_error'))

    for channel_object in results['channels']:
        oc.add(channel_object_dir(channel_object))
    if len(oc) >= limit:
        oc.add(NextPageObject(key=Callback(SearchChannels, query=query,
                                           apiurl=results['_links']['next'], limit=limit),
                              title=u'%s'%L('more'),
                              thumb=ICONS['more']))
    return oc


@route(PREFIX + '/search/games')
def SearchGames(query, apiurl=None):
    oc = ObjectContainer(title2=L('search'), no_cache=True)

    results = api_request(apiurl) if apiurl is not None else \
              api_request('/search/games', params={'query':query, 'type':'suggest', 'live':'true'})
    if results is None:
        return error_message(oc.title2, "Error")
    if not results['games']:
        return error_message(L('search'), L('search_error'))

    for game in results['games']:
        oc.add(DirectoryObject(key=Callback(ChannelsForGameList, game=game['name']),
                               title=u'%s'%game['name'],
                               thumb=Resource.ContentsOfURLWithFallback(
                                   game['box']['medium'], fallback=ICONS['videos'])))
    return oc
