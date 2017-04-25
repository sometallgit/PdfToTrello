import pdfrw 
import os
import sys
import tempfile
import subprocess
import time
import json
from PIL import Image
from trello import TrelloClient
"""
message = str(gPdfFile.pages[0].Annots[2].Contents)
coords = str(gPdfFile.pages[0].Annots[2].Rect)
owner = str(gPdfFile.pages[0].Annots[2].T)
owner = str(gPdfFile.pages[0].CropBox)
"""


class PdfData:

	def __init__(self, pdfFile):
		self.m_Pages = []
		self.processPages(pdfFile)
	
	def processPages(self, pdfFile):
		for page in pdfFile.pages:
			print('process page')
			self.m_Pages.append(Page(page))			


class Page:
	def __init__(self, page):
		self.m_Comments = []
		self.m_PageWidth = 0
		self.m_PageHeight = 0
		#get all comment data
		currentIndex = 0
		self.m_PageWidth = int(float(page.CropBox[2]))
		self.m_PageHeight = int(float(page.CropBox[3]))
		if not page.Annots:
			return
		numComments = len(page.Annots)
		while True:
			self.m_Comments.append(Comment(page.Annots[currentIndex], self))
			print('process comment')
			#we increase by two because pdf appears to store each annotation twice
			currentIndex += 2
			if currentIndex > numComments - 1:
				break


class Comment:
	'''
	m_CommentString = ''
	m_CommentLocationX = 0
	m_CommentLocationY = 0 
	m_CommentOwner = ''
	m_CommentRelativeLocationX = 0
	m_CommentRelativeLocationY = 0
	'''

	def __init__(self, annot, page):
		self.m_CommentString = annot.Contents
		self.m_CommentLocationX = int(float(annot.Rect[2]))
		self.m_CommentLocationY = int(float(annot.Rect[3]))
		self.m_CommentOwner = annot.T
		self.m_CommentRelativeLocationX = self.m_CommentLocationX / page.m_PageWidth
		self.m_CommentRelativeLocationY = self.m_CommentLocationY / page.m_PageHeight 
		print(self.m_CommentString)
		print('Relative Location X: ' + str(self.m_CommentRelativeLocationX))
		print('Relative Location Y: ' + str(self.m_CommentRelativeLocationY))


def annotatePages(_pdf):

	#for every page
	pageNum = 1
	for page in _pdf.m_Pages:
		#if the page has comments
		if page.m_Comments:
			#pull out the page image
			extractPageImage(pageNum, _pdf)
			
		pageNum += 1

def extractPageImage(pageNum, _pdf):
	#make the output directory if it doesn't already exist
	if not os.path.exists(gProgramDirectory + '\\tempworkingdir'):
		os.mkdir(gProgramDirectory + '\\tempworkingdir')
	#gswin32c -dNOPAUSE -dBATCH -sDEVICE=jpeg -dShowAnnots=false -dFirstPage=x -dLastPage=x -sOutputFile=x.xxx pdf.pdf
	exePath = gProgramDirectory + '\\gs9.21\\bin\\gswin32c.exe' 
	args = ' -dNOPAUSE -dBATCH -sDEVICE=jpeg -dShowAnnots=false '
	pageNumber = '-dFirstPage=' + str(pageNum) + ' -dLastPage=' + str(pageNum) + ' '
	imageFile = gProgramDirectory + '\\tempworkingdir\\temppage_' + str(pageNum) + '.jpg'
	outputFile = '-sOutputFile=' + gProgramDirectory + '\\tempworkingdir\\temppage_' + str(pageNum) + '.jpg '
	inputFile =  gInputPdfFile

	fullArgs = exePath + args + pageNumber + outputFile + inputFile
	runExternalProgramFromBatch(fullArgs)
	annotateImage(pageNum, _pdf)
	uploadToTrello(imageFile, pageNum, _pdf)

