from imgurpython import ImgurClient
from random import randint
from apiclient.discovery import build
import os
import requests
import lxml
from bs4 import BeautifulSoup
from xml.etree import ElementTree
import logging
import threading

# Enable logging
logger = logging.getLogger(__name__)

client_id = '2b847434b5cfe44'
client_secret = 'dc2ac602ed45c95f1be94d4e2e49e3a3f0bc22f3'
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.environ.get("SEARCH_ENGINE_ID")
SAFE_LEVEL = os.environ.get("SAFE_LEVEL")
KONACHAN_MAX_OFFSET = int(os.environ.get("KONACHAN_MAX_OFFSET", 2000))

# Inizializza il client di Imgur
client = None

# Inizializza l'engine di Google API
service = None

def getFromGoogle(**kwargs):
	if service == None:
		service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)

	startIndex = randint(1,100)
	try:
		res = service.cse().list(
			q='loli',
			cx=SEARCH_ENGINE_ID,
			searchType="image",
			num=1,
			start=startIndex,
			safe=SAFE_LEVEL,
			).execute()
		return {"link" : res["items"][0]["link"], "gif" : False}
	except Exception as e:
		return getFromImgur()

def getFromImgur(**kwargs):
	if client == None:
		client = ImgurClient(client_id, client_secret)
	items = client.gallery_search("loli", advanced=None, sort='time', window='all', page=0)
	randNum = randint(0,len(items)-1)
	if items[randNum]:
		try:
			image = client.get_album_images(items[randNum].id)[0]
		except Exception as e:
			print(e)
			return getFromImgur();
		if image.animated:
			return {"link" : image.mp4, "gif" : True}
		else:
			return {"link" : image.link, "gif" : False}

def getFromZerochan(**kwargs):
	params = {"p" : randint(1,100), "s" : "random"}
	r1 = requests.get("http://www.zerochan.net/Little+Girl", params=params)
	imagesList = BeautifulSoup(r1.text, "lxml").find(id="thumbs2").find_all("li")
	r1.close()
	imageIndex = randint(0,len(imagesList)-1)
	r2 = requests.get("http://zerochan.net/" + imagesList[imageIndex].a["href"])
	imageUrl = BeautifulSoup(r2.text, "lxml").find(id="large").img["src"]
	r2.close()
	return {"link" : imageUrl, "gif" : False}

def printQualcosa():
	logger.debug("Qualcosa")

def getFromKonachan(param=None, **kwargs):
	print("Ciao")
	logger.debug("Avviato getFromKonachan")
	if param:
		text = "loli %s rating:safe" % param
	else:
		text = "loli rating:safe"
	if session:
		if param:
			params = {"limit": 0,
					"tags": text}
			req = requests.get("https://konachan.com/post.xml", params=params)
			tree = ElementTree.fromstring(req.content)
			count = int(tree.attrib["count"])
		else:
			count = models.getVariable(session, 'konachan_count') if not None else KONACHAN_MAX_OFFSET
			count = int(count)
	else:
		count = KONACHAN_MAX_OFFSET
		

	if param:
		text = "loli %s rating:safe" % param
	else:
		text = "loli rating:safe"

	params = {"limit": 1,
			"page": randint(0,count),
			"tags": text}
	try:
		req = requests.get("https://konachan.com/post.xml", params=params)
	except Exception as e:
		logger.error("Errore nel request a Konachan: %s", str(e))
		return None
	tree = ElementTree.fromstring(req.content)
	link = tree[0].attrib["file_url"]
	link = "https:" + link

	if session and not param:
		models.setVariable(session, 'konachan_count', str(tree.attrib['count']))

	return {"link": link, "gif": False}

# Metodi da usare per ottenere le immagini
ALGORITHMS = [#getFromZerochan,
			getFromKonachan]

ALGORITHMS_PARAMS = [getFromKonachan]

def getFromAlgorithms(session, param=None):
	logger.debug("GetFromAlgorithms in thread %i con parametri %s", threading.get_ident(), param)
	return getFromKonachan(None, session=None)
	if param:
		index = randint(0,len(ALGORITHMS_PARAMS)-1)
		return ALGORITHMS_PARAMS[index](param, session=session)
	else:
		index = randint(0,len(ALGORITHMS)-1)
		return ALGORITHMS[index](session=session)
