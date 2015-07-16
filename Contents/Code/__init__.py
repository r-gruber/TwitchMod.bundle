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
TWITCH_LIST_STREAMS     = TWITCH_API_BASE + '/streams'
TWITCH_SEARCH_STREAMS   = TWITCH_API_BASE + '/search/streams'
TWITCH_FOLLOWED_STREAMS = TWITCH_API_BASE + '/users/{0}/follows/channels'
TWITCH_CHANNEL          = TWITCH_API_BASE + '/channels/{0}'
TWITCH_CHANNEL_VODS     = TWITCH_API_BASE + '/channels/{0}/videos'
TWITCH_VOD              = TWITCH_API_BASE + '/videos/{0}'

PAGE_LIMIT = 100
NAME = 'Twitch'

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
                key   = Callback(FeaturedStreamsMenu),
                title = L('featured_streams')
                )
        )
	oc.add(DirectoryObject(
                key     = Callback(ListGames),
                title   = L('games'),
                summary = L('browse_summary')
                )
        )
	oc.add(InputDirectoryObject(
                key     = Callback(SearchResults),
                title   = L('search'),
                prompt  = L('search_prompt'),
                summary = L('search_prompt')
                )
        )
        oc.add(DirectoryObject(
                key   = Callback(FollowedStreamsMenu),
                title = L('followed_streams')
                )
        )
        oc.add(PrefsObject(
                title   = L('Preferences'),
                tagline = L('Preferences'),
                summary = L('Preferences'),
                )
        )

	return oc

@route('/video/twitch/following')
def FollowedStreamsMenu():

        oc = ObjectContainer(title2=L('followed_streams'))

        username = Prefs['username']
        if not username:
                return oc

        url = TWITCH_FOLLOWED_STREAMS.format(username)

        following = JSON.ObjectFromURL(url)

        for channel in following['follows']:
                channel_name = channel['channel']['name']
                oc.add(DirectoryObject(
                        key   = Callback(ChannelMenu, channel=channel_name),
                        title = channel['channel']['display_name'],
                        thumb = Resource.ContentsOfURLWithFallback(channel['channel']['video_banner'])
                        )
                )
        return oc

@route('video/twitch/channel/menu')
def ChannelMenu(channel):
        oc = ObjectContainer(title2=channel)

        url = TWITCH_CHANNEL.format(channel)

        channelObject = JSON.ObjectFromURL(url)

        oc.add(VideoClipObject(
                url     = channelObject['url'],
                title   = channelObject['display_name'],
                summary = channelObject['status'],
                thumb   = Resource.ContentsOfURLWithFallback(channelObject['video_banner'])
                )
        )

        oc.add(DirectoryObject(
                key   = Callback(ChannelVodsList, channel=channel, limit=5),
                title = L('past_broadcasts'),
                )
        )

        return oc

@route('/video/twitch/channel/vods')
def ChannelVodsList(channel=None, apiurl=None, limit=20):
        oc = ObjectContainer(title2=L('past_broadcasts'))

        if apiurl:
                url = apiurl
        else:
                limitstr = "?limit={0}&offset={1}".format(limit, 0)
                url = TWITCH_CHANNEL_VODS.format(channel) + limitstr

        videos = JSON.ObjectFromURL(url)

        for video in videos['videos']:
                oc.add(VideoClipObject(
                        url     = video['url'],
                        title   = video['title'],
                        thumb   = Resource.ContentsOfURLWithFallback(video['preview']),
                        summary = video['description']
                        )
                )

        if videos['_links']['next']:
                oc.add(NextPageObject(
                        key   = Callback(ChannelVodsList, apiurl=videos['_links']['next'], limit=limit),
                        title = L('more')
                        )
                )
        return oc

####################################################################################################
@route('/video/twitch/featured')
def FeaturedStreamsMenu():

	oc = ObjectContainer(title2=L('featured_streams'), no_cache=True)
	url = "%s?limit=%s" % (TWITCH_FEATURED_STREAMS, PAGE_LIMIT)
	featured = JSON.ObjectFromURL(url)

	for stream in featured['featured']:
		summary = String.StripTags(stream['text'])

		if stream['stream']['game']:
			subtitle = "%s\n%s Viewers" % (stream['stream']['game'], stream['stream']['viewers'])
		else:
			subtitle = "%s Viewers" % (stream['stream']['viewers'])

		oc.add(VideoClipObject(
			url = stream['stream']['channel']['url'],
			title = stream['stream']['channel']['display_name'],
			summary = '%s\n\n%s' % (subtitle, summary),
			thumb = Resource.ContentsOfURLWithFallback(stream['stream']['preview']['large'])
		      )
                )

	return oc

####################################################################################################
@route('/video/twitch/games')
def ListGames(apiurl=None, limit=20):

	oc = ObjectContainer(title2=L('top_games'), no_cache=True)

        url = apiurl if apiurl else "{0}?limit={1}".format(TWITCH_TOP_GAMES, limit)


	games = JSON.ObjectFromURL(url)

	for game in games['top']:
                game_summary = "{0} {1}\n{2} {3}".format(game['channels'], L('channels'), game['viewers'], L('viewers'))
                thumb = game['game']['box']['medium']

		oc.add(DirectoryObject(
			key     = Callback(ListChannelsForGame, game=game['game']['name']),
			title   = game['game']['name'],
			summary = game_summary,
			thumb   = Resource.ContentsOfURLWithFallback(thumb)
		))

        if games['_links']['next']:
                oc.add(NextPageObject(
                        key   = Callback(ListGames, apiurl=games['_links']['next']),
                        title = L('more')
                ))

	return oc

####################################################################################################
@route('/video/twitch/channel')
def ListChannelsForGame(game, apiurl=None, limit=20):

	oc = ObjectContainer(title2=game, no_cache=True)
	url = apiurl if apiurl else "{0}?game={1}&limit={2}".format(TWITCH_LIST_STREAMS, String.Quote(game, usePlus=True), limit)

	streams = JSON.ObjectFromURL(url)

	for stream in streams['streams']:
                subtitle = " {0} {1}".format(stream['viewers'], L('viewers'))
		oc.add(VideoClipObject(
			url     = stream['channel']['url'],
			title   = stream['channel']['display_name'],
			summary = '%s\n\n%s' % (subtitle, stream['channel']['status']),
			thumb   = Resource.ContentsOfURLWithFallback(stream['channel']['logo'])
		      )
                )
        if streams['_links']['next']:
                oc.add(NextPageObject(
                        key   = Callback(ListChannelsForGame, game=game, apiurl=streams['_links']['next']),
                        title = L('more')
                ))

	return oc

####################################################################################################
def SearchResults(query=''):

	oc = ObjectContainer(no_cache=True)
	results = JSON.ObjectFromURL("%s?query=%s&limit=%s" % (TWITCH_SEARCH_STREAMS, String.Quote(query, usePlus=True), PAGE_LIMIT))

	for stream in results['streams']:
		if stream['game']:
                        subtitle = "{0}\n{1} {2}".format(stream['game'], stream['viewers'], L('viewers'))
		else:
                        subtitle = "{0} {1}".format(stream['viewers'], L('viewers'))

		oc.add(VideoClipObject(
			url     = stream['channel']['url'],
			title   = stream['channel']['display_name'],
			summary = '%s\n\n%s' % (subtitle, stream['channel']['status']),
			thumb   = Resource.ContentsOfURLWithFallback(stream['channel']['logo'])
		))

	if len(oc) < 1:
		return ObjectContainer(header="Not found", message="No streams were found that match your query.")

	return oc
