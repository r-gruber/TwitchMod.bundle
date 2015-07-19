#-*- encoding: utf-8 -*-
# Twitch.tv Plugin
# v0.1 by Marshall Thornton <marshallthornton@gmail.com>
# Code inspired by Justin.tv plugin by Trevor Cortez and John Roberts
# v0.2 by Nicolas Aravena <mhobbit@gmail.com>
# Adaptation of v0.1 for new Plex Media Server.

# v0.3 by Cory <babylonstudio@gmail.com>
# added followed streams, vod support, quality options

####################################################################################################
TWITCH_API_BASE = 'https://api.twitch.tv/kraken'
TWITCH_FEATURED_STREAMS = TWITCH_API_BASE + '/streams/featured'
TWITCH_TOP_GAMES        = TWITCH_API_BASE + '/games/top'
TWITCH_SEARCH_STREAMS   = TWITCH_API_BASE + '/search/streams'
TWITCH_FOLLOWED_STREAMS = TWITCH_API_BASE + '/users/{0}/follows/channels'
TWITCH_STREAMS          = TWITCH_API_BASE + '/streams'
TWITCH_STREAMS_CHANNEL  = TWITCH_API_BASE + '/streams/{0}'
TWITCH_STREAMS_CHANNELS = TWITCH_API_BASE + '/streams?channel={0}'
TWITCH_CHANNELS         = TWITCH_API_BASE + '/channels/{0}'
TWITCH_CHANNELS_VODS    = TWITCH_API_BASE + '/channels/{0}/videos'

STREAM_OBJECT_CACHE_TIME    = 0
FOLLOWED_STREAMS_CACHE_TIME = 5

PAGE_LIMIT = 20
NAME = 'Twitch'

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
def GetStreamObjects(channels, cacheTime=STREAM_OBJECT_CACHE_TIME):

        streamObjects = {}

        try:
                url     = TWITCH_STREAMS_CHANNELS.format(','.join(channels))
                streams = JSON.ObjectFromURL(url, cacheTime=cacheTime)
        except:
                return streamObjects

        for stream in streams['streams']:
                streamObjects[stream['channel']['name']] = JSON.StringFromObject(stream)

        return streamObjects

# given a streamObject, return a DirectoryObject
def DirectoryObjectFromStreamObject(streamObjectJSONString):

        streamObject = JSON.ObjectFromString(streamObjectJSONString)
        name         = streamObject['channel']['name']
        display_name = streamObject['channel']['display_name']
        status       = streamObject['channel']['status'] if 'status' in streamObject['channel'] else ''
        logo_img     = streamObject['channel']['logo']
        preview_img  = streamObject['preview']['medium']

        viewers       = "{:,}".format(int(streamObject['viewers']))
        viewersString = " {0} {1}".format(viewers, L('viewers'))

        metadata = {}
        metadata['name']         = name
        metadata['display_name'] = display_name
        metadata['title']        = "{0} - {1} - {2}".format(display_name, viewersString, status)
        metadata['summary']      = "{0}\n\n{1}".format(viewersString, status)
        metadata['logo']         = logo_img
        metadata['preview']      = preview_img

        return DirectoryObject(
                        key     = Callback(ChannelMenu, channelName=metadata['name'], streamObject=streamObjectJSONString),
                        title   = u'%s' % metadata['title'],
                        summary = u'%s' % metadata['summary'],
                        thumb   = Resource.ContentsOfURLWithFallback(metadata['logo'])
        )              
     
####################################################################################################
def Start():

	ObjectContainer.title1 = NAME
	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.117 Safari/537.36'
	HTTP.CacheTime = 300

####################################################################################################
@handler('/video/twitch', NAME)
def MainMenu():

	oc = ObjectContainer()

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

        oc.add(DirectoryObject(
                key   = Callback(FollowedStreamsList),
                title = u'%s' % L('followed_streams'),
                thumb = ICONS['following'],
        ))

        oc.add(PrefsObject(
                title   = u'%s' % L('Preferences'),
                tagline = u'%s' % L('Preferences'),
                summary = u'%s' % L('Preferences'),
                thumb   = ICONS['settings'],
        ))

	return oc

####################################################################################################
# a request is only made if refresh is True, otherwise assume that the passed streamObject is valid
@route('video/twitch/channel/menu')
def ChannelMenu(channelName, refresh=False, streamObject=None):
        
        oc = ObjectContainer(title2=channelName)

        # get a stream object if needed
        if refresh:
                url = TWITCH_STREAMS_CHANNEL.format(channelName)
                streamObject = JSON.ObjectFromURL(url, cacheTime=0)['stream']
        else:
                streamObject = JSON.ObjectFromString(streamObject) if streamObject else None

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
                        url     = streamObject['channel']['url'],
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
@route('/video/twitch/following')
def FollowedStreamsList(apiurl=None, limit=PAGE_LIMIT, username=None):

        oc = ObjectContainer(title2=L('followed_streams'))

        if not username:
                username = Prefs['username']
                if not username:
                        return oc

        # twitch apis provide the 'next' urls for paging, so we only need to construct ours once
        if not apiurl:
                limitstr = "?limit={0}".format(limit)
                apiurl   = TWITCH_FOLLOWED_STREAMS.format(username) + limitstr

        # get a list of follows objects
        try:
                following = JSON.ObjectFromURL(apiurl, cacheTime=FOLLOWED_STREAMS_CACHE_TIME)
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

        if following['_total'] >= limit:
                oc.add(NextPageObject(
                        key   = Callback(FollowedStreamsList, apiurl=following['_links']['next'], limit=limit),
                        title = u'%s' % L('more'),
                        thumb = ICONS['more'],
                ))

        return oc

