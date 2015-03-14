from numpy import *
from scipy import *
from wave import *
import wave
import struct

leftChannel = array (list())
rightChannel = array (list())
resonantConst = 183
formatDict = dict()
startofFileIndex = 0

#
#  attributes of wav files:
#  max bit amplitude:		32767
#  min bit amplitude:      -32767
#  resting bit range:      (-4,4)
#  bits per second:         48000
#  middle C bit period:     183 bits 
#  
#  ARBITRARY NUMBER LIST:
#  1000:  predicted amplitude of a bit being audible by human hearing on max volume
#  200:   predicted number of bits where a silence is discernable
#   

def wavLoad (fname):
	#initialize wav file
	RawWav = wave.open (fname, "r")
	#create struct containing attributes of the audio data 
	(nchannels, sampwidth, framerate, nframes, comptype, compname) = RawWav.getparams()
	#number of frames in the entire file (ie, number of data points for data scientists)
	frames = RawWav.readframes (nframes * nchannels)
	#list of every single point of data
	out = struct.unpack_from ("%dh" % nframes * nchannels, frames)

	# Next up: convert 2 channels to numpy arrays
	# 
	# If your song is written in more than two channels
	# may god have mercy on you.
	global leftChannel
	global rightChannel

	if nchannels == 2:
	   leftChannel = array (list (out[0::2]))
	   rightChannel = array (list  (out[1::2]))
	
	else:
	   leftChannel = array (out)
	   rightChannel = leftChannel

def isEndOfFile(bitIndex):
	# seg fault safety.  making sure the calculations don't go out of range
	if (bitIndex+100 >= leftChannel.size):
		return True
	return False

def findEmpendingSilence(bitIndex):
	# detects noise within the next 100 bits
	if (not isEndOfFile(bitIndex)):
		for i in range (bitIndex, bitIndex+100):
			if leftChannel[i] > 1000 or leftChannel[i] < -1000:
				return False
	return True

def isMidPeriod(bitIndex):
	# if a 'silent' bit is found, this is to verify 
	# whether or not the bit actually just mid cycle
	if (not isEndOfFile(bitIndex)):
		if (leftChannel[bitIndex+100] > 1000 or leftChannel[bitIndex+100] < -1000):
			if (leftChannel[bitIndex-100] > 1000 or leftChannel[bitIndex-100] < -1000):
				return True
	return False

def findFileStart():
	for bitIndex in range(0,leftChannel.size):
		# 1000 amplitude is expected to be audible
		if (leftChannel[bitIndex] > 1000 or leftChannel[bitIndex] < -1000):
			return bitIndex

def CreateMorseList(channel):
	global startofFileIndex
	distanceSegments = list()
	startofFileIndex = findFileStart()
	silenceToggle = False
	currentSegmentSize = 0

	# 200 is the bit frequency where audio is still audible
	for bitIndex in range(startofFileIndex,leftChannel.size,1):

		if(silenceToggle):
			#detecting something audible after silence
			if ((leftChannel[bitIndex] > 1000 or leftChannel[bitIndex] < -1000 or isMidPeriod(bitIndex)) and currentSegmentSize > 1000):
				if (currentSegmentSize > 200):
					distanceSegments.append((currentSegmentSize, False))
				currentSegmentSize = 1
				silenceToggle = False
				continue

		elif(not silenceToggle):
			#detecting silence after a bunch of noise
			if ((leftChannel[bitIndex] <= 1000 and leftChannel[bitIndex] >= -1000) and findEmpendingSilence(bitIndex) and currentSegmentSize > 1000):
				if (currentSegmentSize > 200):
					distanceSegments.append((currentSegmentSize, True))
				currentSegmentSize = 1
				silenceToggle = True
				continue

		currentSegmentSize += 1
	return distanceSegments

# many morse code generators vary, and many don't
# output a consitent number of bits.  This algorithm
# is designed to fight these inconsistencies.
def formatParsingAlgo(MorseCodeData):
	formatDict = dict()
	#create list of all empty segments and noise segments
	falseList = list()
	trueList = list()

	for segmentIndex in range(0,len(MorseCodeData)):
		if MorseCodeData[segmentIndex][1] == False:
			falseList.append(MorseCodeData[segmentIndex][0])
		else:
			trueList.append(MorseCodeData[segmentIndex][0])

	trueList.sort()
	#no dah's found
	if (trueList[0] + 100  > trueList[-1]):
		trueList[-1] = -1


	formatDict['dit'] = trueList[1]
	formatDict['dah'] = trueList[-1]
	
	falseList.sort()

	for i in range(0,len(falseList)):
		# dits have the same length as the space between bits
		# dahs have the same length as the space between letters
		# these if statements check and assing space lengths based on this information 
		if (formatDict['dit'] + 100 > falseList[i] and formatDict['dit'] - 100 < falseList[i]):
			formatDict['symbolspace'] = falseList[i]
		elif (formatDict['dah'] + 100 > falseList[i] and formatDict['dah'] - 100 < falseList[i]):
			formatDict['letterspace'] = falseList[i]

	#checking to make sure letterspace is defined
	#there were instances during testing where the input was just letters and no words of length > 1
	#this caused a key error
	
	if not 'symbolspace' in formatDict:
		formatDict['symbolspace'] = formatDict['dit']
	
	if not 'letterspace' in formatDict:
		formatDict['letterspace'] = formatDict['symbolspace']*2
		#check for multiple words
	if(falseList[-1] -100 > formatDict['letterspace']):
		formatDict['wordspace'] = falseList[-1]

	return formatDict

def ParseIntoMorse(MorseCodeData):
	#actual dits and dahs and silences
	MorseCode = list()
	for segment in MorseCodeData:
		segLen = segment[0]
		segType = segment[1]

		# if segment is audible
		if (segType == True):
			# what type of audio?
			if (segLen <= formatDict['dah'] + 1000 and segLen >= formatDict['dah'] - 1000):
				MorseCode.append('-')

			if (segLen <= formatDict['dit']+ 1000 and segLen >= formatDict['dit'] - 1000):
				MorseCode.append('.')

		# if segment is silence
		if (segType == False):
			# what type of silence?
			if (segLen <= formatDict['letterspace'] + 1000 and segLen >= formatDict['letterspace'] - 1000):
				MorseCode.append(' ')

			if (segLen <= formatDict['symbolspace'] + 1000 and segLen >= formatDict['symbolspace'] - 1000):
				# space between dits and dahs has no representative
				continue

			if (segLen <= formatDict['wordspace'] + 1000 and segLen >= formatDict['wordspace'] - 1000):
				MorseCode.append('   ')

	return MorseCode


if (__name__ == "__main__"):
	#load morse load translations from external file
	f = file('morsecodetranslation.txt', 'r')
	LetterToMorse = f.read().split()
	
	#create a dictionary that stores all the translations in the morse code file
	MorseDict = dict()
	for morseIndex in range(0,len(LetterToMorse),2):
		MorseDict[str(LetterToMorse[morseIndex+1])] = LetterToMorse[morseIndex]
	MorseDict[""] = " "

	#load up the left and right channels
	wavLoad("alphabetmorse.wav")

	#take morse code data and load it up
	rawMorseCodeData = CreateMorseList(leftChannel)

	#find data, how long are the dits and dahs? the silences? 
	#how much silence is at the beginning and the end?
	formatDict = formatParsingAlgo(rawMorseCodeData)

	#finally, create readable morse code from list list
	MorseCode = ParseIntoMorse(rawMorseCodeData)

	output = ""
	for i in "".join(MorseCode).split(" "):
		output += MorseDict[i]
		#print i,

	print output
