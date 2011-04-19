import re, string, os, socket
from PMS import *
from PMS.Objects import *
from PMS.Shortcuts import *

REQUIRED_TAGS = {
	"str":[
		"dmap.itemname",
		"daap.songalbum",
		"daap.songartist",
		"daap.songgenre"
	],
	"int":[
		"daap.songcompilation",
		"daap.songdiscnumber",
		"daap.songsize",
		"daap.songtime",
		"daap.songtracknumber",
		"daap.songyear",
		"daap.songuserrating"
	]}

class ArtistItem(XMLObject):
	def __init__(self, key, artist, thumb=None, **kwargs):
		XMLObject.__init__(self, key=key, artist=artist, thumb=thumb, **kwargs)
		self.tagName = "Artist"

class AlbumItem(XMLObject):
	def __init__(self, key, label, album=None, artist=None, genre=None, year=None, **kwargs):
		XMLObject.__init__(self, key=key, label=label, album=album, artist=artist, genre=genre, year=year, **kwargs)
		self.tagName = "Album"

def Start():
	Plugin.AddPrefixHandler("/music/firefly", ServerMenu, "Firefly Media Server", "icon-default.png")	
	Plugin.AddViewGroup("Songs", mediaType="songs", viewMode="Songs")
	Prefs.Add("pref_host", "text", "0.0.0.0", "Host/IP")
	Prefs.Add("pref_port", "text", "3689", "Port")
	MediaContainer.title1  = "Firefly Media Server"
	MediaContainer.content = "Objects"
					
def ServerMenu():
	global ff_host, ff_port, server_name
	dir = MediaContainer()	
	ff_host = Prefs.Get("pref_host")
	ff_port = int(Prefs.Get("pref_port"))
	if ff_host != "0.0.0.0" and isValidHost(ff_host, ff_port):
		url = "http://%s:%d/server-info?output=xml" % (ff_host, ff_port)
		server_name = XML.ElementFromURL(url, errors="ignore").xpath("//dmap.itemname")[0].text
		dir.Append(Function(DirectoryItem(MainMenu, title=server_name)))
		dir.Append(PrefsItem(title="Preferences"))
	else: dir.Append(PrefsItem(title="Add a server"))		
	return dir
	
def MainMenu(sender):
	dir = MediaContainer(title1=server_name)
	total_songs, total_playlists = Populate()
	if total_songs:
		dir.Append(Function(DirectoryItem(GetArtists, title="Artists")))
		dir.Append(Function(DirectoryItem(GetAlbums, title="Albums")))
		dir.Append(Function(DirectoryItem(GetGenres, title="Genres")))
		if total_playlists: dir.Append(Function(DirectoryItem(GetPlaylists, title="Playlists")))
		dir.Append(Function(DirectoryItem(GetAlbums, title="Compilations"), title="Compilations", compilations=True))
	return dir
	
def isValidHost(host, port):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		s.settimeout(3)
		s.connect((host, port))
		s.shutdown(2)
		return True
	except:
		return False
		
def GetXML(uri, fill=False):
	url = "http://%s:%d" % (ff_host, ff_port)
	query = url + uri
	results = []
	for item in XML.ElementFromURL(query, errors='ignore').xpath('//dmap.listingitem'):
		row = {}
		for index in item: row[index.tag] = index.text
		if fill:
			for field in REQUIRED_TAGS:
				for tag in REQUIRED_TAGS[field]: 
					if tag not in row: row[tag] = 0 if field == "int" else None
		results.append(row)
	return results
	
def Populate():
	global song_db, playlist_db
	song_db = GetXML('/databases/1/items?output=xml&meta=dmap.itemname,dmap.itemid,daap.songalbum,daap.songartist,daap.songcompilation,daap.songdiscnumber,daap.songgenre,daap.songsize,daap.songtime,daap.songtracknumber,daap.songyear,daap.songuserrating', True)
	playlist_db = GetXML('/databases/1/containers?output=xml')
	return len(song_db), len(playlist_db)

def UniqueList(seq, idfun=None):
	if idfun is None:
		def idfun(x): return x
	seen = {}
	result = []
	for item in seq:
		marker = idfun(item)
		if marker in seen: continue
		seen[marker] = 1
		result.append(item)
	return result
	
def GetArtists(sender, start=None, end=None):
	dir = MediaContainer(title1=server_name, title2="Artists")
	artists = []
	for index in song_db:
		if not index['daap.songcompilation']: artists.append(index['daap.songartist'])
	artists = UniqueList(artists, lambda x: x.lower())
	if start is not None and end is not None: artists = artists[start:end]
	for artist in artists:
		first_word = artist.split(" ", 2)[0]
		title = "%s, %s" % (artist[len(first_word) + 1:len(artist)], first_word) if first_word.lower() in ["a", "an", "the"] else artist
		dir.Append(Function(ArtistItem(GetAlbums, artist=title), title=artist, artist=artist))
	del artists
	dir.Sort("artist")
	return dir

