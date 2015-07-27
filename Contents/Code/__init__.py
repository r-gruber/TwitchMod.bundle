#-*- encoding: utf-8 -*-
# Twitch.tv Plugin
# v0.1 by Marshall Thornton <marshallthornton@gmail.com>
# Code inspired by Justin.tv plugin by Trevor Cortez and John Roberts
# v0.2 by Nicolas Aravena <mhobbit@gmail.com>
# Adaptation of v0.1 for new Plex Media Server.
# v0.3 by Cory <babylonstudio@gmail.com>
# added followed streams, vod support, quality options

####################################################################################################
TWITCH_API_BASE      = 'https://api.twitch.tv/kraken'
TWTICH_API_VERSION   = 3
TWITCH_API_MIME_TYPE = "application/vnd.twitchtv.v{0}+json".format(TWTICH_API_VERSION)

TWITCH_FEATURED_STREAMS = TWITCH_API_BASE + '/streams/featured'
TWITCH_TOP_GAMES        = TWITCH_API_BASE + '/games/top'
TWITCH_SEARCH_STREAMS   = TWITCH_API_BASE + '/search/streams'
TWITCH_FOLLOWED_STREAMS = TWITCH_API_BASE + '/users/{0}/follows/channels'
TWITCH_STREAMS          = TWITCH_API_BASE + '/streams'
TWITCH_STREAMS_CHANNEL  = TWITCH_API_BASE + '/streams/{0}'
TWITCH_STREAMS_CHANNELS = TWITCH_API_BASE + '/streams?channel={0}'
TWITCH_CHANNELS         = TWITCH_API_BASE + '/channels/{0}'
TWITCH_CHANNELS_VODS    = TWITCH_API_BASE + '/channels/{0}/videos'
TWITCH_TEAMS            = TWITCH_API_BASE + '/teams'
TWITCH_TEAMS            = TWITCH_API_BASE + '/teams'

PAGE_LIMIT = 20
NAME = 'TwitchMod'
PATH = '/video/twitchmod'

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
# Shared Functions
####################################################################################################
def ErrorMessage(error, message):

        return ObjectContainer(
                header  = u'%s' % error,
                message = u'%s' % message, 
        )

# get the streamObjects for the given list of channel names
# returns a dict, key is stream name, value is the 'stream object' json string
def GetStreamObjects(channels, cacheTime=0):

        streamObjects = {}

        try:
                url     = TWITCH_STREAMS_CHANNELS.format(','.join(channels))
                streams = JSON.ObjectFromURL(url, cacheTime=cacheTime)
        except:
                return streamObjects

        for stream in streams['streams']:
                streamObjects[stream['channel']['name']] = stream

        return streamObjects

# given a streamObject (dict), return a DirectoryObject
def DirectoryObjectFromStreamObject(streamObject):

        name         = streamObject['channel']['name']
        display_name = streamObject['channel']['display_name']
        status       = streamObject['channel']['status'] if 'status' in streamObject['channel'] else ''
        logo_img     = streamObject['channel']['logo']
        preview_img  = streamObject['preview']['medium']

        viewers       = "{:,}".format(int(streamObject['viewers']))
        viewersString = "{0} {1}".format(viewers, L('viewers'))

        metadata = {}
        metadata['name']         = name
        metadata['display_name'] = display_name
        metadata['title']        = "{0} - {1} - {2}".format(display_name, viewersString, status)
        metadata['summary']      = "{0}\n\n{1}".format(viewersString, status)
        metadata['logo']         = logo_img
        metadata['preview']      = preview_img

        return DirectoryObject(
                        key     = Callback(ChannelMenu, channelName=metadata['name'], streamObject=streamObject),
                        title   = u'%s' % metadata['title'],
                        summary = u'%s' % metadata['summary'],
                        thumb   = Resource.ContentsOfURLWithFallback(metadata['logo'])
        )              
     
####################################################################################################
def Start():

        ObjectContainer.title1 = NAME

        HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.117 Safari/537.36'
        HTTP.Headers['Accept']     = TWITCH_API_MIME_TYPE
        HTTP.CacheTime = 300

        if not 'usernames' in Dict:
                Dict['usernames'] = []
                Dict.Save()

