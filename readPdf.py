import pdfrw 
import os
import sys
"""
pass in pdf file
for every page in pdf
	run through every annotation
		
"""
"""
message = str(gPdfFile.pages[0].Annots[2].Contents)

print (message)

coords = str(gPdfFile.pages[0].Annots[2].Rect)

print (coords)

owner = str(gPdfFile.pages[0].Annots[2].T)

print (owner)

owner = str(gPdfFile.pages[0].CropBox)
"""


class PdfData:
	m_Pages = []

	def __init__(self, pdfFile):
		self.processPages(pdfFile)
	
	def processPages(self, pdfFile):
		for page in pdfFile.pages:
			self.m_Pages.append(Page(page))			


class Page:
	m_Comments = []
	m_PageWidth = 0
	m_PageHeight = 0
	def __init__(self, page):
		#get all comment data
		numComments = len(page.Annots)
		currentIndex = 0
		self.m_PageWidth = int(float(page.CropBox[2]))
		self.m_PageHeight = int(float(page.CropBox[3]))
		while True:
			self.m_Comments.append(Comment(page.Annots[currentIndex], self))

			#we increase by two because pdf appears to store each annotation twice
			currentIndex += 2
			if currentIndex > numComments - 1:
				break


class Comment:
	m_CommentString = ''
	m_CommentLocationX = 0
	m_CommentLocationY = 0 
	m_CommentOwner = ''
	m_CommentRelativeLocationX = 0
	m_CommentRelativeLocationY = 0

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
	for page in _pdf.m_Pages:
		#if the page has comments
		if page.m_Comments:
			#pull out the page image
			extractPageImage()
			#resize page image
			#for every comment
			#place annotation at relative location

def extractPageImage():
	#gswin32c -dNOPAUSE -dBATCH -sDEVICE=jpeg -dShowAnnots=false -dFirstPage=x -dLastPage=x -sOutputFile=x.xxx pdf.pdf
	exePath = gProgramDirectory + '\\gs9.21\\bin\\gswin32c.exe' 
	args = ' -dNOPAUSE -dBATCH -sDEVICE=jpeg -dShowAnnots=false '
	page = ''
	outputFile = ''
	inputFile =  ''

	fullArgs = exePath + args + page + outputFile + inputFile
	runExternalProgramFromBatch(args)

def annotateImage():
	pass

def runExternalProgramFromBatch(args):
	# Create temporary batch file to call ffmpeg
	tempBatFile = tempfile.NamedTemporaryFile(suffix='.bat', delete=False)
	tempBatFile.write(bytes(args, 'UTF-8'))
	tempBatFile.close()

	subprocess.call(tempBatFile.name)

	#remove temp batch file
	os.remove(tempBatFile.name)
	pass


gProgramDirectory = os.path.dirname(sys.argv[0])
gInputPdfFile = str(sys.argv[1])

#TODO pdf will be passed in dynamically
gPdfFile = pdfrw.PdfReader(gInputPdfFile)

#collect all annotation data inside the supplied pdf
gPdfData = PdfData(gPdfFile)
annotatePages(gPdfData)





