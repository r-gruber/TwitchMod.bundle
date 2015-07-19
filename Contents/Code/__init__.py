#-*- encoding: utf-8 -*-

# Twitch.tv Plugin
# v0.1 by Marshall Thornton <marshallthornton@gmail.com>
# Code inspired by Justin.tv plugin by Trevor Cortez and John Roberts
# v0.2 by Nicolas Aravena <mhobbit@gmail.com>
# Adaptation of v0.1 for new Plex Media Server.

# v0.3 by Cory <babylonstudio@gmail.com>
# added followed streams

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

# get the streamObjects for the given list of channel names
# returns a dict, key is stream name, value is the 'stream object' json string
def GetStreamObjects(channels):
        streamObjects = {}
        for channel in channels:
                streamObjects[channel] = JSON.StringFromObject({})

        url     = TWITCH_STREAMS_CHANNELS.format(','.join(channels))
        streams = JSON.ObjectFromURL(url, cacheTime=FOLLOWED_STREAMS_CACHE_TIME)

        for stream in streams['streams']:
                streamObjects[stream['channel']['name']] = JSON.StringFromObject(stream)

        return streamObjects

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
                title = L('featured_streams'),
                thumb = ICONS['channels'],
        ))

	oc.add(DirectoryObject(
                key     = Callback(TopGamesList),
                title   = L('games'),
                summary = L('browse_summary'),
                thumb   = ICONS['games'],
        ))

	oc.add(InputDirectoryObject(
                key     = Callback(SearchResults),
                title   = L('search'),
                prompt  = L('search_prompt'),
                summary = L('search_prompt'),
                thumb   = ICONS['search'],
        ))

        oc.add(DirectoryObject(
                key   = Callback(FollowedStreamsList),
                title = L('followed_streams'),
                thumb = ICONS['following'],
        ))

        oc.add(PrefsObject(
                title   = L('Preferences'),
                tagline = L('Preferences'),
                summary = L('Preferences'),
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
                streamObject = JSON.ObjectFromString(streamObject)

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
                        title   = title,
                        summary = summary,
                        thumb   = Resource.ContentsOfURLWithFallback(streamObject['preview']['medium'])
                ))

        # List Highlights
        oc.add(DirectoryObject(
                key   = Callback(ChannelVodsList, channel=channelName, broadcasts=False),
                title = L('highlights'),
                thumb = ICONS['videos'],
        ))

        # List Past Broadcasts
        oc.add(DirectoryObject(
                key   = Callback(ChannelVodsList, channel=channelName, broadcasts=True),
                title = L('past_broadcasts'),
                thumb = ICONS['videos'],
        ))

        return oc