#todo fix a lot of the hardcoding in here and expose a lot of it to config
def annotateImage(pageNum, _pdf):
	#resize page image
	exePath = 'imagemagick\\convert '
	pdfImage = gProgramDirectory + '\\tempworkingdir\\temppage_' + str(pageNum) + '.jpg ' 
	args = '-resize 1500x1500 '
	fullArgs = exePath + pdfImage + args + pdfImage
	runExternalProgramFromBatch(fullArgs)

	#for every comment
	#place annotation at relative location
	currentComment = 1
	while True:
		if currentComment > len(_pdf.m_Pages[pageNum - 1].m_Comments):
			break
		#create an annotation number
		exePath = 'imagemagick\\convert '
		args = ' -background yellow -fill black -font impact -size 25x25 -gravity center label:' + str(currentComment) + ' tempworkingdir\\number.jpg'
		fullArgs = exePath + args
		runExternalProgramFromBatch(fullArgs)

		#add the annotation number to the extracted image
		exePath = 'imagemagick\\composite '
		args = '-gravity SouthWest'
		img = Image.open(pdfImage)
		xOffset = _pdf.m_Pages[pageNum - 1].m_Comments[currentComment - 1].m_CommentRelativeLocationX * img.size[0]
		yOffset = _pdf.m_Pages[pageNum - 1].m_Comments[currentComment - 1].m_CommentRelativeLocationY * img.size[1]
		annotate = ' -geometry +' + str(int(xOffset)) + '+' + str(int(yOffset)) + ' '
		numberImg = gProgramDirectory + '\\tempworkingdir\\number.jpg '
		fullArgs = exePath + args + annotate + numberImg + pdfImage + pdfImage
		runExternalProgramFromBatch(fullArgs)
		#imagemagick\convert.exe -background yellow -fill black -font impact -size 25x25 -gravity center label:number output.jpg
		#imagemagick\composite -gravity SouthWest number.jpg image.jpg image.jpg
		currentComment += 1

def uploadToTrello(imagePath, pageNum, _pdf):
	checklistItems = []
	index = 1
	for comment in _pdf.m_Pages[pageNum - 1].m_Comments:
		checklistItems.append(str(index) + '. ' + comment.m_CommentString)
		index += 1
	print(checklistItems)
	fileAttachment = open(imagePath, 'rb')
	gTrelloClient.addCard('pdf filename and page number', checklistItems, fileAttachment)


def runExternalProgramFromBatch(args):
	# Create temporary batch file to call ffmpeg
	tempBatFile = tempfile.NamedTemporaryFile(suffix='.bat', delete=False)
	tempBatFile.write(bytes(args, 'UTF-8'))
	tempBatFile.close()

	subprocess.call(tempBatFile.name)

	#remove temp batch file
	os.remove(tempBatFile.name)

def getValueFromJSON(filename, category, value):
    with open(gProgramDirectory + '\\' + filename) as data_file:
        data = json.load(data_file)

    return data[category][value]

class Trello:
	def __init__(self):
		self.client = TrelloClient(
		    api_key= getValueFromJSON('auth.json', 'Properties', 'api_key'),
		    api_secret=getValueFromJSON('auth.json', 'Properties', 'api_secret'),
		    token=getValueFromJSON('auth.json', 'Properties', 'token'),
		    token_secret=getValueFromJSON('auth.json', 'Properties', 'token_secret')
		)
		self.list = self.findList()

	def findList(self):
		self.teamName = input('Enter team name: ')
		for org in self.client.list_organizations():
			if org.name.startswith(self.teamName):
				print('Found Team')
				for board in org.all_boards():
					if board.name.startswith('board'):	
						print(board)
						for list in board.all_lists():
							if list.name.startswith('list'):
								print(list)
								return list

		print('Team could not be found.')

	def addCard(self, cardName, checklistItems, fileAttachment):
		card = self.list.add_card(cardName)

		
		card.attach(file = fileAttachment, mimeType = 'image/jpeg', name = 'img.jpg')
		card.add_checklist('Checklist', checklistItems)
		

gProgramDirectory = os.path.dirname(sys.argv[0])
gInputPdfFile = str(sys.argv[1])

gTrelloClient = Trello()

#TODO pdf will be passed in dynamically
gPdfFile = pdfrw.PdfReader(gInputPdfFile)

#collect all annotation data inside the supplied pdf
gPdfData = PdfData(gPdfFile)
annotatePages(gPdfData)





						