####################################################################################################
@handler(PATH, NAME)
def MainMenu():

        oc = ObjectContainer(no_cache=True, replace_parent=False)

        oc.add(DirectoryObject(
                key   = Callback(FeaturedStreamsList),
                title = u'%s' % L('featured_streams'),
                thumb = ICONS['channels'],
        ))

        oc.add(DirectoryObject(
                key     = Callback(TopGamesList),
                title   = u'%s' % L('games'),
                summary = u'%s' % L('browse_summary'),
                thumb   = ICONS['games'],
        ))

        oc.add(InputDirectoryObject(
                key     = Callback(SearchResults),
                title   = u'%s' % L('search'),
                prompt  = u'%s' % L('search_prompt'),
                summary = u'%s' % L('search_prompt'),
                thumb   = ICONS['search'],
        ))

        # Usernames
        for username in Dict['usernames']:
                oc.add(DirectoryObject(
                        key   = Callback(FollowedStreamsList, query=username),
                        title = u'%s\'s %s' % (username, L('followed_streams')),
                        thumb = ICONS['following'],
                ))
        # add
        oc.add(InputDirectoryObject(
                key   = Callback(FollowedStreamsList),
                title = u'%s' % L('add_username'),
                thumb = ICONS['settings'],
        ))
        # remove
        if Dict['usernames']:
                oc.add(DirectoryObject(
                        key   = Callback(ListUsernames),
                        title = u'%s' % L('remove_username'),
                        thumb = ICONS['settings'],
                ))                

        if Client.Platform == "Plex Home Theater":
                oc.add(PrefsObject(
                        title   = u'%s' % L('Preferences'),
                        tagline = u'%s' % L('Preferences'),
                        summary = u'%s' % L('Preferences'),
                        thumb   = ICONS['settings'],
                ))

        return oc

####################################################################################################
# Username management
####################################################################################################
def AddUsername(username):

        Dict['usernames'].append(username)
        Dict.Save()

@route(PATH + '/usernames/list', replace_parent=bool)
def ListUsernames(replace_parent=False):

        oc = ObjectContainer(no_cache=True, no_history=True, replace_parent=replace_parent)

        usernames = Dict['usernames']

        for username in usernames:
                oc.add(DirectoryObject(
                        key   = Callback(RemoveUsername, username=username),
                        title = u'%s: %s' % (L('remove'), username)
                ))

        return oc

@route(PATH + '/usernames/remove')
def RemoveUsername(username):

        usernames = Dict['usernames']

        if username in usernames:
                usernames.remove(username)
                Dict['usernames'] = usernames
                Dict.Save()

        return ListUsernames(replace_parent=True)

