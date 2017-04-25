import pdfrw 
import os
import sys
import tempfile
import subprocess
import time
import json
import shutil
from PIL import Image
from trello import TrelloClient
"""
message = str(gPdfFile.pages[0].Annots[2].Contents)
coords = str(gPdfFile.pages[0].Annots[2].Rect)
owner = str(gPdfFile.pages[0].Annots[2].T)
owner = str(gPdfFile.pages[0].CropBox)
"""
#todo delete temp working directory after upload completed

class PdfData:

	def __init__(self, pdfFile):
		self.m_Pages = []
		self.processPages(pdfFile)
	
	#run through every page in the pdf and get information about the comments
	def processPages(self, pdfFile):
		for page in pdfFile.pages:
			self.m_Pages.append(Page(page))			


class Page:
	def __init__(self, page):
		self.m_Comments = []
		self.m_PageWidth = int(float(page.CropBox[2]))
		self.m_PageHeight = int(float(page.CropBox[3]))
		currentIndex = 0
		#abort if this page doesn't contain annotations
		if not page.Annots:
			return

		numComments = len(page.Annots)
		#process all the comments on the page
		while True:
			self.m_Comments.append(Comment(page.Annots[currentIndex], self))
			#we increase by two because pdf appears to store each annotation twice
			currentIndex += 2
			if currentIndex > numComments - 1:
				break


class Comment:
	def __init__(self, annot, page):
		self.m_CommentString = annot.Contents
		self.m_CommentLocationX = int(float(annot.Rect[2]))
		self.m_CommentLocationY = int(float(annot.Rect[3]))
		self.m_CommentOwner = annot.T
		#convert the absolute annotation position into a relative one
		self.m_CommentRelativeLocationX = self.m_CommentLocationX / page.m_PageWidth
		self.m_CommentRelativeLocationY = self.m_CommentLocationY / page.m_PageHeight 


def annotatePages(_pdf):
	#start at one to make it human readable
	currentPageNum = 1
	for page in _pdf.m_Pages:
		#if the page has comments
		if page.m_Comments:
			#pull out the page image
			processAndUploadPage(currentPageNum, _pdf)
			
		currentPageNum += 1

def processAndUploadPage(pageNum, _pdf):
	#make the output directory if it doesn't already exist
	if not os.path.exists(gProgramDirectory + '\\tempworkingdir'):
		os.mkdir(gProgramDirectory + '\\tempworkingdir')

	exePath = '"' + gProgramDirectory + '\\gs9.21\\bin\\gswin32c.exe' + '"' 
	args = ' -dNOPAUSE -dBATCH -sDEVICE=jpeg -dShowAnnots=false '
	pdfFileName = os.path.basename(gInputPdfFile)
	pageNumber = '-dFirstPage=' + str(pageNum) + ' -dLastPage=' + str(pageNum) + ' '
	imageFile = '"' + gProgramDirectory + '\\tempworkingdir\\' + pdfFileName + '_' + str(pageNum) + '.jpg' + '"'
	outputFile = '-sOutputFile=' + '"' + gProgramDirectory + '\\tempworkingdir\\' + pdfFileName + '_' + str(pageNum) + '.jpg" '
	inputFile =  '"' + gInputPdfFile + '"'

	fullArgs = exePath + args + pageNumber + outputFile + inputFile
	runExternalProgramFromBatch(fullArgs)
	annotateImage(pageNum, _pdf)
	uploadToTrello(gProgramDirectory + '\\tempworkingdir\\' + pdfFileName + '_' + str(pageNum) + '.jpg', pageNum, _pdf)

def annotateImage(pageNum, _pdf):
	#resize page image
	exePath = 'imagemagick\\convert '
	pdfFileName = os.path.basename(gInputPdfFile)
	pdfImage = '"' + gProgramDirectory + '\\tempworkingdir\\' + pdfFileName + '_' + str(pageNum) + '.jpg" ' 
	imageMaxBoundsSize = getValueFromJSON('Config.json', 'Properties', 'MaxExtractedImageSize')
	args = '-resize ' + imageMaxBoundsSize + 'x' + imageMaxBoundsSize + ' '
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
		argAnnotSize = getValueFromJSON('Config.json', 'Properties', 'AnnotationSize')
		argAnnotSize = '-size ' + argAnnotSize + 'x' + argAnnotSize
		args = ' -background yellow -fill black -font impact ' + argAnnotSize + ' -gravity center label:' + str(currentComment) + ' tempworkingdir\\number.jpg'
		fullArgs = exePath + args
		runExternalProgramFromBatch(fullArgs)

		#add the annotation number to the extracted image
		exePath = 'imagemagick\\composite '
		args = '-gravity SouthWest'
		img = Image.open(gProgramDirectory + '\\tempworkingdir\\' + pdfFileName + '_' + str(pageNum) + '.jpg')
		xOffset = _pdf.m_Pages[pageNum - 1].m_Comments[currentComment - 1].m_CommentRelativeLocationX * img.size[0]
		yOffset = _pdf.m_Pages[pageNum - 1].m_Comments[currentComment - 1].m_CommentRelativeLocationY * img.size[1]
		annotate = ' -geometry +' + str(int(xOffset)) + '+' + str(int(yOffset)) + ' '
		numberImg = '"' + gProgramDirectory + '\\tempworkingdir\\number.jpg" '
		fullArgs = exePath + args + annotate + numberImg + pdfImage + pdfImage
		runExternalProgramFromBatch(fullArgs)
		currentComment += 1

def uploadToTrello(imagePath, pageNum, _pdf):
	checklistItems = []
	index = 1
	for comment in _pdf.m_Pages[pageNum - 1].m_Comments:
		checklistItems.append(str(index) + '. ' + comment.m_CommentString)
		index += 1
	fileAttachment = open(imagePath, 'rb')
	gTrelloClient.addCard(os.path.basename(gInputPdfFile) + '_' + str(pageNum), checklistItems, fileAttachment)


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
					if getValueFromJSON('Config.json', 'Properties', 'BoardName') in board.name:	
						print('Found board')
						for list in board.all_lists():
							if getValueFromJSON('Config.json', 'Properties', 'ListName') in list.name:	
								print('Found list')
								return list

						print('List could not be found. Make sure list name exactly matches config.json')
						break
						exit()
				print('Board could not be found. Make sure board name contains the correct spelling and case inside config.json')
				break;
				exit()
		print('Team could not be found. Make sure spelling exactly matches what is listed on Trello')
		exit()

	def addCard(self, cardName, checklistItems, fileAttachment):
		card = self.list.add_card(cardName)
		card.attach(file = fileAttachment, mimeType = 'image/jpeg', name = cardName + '.jpg')
		card.add_checklist('Checklist', checklistItems)
		

gProgramDirectory = os.path.dirname(sys.argv[0])
gInputPdfFile = str(sys.argv[1])

gTrelloClient = Trello()

gPdfFile = pdfrw.PdfReader(gInputPdfFile)

#collect all annotation data inside the supplied pdf
gPdfData = PdfData(gPdfFile)
annotatePages(gPdfData)

#delete temporary directory after we're done
shutil.rmtree(gProgramDirectory + '\\tempworkingdir')

print('\n\nDone!\n\n')

						