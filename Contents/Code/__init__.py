# Twitch.tv Plugin
# v0.1 by Marshall Thornton <marshallthornton@gmail.com>
# Code inspired by Justin.tv plugin by Trevor Cortez and John Roberts
# v0.2 by Nicolas Aravena <mhobbit@gmail.com>
# Adaptation of v0.1 for new Plex Media Server.

####################################################################################################

TWITCH_FEATURED_STREAMS = 'https://api.twitch.tv/kraken/streams/featured'
TWITCH_TOP_GAMES = 'https://api.twitch.tv/kraken/games/top'
TWITCH_LIST_STREAMS = 'https://api.twitch.tv/kraken/streams'
TWITCH_SEARCH_STREAMS = 'https://api.twitch.tv/kraken/search/streams'

PAGE_LIMIT = 100
NAME = 'Twitch.tv'
ART = 'art-default.jpg'
ICON = 'icon-default.jpg'

####################################################################################################
def Start():

	ObjectContainer.art = R(ART)
	ObjectContainer.title1 = NAME
	DirectoryObject.thumb = R(ICON)

	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:19.0) Gecko/20100101 Firefox/19.0'
	HTTP.CacheTime = 600

####################################################################################################
@handler('/video/twitch', NAME, thumb=ICON, art=ART)
def MainMenu():

	oc = ObjectContainer()
	oc.add(DirectoryObject(key=Callback(FeaturedStreamsMenu), title="Featured Streams"))
	oc.add(DirectoryObject(key=Callback(GamesMenu), title="Games", summary="Browse Live Streams by Game"))
	oc.add(InputDirectoryObject(key=Callback(SearchResults), title="Search", prompt="Search for a Stream", summary="Search for a Stream", thumb=R('search.png')))

	return oc

####################################################################################################
@route('/video/twitch/featured')
def FeaturedStreamsMenu():

	oc = ObjectContainer(title2="Featured Streams")
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
			thumb = Resource.ContentsOfURLWithFallback(stream['stream']['preview']['large'], fallback='icon-default.jpg')
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
			thumb = Resource.ContentsOfURLWithFallback(game['game']['logo']['large'], fallback='icon-default.jpg')
		))

	if len(games['top']) == 100:
		oc.add(NextPageObject(
			key = Callback(GamesMenu, page=page+1),
			title = "More Games"
		))

	return oc

####################################################################################################
@route('/video/twitch/channel')
def ChannelMenu(game):

	oc = ObjectContainer(title2=game)
	url = "%s?game=%s&limit=%s" % (TWITCH_LIST_STREAMS, String.Quote(game, usePlus=True), PAGE_LIMIT)
	streams = JSON.ObjectFromURL(url)

	for stream in streams['streams']:
		subtitle = " %s Viewers" % stream['viewers']

		oc.add(VideoClipObject(
			url = stream['channel']['url'],
			title = stream['channel']['display_name'],
			summary = '%s\n\n%s' % (subtitle, stream['channel']['status']),
			thumb = Resource.ContentsOfURLWithFallback(stream['channel']['logo'], fallback='icon-default.jpg')
		))

	return oc

####################################################################################################
def SearchResults(query=''):

	oc = ObjectContainer()
	results = JSON.ObjectFromURL("%s?query=%s&limit=%s" % (TWITCH_SEARCH_STREAMS, String.Quote(query, usePlus=True), PAGE_LIMIT))

	for stream in results['streams']:
		if stream['game']:
			subtitle = "%s\n%s Viewers" % (stream['game'], stream['viewers'])
		else:
			subtitle = "%s Viewers" % (stream['viewers'])

		oc.add(VideoClipObject(
			url = stream['channel']['url'],
			title = stream['channel']['display_name'],
			summary = '%s\n\n%s' % (subtitle, stream['channel']['status']),
			thumb = Resource.ContentsOfURLWithFallback(stream['channel']['logo'], fallback='icon-default.jpg')
		))

	if len(oc) < 1:
		return ObjectContainer(header="Not found", message="No streams were found that match your query.")

	return oc