def GetAlbums(sender, title="Albums", artist=None, genre=None, container=1, compilations=False):
	dir = MediaContainer(title1=server_name, title2=title)
	albums = []
	if container <= 1:
		for index in song_db:
			row = None
			if not compilations:
				if not index['daap.songcompilation'] and index['daap.songalbum'] is not None:
					if (genre is None and artist and artist.lower() == index['daap.songartist'].lower()) or \
						(artist is None and genre and index['daap.songgenre'] and genre.lower() == index['daap.songgenre'].lower() or \
						(artist is None and genre is None)):
						row = {'daap.songalbum': index['daap.songalbum'], 'daap.songartist': index['daap.songartist'], 'daap.songcompilation': index['daap.songcompilation']}
			elif index['daap.songalbum'] is not None and index['daap.songcompilation']: row = {'daap.songalbum': index['daap.songalbum'], 'daap.songartist': index['daap.songartist'], 'daap.songcompilation': index['daap.songcompilation']}			
			if row is not None and row not in albums: albums.append(row)
	else:
		container_db = GetXML('/databases/1/containers/%d/items?output=xml&meta=dmap.itemname,dmap.itemid,daap.songalbum,daap.songartist,daap.songcompilation,daap.songsize,daap.songtime,daap.songyear' % container, True)
		for index in container_db:
			if index['daap.songalbum'] is not None:
				row = {'daap.songalbum': index['daap.songalbum'], 'daap.songartist': index['daap.songartist'], 'daap.songcompilation': index['daap.songcompilation']}
				if row not in albums: albums.append(row)
		del container_db
	albums = UniqueList(albums, lambda x: x['daap.songalbum'].lower())
	# Sorting routine. Hopefully this can be removed when correct AlbumItem hooks are implemented in a future version of Plex.
	albums = [(x['daap.songalbum'], x) for x in albums]
	albums.sort()
	albums = [y for (x,y) in albums]
	for album in albums:
		title = "%s - %s" % (album['daap.songalbum'], album['daap.songartist']) if not artist and not album['daap.songcompilation'] else album['daap.songalbum']
		dir.Append(Function(AlbumItem(GetSongs, artist=album['daap.songartist'], album=album['daap.songalbum'], year=album['daap.songyear']), album=['daap.songalbum'], artist=album['daap.songartist']))
#		dir.Append(Function(DirectoryItem(GetSongs, title=title), album=album['daap.songalbum'], artist=album['daap.songartist']))
	del albums	
	return dir

def GetPlaylists(sender):
	dir = MediaContainer(title1=server_name, title2="Playlists")	
	for index in playlist_db:
		if index['dmap.itemname'] != 'Library':
			dir.Append(Function(DirectoryItem(GetAlbums, title=index['dmap.itemname']), title=index['dmap.itemname'], container=int(index['dmap.itemid'])))	
	return dir
	
def GetSongs(sender, album, artist=None):
	dir = MediaContainer(title1=server_name, title2="Songs", viewGroup="Songs")	
	songs = []
	for index in song_db:
		if index['daap.songalbum'] is not None and album.lower() == index['daap.songalbum'].lower() and \
			((artist and artist.lower() == index['daap.songartist'].lower()) or not artist):
				url = "http://%s:%s/databases/1/items/%d.mp3" % (ff_host, ff_port, int(index['dmap.itemid']))
				dir.Append(TrackItem(url, title=index['dmap.itemname'], artist=index['daap.songartist'], album=index['daap.songalbum'], \
					index=int(index['daap.songtracknumber']), rating=int(index['daap.songuserrating']), duration=int(index['daap.songtime']), \
					size=int(index['daap.songsize']), year=int(index['daap.songyear']), \
					sort=int("%d%02d" % (int(index['daap.songdiscnumber']), int(index['daap.songtracknumber'])))))
	del songs
	dir.Sort("sort")
	return dir
	
def GetGenres(sender):
	dir = MediaContainer(title1=server_name, title2="Genres")
	genres = []
	for index in song_db:
		if index['daap.songgenre'] and index['daap.songgenre'] not in genres and not index['daap.songcompilation']:
			genres.append(index['daap.songgenre'])
	genres.sort()
	for genre in genres:
		dir.Append(Function(DirectoryItem(GetAlbums, title=genre), title=genre, genre=genre))
	del genres
	return dir
	
		