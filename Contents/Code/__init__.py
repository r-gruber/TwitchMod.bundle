# Twitch.tv Plugin
# v0.1 by Marshall Thornton <marshallthornton@gmail.com>
# Code inspired by Justin.tv plugin by Trevor Cortez and John Roberts
# v0.2 by Nicolas Aravena <mhobbit@gmail.com>
# Adaptation of v0.1 for new Plex Media Server.

####################################################################################################

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

    ObjectContainer.art = R(ART)
    ObjectContainer.title1 = NAME
    DirectoryItem.thumb = R(ICON)
    
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:19.0) Gecko/20100101 Firefox/19.0'

####################################################################################################
@handler('/video/twitch', NAME, thumb=ICON, art=ART)
def MainMenu():
    oc = ObjectContainer()
	oc.add(DirectoryObject(key=Callback(FeaturedStreamsMenu), title="Featured Streams"))
    oc.add(DirectoryObject(key=Callback(GamesMenu), title="Games", summary="Browse live streams by game"))
    oc.add(InputDirectoryObject(key=Callback(SearchResults), title="Search", prompt="Search For A Stream", summary="Search for a stream"))

    return oc

####################################################################################################
@route('/video/twitch/featured')
def FeaturedStreamsMenu():

    oc = ObjectContainer(title2="Featured Streams")
    url  = "%s?limit=%s" % (TWITCH_FEATURED_STREAMS, PAGE_LIMIT)
    featured = JSON.ObjectFromURL(url, cacheTime=CACHE_INTERVAL)

    for stream in featured['featured']:
        subtitle = "%s\n%s Viewers" % (stream['stream']['game'], stream['stream']['viewers'])
        summary = String.StripTags(stream['text'])
        streamUrl = "%s&channel=%s" % (TWITCH_LIVE_PLAYER, stream['stream']['channel']['name'])
        oc.add(VideoClipObject(url=streamUrl, title=stream['stream']['channel']['display_name'], thumb=stream['stream']['preview'], subtitle=subtitle))

        return oc

####################################################################################################
@route('/video/twitch/games', page=int)
def GamesMenu(page=0):

    oc = ObjectContainer(title2="Top Games")
    url  = "%s?limit=%s&offset=%s" % (TWITCH_TOP_GAMES, PAGE_LIMIT, page*PAGE_LIMIT)
    games = JSON.ObjectFromURL(url, cacheTime=CACHE_INTERVAL)

    for game in games['top']:
        gameSummary = "%s Channels\n%s Viewers" % (game['channels'], game['viewers'])
        oc.add(DirectoryObject(key=Callback(ChannelMenu, game=game['game']['name'])), title=game['game']['name'], summary=gameSummary, thumb=game['game']['logo']['large'])

    if(len(games['top']) == 100):
        oc.add(DirectoryObject(key=Callback(GamesMenu, title = "More Games", page = (page+1))))

    return oc

####################################################################################################
@route('/video/twitch/channel')
def ChannelMenu(game=None):

    oc = ObjectContainer(title2=game)
    url = "%s?game=%s&limit=%s" % (TWITCH_LIST_STREAMS, String.Quote(game, usePlus=True), PAGE_LIMIT)
    streams = JSON.ObjectFromURL(url, cacheTime=CACHE_INTERVAL)

    for stream in streams['streams']:
        subtitle = " %s Viewers" % stream['viewers']
        streamURL = "%s&channel=%s" % (TWITCH_LIVE_PLAYER, stream['channel']['name'])
        oc.add(VideoClipObject(url=streamUrl, title=stream['channel']['display_name'], summary=stream['channel']['status'],thumb=stream['channel']['logo'], subtitle=subtitle, duration=0)))        

    return oc

####################################################################################################
def SearchResults(query=''):

    oc = ObjectContainer()
    results = JSON.ObjectFromURL("%s?query=%s&limit=%s" % (TWITCH_SEARCH_STREAMS, String.Quote(query, usePlus=True), PAGE_LIMIT), cacheTime=CACHE_INTERVAL)

    for stream in results['streams']:
        subtitle = "%s\n%s Viewers" % (stream['game'], stream['viewers'])
        streamURL = "%s&channel=%s" % (TWITCH_LIVE_PLAYER, stream['channel']['name'])
        oc.add(VideoClipObject(url=streamUrl, title=stream['channel']['display_name'], summary=stream['channel']['status'],thumb=stream['channel']['logo'], subtitle=subtitle, duration=0)))        

    if len(oc) < 1:
        return ObjectContainer(header="Not found", message="No streams were found that match your query.")

    return oc