####################################################################################################
# Two requests are made in this route
# 1. get a list of 'follow' objects, which contains the information for the channels
# 2. get a list of 'stream' objects, which contains info about the stream if its live
@route('/video/twitch/following')
def FollowedStreamsList(apiurl=None, limit=PAGE_LIMIT):

        oc = ObjectContainer(title2=L('followed_streams'))

        username = Prefs['username']
        if not username:
                return oc

        # twitch apis provide the 'next' urls for paging, so we only need to construct ours once
        if not apiurl:
                limitstr = "?limit={0}".format(limit)
                apiurl   = TWITCH_FOLLOWED_STREAMS.format(username) + limitstr

        # get a list of follows objects
        following = JSON.ObjectFromURL(apiurl, cacheTime=FOLLOWED_STREAMS_CACHE_TIME)

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

                # format the title
                title = "{0} - {1}".format(channel_display_name, L('offline'))

                # see if its live, if so change the title
                streamObject = JSON.ObjectFromString(streamObjects[channel_name])
                if streamObject:
                        viewers       = "{:,}".format(int(streamObject['viewers'])) # add commas to big numbers
                        viewersString = "{0} {1}".format(viewers, L('viewers'))
                        title         = "{0} - {1} {2}".format(channel_display_name, L('live'), viewersString)

                oc.add(DirectoryObject(
                        key   = Callback(ChannelMenu, channelName=channel_name, streamObject=streamObjects[channel_name]),
                        title = title,
                        thumb = Resource.ContentsOfURLWithFallback(channel_logo)
                ))

        if following['_total'] >= limit:
                oc.add(NextPageObject(
                        key   = Callback(FollowedStreamsList, apiurl=following['_links']['next'], limit=limit),
                        title = L('more'),
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
                title = "{0} - {1}".format(vod_date.strftime('%a %b %d, %Y'), video['title'])
                oc.add(VideoClipObject(
                        url     = video['url'],
                        title   = title,
                        thumb   = Resource.ContentsOfURLWithFallback(video['preview']),
                        summary = video['description'],
                        duration = int(video['length'])*1000
                ))

        if videos['_total'] >= limit:
                oc.add(NextPageObject(
                        key   = Callback(ChannelVodsList, apiurl=videos['_links']['next'], broadcasts=broadcasts, limit=limit),
                        title = L('more'),
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
                streamObject         = JSON.StringFromObject(stream['stream'])
                channel_display_name = stream['stream']['channel']['display_name']
                channel_name         = stream['stream']['channel']['name']
                
                viewers       = "{:,}".format(int(stream['stream']['viewers']))
                viewersString = "{0} {1}".format(viewers, L('viewers'))

		summary = String.StripTags(stream['text'])
                status  = stream['stream']['channel']['status'] if 'status' in stream['stream']['channel'] else ''

                title = "%s - %s - %s" % (channel_display_name, viewersString, status)

                oc.add(DirectoryObject(
                        key     = Callback(ChannelMenu, channelName=channel_name, streamObject=streamObject),
                        title   = title,
                        summary = '%s\n\n%s\n\n%s' % (viewersString, status, summary),
                        thumb   = Resource.ContentsOfURLWithFallback(stream['stream']['channel']['logo'])
                ))

        # featured streams doesnt provide a total
        if len(oc) >= limit:
                oc.add(NextPageObject(
                        key   = Callback(FeaturedStreamsList, apiurl=featured['_links']['next']),
                        title = L('more'),
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
			title   = game_name,
			summary = game_summary,
			thumb   = Resource.ContentsOfURLWithFallback(thumb),
		))

        if games['_total'] >= limit:
                oc.add(NextPageObject(
                        key   = Callback(TopGamesList, apiurl=games['_links']['next']),
                        title = L('more'),
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
                streamObject  = JSON.StringFromObject(stream)
                channel_name  = stream['channel']['name']
                channel_display_name = stream['channel']['display_name']

                viewers = "{:,}".format(int(stream['viewers']))
                viewersString = " {0} {1}".format(viewers, L('viewers'))

                status = stream['channel']['status'] if 'status' in stream['channel'] else ''

                # apparently using .format() makes setting the DirectoryObject title not work for unicode
                title = "%s - %s - %s" % (channel_display_name, viewersString, status)

                oc.add(DirectoryObject(
                        key     = Callback(ChannelMenu, channelName=channel_name, streamObject=streamObject),
                        title   = title,
                        summary = '%s\n\n%s' % (viewersString, status),
                        thumb   = Resource.ContentsOfURLWithFallback(stream['channel']['logo'])
                ))              

        if streams['_total'] >= limit:
                oc.add(NextPageObject(
                        key   = Callback(ChannelsForGameList, game=game, apiurl=streams['_links']['next'], limit=limit),
                        title = L('more'),
                        thumb = ICONS['more'],
                ))

	return oc

####################################################################################################
@route('/video/twitch/search')
def SearchResults(query='', limit=PAGE_LIMIT):

	oc = ObjectContainer(no_cache=True)
	results = JSON.ObjectFromURL("%s?query=%s&limit=%s" % (TWITCH_SEARCH_STREAMS, String.Quote(query, usePlus=True), limit))

	for stream in results['streams']:
                streamObject  = JSON.StringFromObject(stream)
                channel_name  = stream['channel']['name']

                viewersString = "{0} {1}".format(stream['viewers'], L('viewers'))
                subtitle = "{0}\n{1}".format(stream['game'], viewersString) if stream['game'] else viewersString

                status = stream['channel']['status'] if 'status' in stream['channel'] else ''

                oc.add(DirectoryObject(
                        key     = Callback(ChannelMenu, channelName=channel_name, streamObject=streamObject),
                        title   = stream['channel']['display_name'],
                        summary = '%s\n\n%s' % (subtitle, status),
                        thumb   = Resource.ContentsOfURLWithFallback(stream['channel']['logo'])
                ))   

	if len(oc) < 1:
		return ObjectContainer(header="Not found", message="No streams were found that match your query.")

	return oc
