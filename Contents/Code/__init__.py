# Twitch.tv Plugin
# v0.1 by Marshall Thornton <marshallthornton@gmail.com>
# Code inspired by Justin.tv plugin by Trevor Cortez and John Roberts
# v0.2 by Nicolas Aravena <mhobbit@gmail.com>
# Adaptation of v0.1 for new Plex Media Server.

####################################################################################################

TWITCH_LIST_STREAMS = 'https://api.twitch.tv/kraken/streams'
TWITCH_FEATURED_STREAMS = 'https://api.twitch.tv/kraken/streams/featured'
TWITCH_TOP_GAMES = 'https://api.twitch.tv/kraken/games/top'
TWITCH_SEARCH_STREAMS = 'https://api.twitch.tv/kraken/search/streams'
TWITCH_LIVE_PLAYER = 'http://www-cdn.jtvnw.net/widgets/live_embed_player.swf?auto_play=true'

PAGE_LIMIT = 100
NAME = 'Twitch.tv'
ART = 'art-default.jpg'
ICON = 'icon-default.png'

####################################################################################################
def Start():

	ObjectContainer.art = R(ART)
	ObjectContainer.title1 = NAME
	DirectoryItem.thumb = R(ICON)

	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:19.0) Gecko/20100101 Firefox/19.0'
	HTTP.CacheTime = 600

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
	url = "%s?limit=%s" % (TWITCH_FEATURED_STREAMS, PAGE_LIMIT)
	featured = JSON.ObjectFromURL(url)

	for stream in featured['featured']:
		subtitle = "%s\n%s Viewers" % (stream['stream']['game'], stream['stream']['viewers'])
		summary = String.StripTags(stream['text'])
		stream_url = "%s&channel=%s" % (TWITCH_LIVE_PLAYER, stream['stream']['channel']['name'])

		oc.add(VideoClipObject(
			url = stream_url,
			title = stream['stream']['channel']['display_name'],
			summary = '%s\n\n%s' % (subtitle, summary),
			thumb = stream['stream']['preview']
		))

	return oc

####################################################################################################
@route('/video/twitch/games', page=int)
def GamesMenu(page=0):

	oc = ObjectContainer(title2="Top Games")
	url = "%s?limit=%s&offset=%s" % (TWITCH_TOP_GAMES, PAGE_LIMIT, page*PAGE_LIMIT)
	games = JSON.ObjectFromURL(url)

	for game in games['top']:
		game_summary = "%s Channels\n%s Viewers" % (game['channels'], game['viewers'])

		oc.add(DirectoryObject(
			key = Callback(ChannelMenu, game=game['game']['name']),
			title = game['game']['name'],
			summary = game_summary,
			thumb = game['game']['logo']['large']
		))

	if len(games['top']) == 100:
		oc.add(DirectoryObject(key=Callback(GamesMenu, title="More Games", page=page+1)))

	return oc

####################################################################################################
@route('/video/twitch/channel')
def ChannelMenu(game):

	oc = ObjectContainer(title2=game)
	url = "%s?game=%s&limit=%s" % (TWITCH_LIST_STREAMS, String.Quote(game, usePlus=True), PAGE_LIMIT)
	streams = JSON.ObjectFromURL(url)

	for stream in streams['streams']:
		subtitle = " %s Viewers" % stream['viewers']
		stream_url = "%s&channel=%s" % (TWITCH_LIVE_PLAYER, stream['channel']['name'])

		oc.add(VideoClipObject(
			url = stream_url,
			title = stream['channel']['display_name'],
			summary = '%s\n\n%s' % (subtitle, stream['channel']['status']),
			thumb = stream['channel']['logo']
		))

	return oc

####################################################################################################
def SearchResults(query=''):

	oc = ObjectContainer()
	results = JSON.ObjectFromURL("%s?query=%s&limit=%s" % (TWITCH_SEARCH_STREAMS, String.Quote(query, usePlus=True), PAGE_LIMIT))

	for stream in results['streams']:
		stream_url = "%s&channel=%s" % (TWITCH_LIVE_PLAYER, stream['channel']['name'])
		subtitle = "%s\n%s Viewers" % (stream['game'], stream['viewers'])

		oc.add(VideoClipObject(
			url = stream_url,
			title = stream['channel']['display_name'],
			summary = '%s\n\n%s' % (subtitle, stream['channel']['status']),
			thumb = stream['channel']['logo']
		))

	if len(oc) < 1:
		return ObjectContainer(header="Not found", message="No streams were found that match your query.")

	return oc