####################################################################################################
# a request is only made if refresh is True, otherwise assume that the passed streamObject is valid
@route(PATH + '/channel/{channelName}/menu', streamObject=dict)
def ChannelMenu(channelName, streamObject=None):
        
        oc = ObjectContainer(title2=u'%s' % channelName)

        # get a stream object if needed
        if not streamObject:
                url = TWITCH_STREAMS_CHANNEL.format(channelName)
                streamObject = JSON.ObjectFromURL(url, cacheTime=0)['stream']

        # Watch Live (streamObject is only true when a channel is Live)
        if streamObject:
                # viewer count with commas
                viewers = "{:,}".format(int(streamObject['viewers']))
                viewersString = "{0} {1}".format(viewers, L('viewers')) 

                # channel status sometimes gave a key error
                status  = streamObject['channel']['status'] if 'status' in streamObject['channel'] else ''
                title   = "{0} - {1} - {2}".format(L('watch_stream'), viewersString, status)
                summary = '{0}\n{1}'.format(viewersString, status)

                oc.add(VideoClipObject(
                        url     = "1" + streamObject['channel']['url'],
                        title   = u'%s' % title,
                        summary = u'%s' % summary,
                        thumb   = Resource.ContentsOfURLWithFallback(streamObject['preview']['medium'])
                ))

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
def FollowedStreamsList(query, apiurl=None, limit=PAGE_LIMIT):

        if not query in Dict['usernames']:
                AddUsername(username=query)

        oc = ObjectContainer(title2=L('followed_streams'))

        if not query:
               return oc

        # twitch apis provide the 'next' urls for paging, so we only need to construct ours once
        if not apiurl:
                params = "?limit={0}".format(limit)
                apiurl = TWITCH_FOLLOWED_STREAMS.format(query) + params

        # get a list of follows objects
        try:
                following = JSON.ObjectFromURL(apiurl, cacheTime=0)
        except:
                return ErrorMessage(L('followed_streams'), L('followed_streams_list_error'))

        # gather all the channel names that the user is following
        followed_channels = []
        for channel in following['follows']:
                followed_channels.append(channel['channel']['name'])

        # get a list of stream objects for followed streams so we can add Live status to the title
        # an offline stream wont return a stream object
        streamObjects = GetStreamObjects(followed_channels)

        # listing all the followed channels, both live and offline
        for channel in following['follows']:
                channel_display_name = channel['channel']['display_name']
                channel_name         = channel['channel']['name']
                channel_logo         = channel['channel']['logo']

                if channel_name in streamObjects:
                        # live, has a stream object
                        oc.add(DirectoryObjectFromStreamObject(streamObjects[channel_name]))
                else:
                        # not live, doesnt have a streamobject, use channel info
                        title = "{0} - {1}".format(channel_display_name, L('offline'))
                        oc.add(DirectoryObject(
                                key   = Callback(ChannelMenu, channelName=channel_name),
                                title = u'%s' % title,
                                thumb = Resource.ContentsOfURLWithFallback(channel_logo)
                        ))

        if len(oc) >= limit:
                oc.add(NextPageObject(
                        key   = Callback(FollowedStreamsList, query=query, apiurl=following['_links']['next'], limit=limit),
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

        for video in videos['videos']:
                url      = video['url']
                vod_type = url.split('/')[-2]
                
                if vod_type == "v":
                        vod_date    = Datetime.ParseDate(video['recorded_at'])
                        title       = "{0} - {1}".format(vod_date.strftime('%a %b %d, %Y'), video['title'])
                        description = video['description']
                        length      = int(video['length']) * 1000
                        
                        oc.add(VideoClipObject(
                                url      = "1" + url,
                                title    = u'%s' % title,
                                summary  = u'%s' % description,
                                duration = length,
                                thumb    = Resource.ContentsOfURLWithFallback(video['preview']),
                        ))

        if len(oc) >= limit:
                oc.add(NextPageObject(
                        key   = Callback(ChannelVodsList, apiurl=videos['_links']['next'], broadcasts=broadcasts, limit=limit),
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
                        thumb   = Resource.ContentsOfURLWithFallback(thumb),
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
                oc.add(DirectoryObjectFromStreamObject(streamObject))            

        if len(oc) >= limit:
                oc.add(NextPageObject(
                        key   = Callback(ChannelsForGameList, game=game, apiurl=streams['_links']['next'], limit=limit),
                        title = u'%s' % L('more'),
                        thumb = ICONS['more'],
                ))

        return oc

####################################################################################################
@route(PATH + '/search', limit=int)
def SearchResults(query='', apiurl=None, limit=PAGE_LIMIT):

        oc = ObjectContainer(title2=L('search'), no_cache=True)

        if not apiurl:
                params = "?query={0}&limit={1}".format(String.Quote(query, usePlus=True), limit)
                apiurl = TWITCH_SEARCH_STREAMS + params

        results = JSON.ObjectFromURL(apiurl)

        for streamObject in results['streams']:
                oc.add(DirectoryObjectFromStreamObject(streamObject))

        if len(oc) < 1:
                return ErrorMessage(L('search'), L('search_error'))

        if len(oc) >= limit:
                oc.add(NextPageObject(
                        key   = Callback(SearchResults, query=query, apiurl=results['_links']['next'], limit=limit),
                        title = u'%s' % L('more'),
                        thumb = ICONS['more'],
                ))                

        return oc