####################################################################################################
@route('/video/twitch/channel/vods')
def ChannelVodsList(channel=None, apiurl=None, broadcasts=True, limit=PAGE_LIMIT):
     
        oc = ObjectContainer(title2=L('past_broadcasts') if broadcasts else L('highlights'))
        
        if not apiurl:
                limitstr = "?limit={0}&broadcasts={1}".format(limit, str(broadcasts).lower())
                apiurl = TWITCH_CHANNELS_VODS.format(channel) + limitstr

        videos = JSON.ObjectFromURL(apiurl)

        for video in videos['videos']:
                vod_date = Datetime.ParseDate(video['recorded_at'])
                title    = "{0} - {1}".format(vod_date.strftime('%a %b %d, %Y'), video['title'])

                oc.add(VideoClipObject(
                        url      = video['url'],
                        title    = u'%s' % title,
                        summary  = u'%s' % video['description'],
                        duration = int(video['length'])*1000,
                        thumb    = Resource.ContentsOfURLWithFallback(video['preview']),
                ))

        if videos['_total'] >= limit:
                oc.add(NextPageObject(
                        key   = Callback(ChannelVodsList, apiurl=videos['_links']['next'], broadcasts=broadcasts, limit=limit),
                        title = u'%s' % L('more'),
                        thumb = ICONS['more'],
                ))

        return oc

####################################################################################################
@route('/video/twitch/featured')
def FeaturedStreamsList(apiurl=None, limit=PAGE_LIMIT):

	oc = ObjectContainer(title2=L('featured_streams'), no_cache=True)

        if not apiurl:
	       apiurl = "%s?limit=%s" % (TWITCH_FEATURED_STREAMS, limit)
	featured = JSON.ObjectFromURL(apiurl)

	for stream in featured['featured']:
                streamObject = JSON.StringFromObject(stream['stream'])
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
@route('/video/twitch/games')
def TopGamesList(apiurl=None, limit=PAGE_LIMIT):

	oc = ObjectContainer(title2=L('top_games'), no_cache=True)

        url = apiurl if apiurl else "{0}?limit={1}".format(TWITCH_TOP_GAMES, limit)

	games = JSON.ObjectFromURL(url)

	for game in games['top']:
                game_name    = game['game']['name']
                game_summary = "{0} {1}\n{2} {3}".format(game['channels'], L('channels'), game['viewers'], L('viewers'))
                # image options are [box][large,medium,small] or [logo][large,medium,small]
                thumb        = game['game']['box']['medium']

		oc.add(DirectoryObject(
			key     = Callback(ChannelsForGameList, game=game_name),
			title   = u'%s' % game_name,
			summary = u'%s' % game_summary,
			thumb   = Resource.ContentsOfURLWithFallback(thumb),
		))

        if games['_total'] >= limit:
                oc.add(NextPageObject(
                        key   = Callback(TopGamesList, apiurl=games['_links']['next']),
                        title = u'%s' % L('more'),
                        thumb = ICONS['more'],
                ))

	return oc

####################################################################################################
@route('/video/twitch/channel')
def ChannelsForGameList(game, apiurl=None, limit=PAGE_LIMIT):

	oc = ObjectContainer(title2=game, no_cache=True)
	        
        if not apiurl:
                apiurl = "{0}?game={1}&limit={2}".format(TWITCH_STREAMS, String.Quote(game, usePlus=True), limit)

	streams = JSON.ObjectFromURL(apiurl)

	for stream in streams['streams']:
                streamObject = JSON.StringFromObject(stream)
                oc.add(DirectoryObjectFromStreamObject(streamObject))            

        if streams['_total'] >= limit:
                oc.add(NextPageObject(
                        key   = Callback(ChannelsForGameList, game=game, apiurl=streams['_links']['next'], limit=limit),
                        title = u'%s' % L('more'),
                        thumb = ICONS['more'],
                ))

	return oc

####################################################################################################
@route('/video/twitch/search')
def SearchResults(query='', limit=PAGE_LIMIT):

	oc = ObjectContainer(title2=L('search'), no_cache=True)
	results = JSON.ObjectFromURL("%s?query=%s&limit=%s" % (TWITCH_SEARCH_STREAMS, String.Quote(query, usePlus=True), limit))

	for stream in results['streams']:
                streamObject = JSON.StringFromObject(stream)
                oc.add(DirectoryObjectFromStreamObject(streamObject))

	if len(oc) < 1:
                return ErrorMessage(L('search'), L('search_error'))

	return oc
