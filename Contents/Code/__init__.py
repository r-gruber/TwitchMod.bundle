# Twitch.tv Plugin
# v0.1 by Marshall Thornton <marshallthornton@gmail.com>
# Code inspired by Justin.tv plugin by Trevor Cortez and John Roberts
# v0.2 by Nicolas Aravena <mhobbit@gmail.com>
# Adaptation of v0.1 for new Plex Media Server.

####################################################################################################

from html_helper import strip_tags
import urllib

TWITCH_LIST_STREAMS     = 'https://api.twitch.tv/kraken/streams'
TWITCH_FEATURED_STREAMS = 'https://api.twitch.tv/kraken/streams/featured'
TWITCH_TOP_GAMES        = 'https://api.twitch.tv/kraken/games/top'
TWITCH_SEARCH_STREAMS   = 'https://api.twitch.tv/kraken/search/streams'
TWITCH_LIVE_PLAYER      = 'http://www-cdn.jtvnw.net/widgets/live_embed_player.swf?auto_play=true'

PAGE_LIMIT              = 100
CACHE_INTERVAL          = 600
NAME                    = 'Twitch.tv'
ART                     = 'art-default.jpg'
ICON                    = 'icon-default.png'


####################################################################################################
def Start():
    Plugin.AddViewGroup("List", viewMode = "List", mediaType = "items")

    ObjectContainer.art = R(ART)
    ObjectContainer.title1 = NAME
    ObjectContainer.view_group = "List"
    DirectoryItem.thumb = R(ICON)
    
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:15.0) Gecko/20100101 Firefox/15.0.1'


@handler "/video/twitch"
def MainMenu():
    oc = ObjectContainer()
	oc.add(DirectoryObject(key=Callback(FeaturedStreamsMenu), title="Featured Streams"))
    oc.add(DirectoryObject(key=Callback(GamesMenu), title="Games", summary="Browse live streams by game"))
    oc.add(InputDirectoryObject(key=Callback(SearchResults), title="Search", prompt="Search For A Stream", summary="Search for a stream"))

    return oc
    
@route('/video/twitch/featured', page=int, cacheTime=int, allow_sync=True)
def FeaturedStreamsMenu(sender, page=None):
    oc = ObjectContainer(view_group="List", title2="Featured Streams")
    url  = "%s?limit=%s" % (TWITCH_FEATURED_STREAMS, PAGE_LIMIT)

    featured = JSON.ObjectFromURL(url, cacheTime=CACHE_INTERVAL)
   
    for stream in featured['featured']:
        subtitle = "%s\n%s Viewers" % (stream['stream']['game'], stream['stream']['viewers'])
        summary = strip_tags(stream['text'])
        streamUrl = "%s&channel=%s" % (TWITCH_LIVE_PLAYER, stream['stream']['channel']['name'])
        oc.add(VideoClipObject(url=streamUrl, title=stream['stream']['channel']['display_name'], thumb=stream['stream']['preview'], subtitle=subtitle))

        return oc

@route('/video/twitch/games', page=int, cacheTime=int, allow_sync=True)
def GamesMenu(sender, page=0):
    oc = ObjectContainer(view_group="List", title2="Top Games")
    url  = "%s?limit=%s&offset=%s" % (TWITCH_TOP_GAMES, PAGE_LIMIT, page*PAGE_LIMIT)

    games = JSON.ObjectFromURL(url, cacheTime=CACHE_INTERVAL)
   
    for game in games['top']:
        gameSummary = "%s Channels\n%s Viewers" % (game['channels'], game['viewers'])
        oc.add(DirectoryObject(key=Callback(ChannelMenu, game=game['game']['name'])), title=game['game']['name'], summary=gameSummary, thumb=game['game']['logo']['large'])

    if(len(games['top']) == 100):
        oc.add(DirectoryObject(key=Callback(GamesMenu, title = "More Games", page = (page+1))))

    return oc


def ChannelMenu(sender, game=None):
    oc = ObjectContainer(title2=sender.itemTitle)
    url = "%s?game=%s&limit=%s" % (TWITCH_LIST_STREAMS, urllib.quote_plus(game), PAGE_LIMIT)

    streams = JSON.ObjectFromURL(url, cacheTime=CACHE_INTERVAL)

    for stream in streams['streams']:
        subtitle = " %s Viewers" % stream['viewers']
        streamURL = "%s&channel=%s" % (TWITCH_LIVE_PLAYER, stream['channel']['name'])
        oc.add(VideoClipObject(url=streamUrl, title=stream['channel']['display_name'], summary=stream['channel']['status'],thumb=stream['channel']['logo'], subtitle=subtitle, duration=0)))        

    return oc


def SearchResults(sender, query=None):
    oc = ObjectContainer()

    results = JSON.ObjectFromURL("%s?query=%s&limit=%s" % (TWITCH_SEARCH_STREAMS, urllib.quote_plus(query), PAGE_LIMIT), cacheTime=CACHE_INTERVAL)

    for stream in results['streams']:
        subtitle = "%s\n%s Viewers" % (stream['game'], stream['viewers'])
        streamURL = "%s&channel=%s" % (TWITCH_LIVE_PLAYER, stream['channel']['name'])
        oc.add(VideoClipObject(url=streamUrl, title=stream['channel']['display_name'], summary=stream['channel']['status'],thumb=stream['channel']['logo'], subtitle=subtitle, duration=0)))        
    if len(dir) > 0:
        return oc
    else:
        return ObjectContainer(header="Not found", message="No streams were found that match your query.") 
