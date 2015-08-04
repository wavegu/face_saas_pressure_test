import os
import time
import json
import commands
import threading
import linecache
import sys

from pressure_test_report import *

gConfig = {}
gCaseTestTimeSDic = {}

gConfig['ip']   = '127.0.0.1'
gConfig['port'] = '21097'
gConfig['url']  = '/face/v1/algorithm/recognition/feature_extraction'
gConfig['access-id'] = '12345'
gConfig['signature'] = '12345'
gConfig['request body cluster path'] = '/disks/disk0/tool/jmeter_jsons/'

gConfig['test name'] = 'CS201 Pressure Test'
gConfig['test case list'] = ['watermark']
gConfig['thread number min'] = 1
gConfig['thread number max'] = 1
gConfig['thread number step'] = 1
gConfig['time out ms'] = '9999999'

gConfig['jmeter jmx path']  = 'jmeter_jmx/'
gConfig['monitor log path'] = 'dstat/'
gConfig['test result path'] = 'jmeter_result/'
gConfig['test report path'] = './pressure_test_report.txt'

gStartTime = ''
gFinishTime = ''
gStartClockS = 0.0
gFinishClockS = 0.0

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    print 'EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)


def GetFileName(name, suffix, needTime = False):
	localTimeList = list(time.localtime())
	year  = str(localTimeList[0])
	month = str(localTimeList[1])
	date  = str(localTimeList[2])
	hour  = str(localTimeList[3])
	minu  = str(localTimeList[4])
	if needTime:
		outputFileName = name + '_' + year + '_' + month  + '_' + date + '_' + hour + '_' + minu + '.' + suffix
	else:
		outputFileName = name + '.' + suffix
	return outputFileName


def colorPrint(color,mes):
    if color == 'r':
        fore = 31
    elif color == 'g':
        fore = 32
    elif color == 'b':
        fore = 36
    elif color == 'y':
        fore = 33
    else:
        fore = 37
    color = "\x1B[%d;%dm" % (1,fore)
    print "%s %s\x1B[0m" % (color,mes)


class Monitor(threading.Thread):

	def __init__(self, lifeLength, name, threadNumber):
		super(Monitor, self).__init__()
		self.mName = str(name)
		self.mLifeLength = lifeLength
		self.mThreadNumber = threadNumber

	def GetPidList(self):
		processItems = commands.getoutput('ps -ef | grep dstat').split('\n')
		pidList = []
		for item in processItems:
			arguments = item.split(' ')
			pos = 1
			while arguments[pos] == '':
				pos += 1
			pidList.append(arguments[pos])
		return pidList

	def Terminate(self):
		print
		pidList = self.GetPidList()
		for pid in pidList:
			print 'killing dstat', pid
			os.system('kill -9 ' + pid)

	def run(self):
		global gConfig
		if not os.path.isdir(gConfig['monitor log path']):
			os.mkdir(gConfig['monitor log path'])

		outputFileName = GetFileName(gConfig['monitor log path'] + self.mName + '_' + str(self.mThreadNumber), 'csv')
		cmd = 'dstat --output=' + outputFileName + ' -cdn -m'
		os.system(cmd)


class Jmeter:

	def __init__(self, threadNumber, caseName):
		global gConfig

		self.mIp   = gConfig['ip']
		self.mPort = gConfig['port']
		self.mUrl  = gConfig['url']
		self.mCaseName = caseName
		self.mThreadNumber = threadNumber
		self.mTestTime  = gCaseTestTimeSDic[self.mCaseName]
		self.mTimeOutMs = gConfig['time out ms']
		self.mAccessId  = gConfig['access-id']
		self.mSignature = gConfig['signature']

		self.mRequestBodyCluster = gConfig['request body cluster path'] + self.mCaseName + '.cluster'
		self.mConfigXmlFile = GetFileName(gConfig['jmeter jmx path'] + 'Jmeter_conf_' + self.mCaseName + '_' + str(self.mThreadNumber), 'jmx')
		self.mSampleLogFile = GetFileName(gConfig['test result path'] + 'Jmeter_result_' + self.mCaseName + '_' + '{0:0>2}'.format(str(self.mThreadNumber)), 'jtl')

		self.mMonitor = Monitor(200, 'dstat_' + self.mCaseName, self.mThreadNumber)


	def ChangeJMXLine(self, rawLine, tagHeader, newContent):
		if tagHeader in rawLine:
			tagTail = '</' + tagHeader.split(' ')[0].replace('<','') + '>'
			return tagHeader + newContent + tagTail
		return rawLine

	def GenerateConfigXmlFile(self):
		sampleFile = open('feature_extract_HTTP_Request.jmx')
		targetFile = open(self.mConfigXmlFile, 'w')

		jmxBlockNext = {}
		jmxBlockNext['TestPlan'] = 'ThreadGroup'
		jmxBlockNext['ThreadGroup'] = 'HTTPSamplerProxy'
		jmxBlockNext['HTTPSamplerProxy'] = 'HeaderManager'
		jmxBlockNext['HeaderManager'] = 'CSVDataSet'
		jmxBlockNext['CSVDataSet'] = 'ResultCollector'

		jmxBlock = 'TestPlan'

		for line in sampleFile.readlines():
			for current, next in jmxBlockNext.items():
				tagTail = '</' + current
				if tagTail in line:
					jmxBlock = next

			line = self.ChangeJMXLine(line, '<stringProp name="ThreadGroup.num_threads">', str(self.mThreadNumber))
			line = self.ChangeJMXLine(line, '<stringProp name="HTTPSampler.domain">', self.mIp)
			line = self.ChangeJMXLine(line, '<stringProp name="HTTPSampler.port">', self.mPort)
			line = self.ChangeJMXLine(line, '<stringProp name="HTTPSampler.connect_timeout">', self.mTimeOutMs)
			line = self.ChangeJMXLine(line, '<stringProp name="HTTPSampler.response_timeout">', self.mTimeOutMs)
			line = self.ChangeJMXLine(line, '<stringProp name="HTTPSampler.path">', self.mUrl)
			line = self.ChangeJMXLine(line, '<stringProp name="ThreadGroup.duration">', str(self.mTestTime))


			headerKey = 'access-id'
			if jmxBlock == 'HeaderManager':
				if '<stringProp name="Header.value">' in line:
					if headerKey == 'access-id':
						line = self.ChangeJMXLine(line, '<stringProp name="Header.value">', self.mAccessId)
						headerKey = 'signature'
					else:
						line = self.ChangeJMXLine(line, '<stringProp name="Header.value">', self.mSignature)

			elif jmxBlock == 'CSVDataSet':
				line = self.ChangeJMXLine(line, '<stringProp name="filename">', self.mRequestBodyCluster)

			elif jmxBlock == 'ResultCollector':
				line = self.ChangeJMXLine(line, '<stringProp name="filename">', self.mSampleLogFile)

			targetFile.write(line + '\n')

		sampleFile.close()
		targetFile.close()


	def Terminate(self):
		print
		colorPrint('g', 'killing jmeter ' + self.mCaseName + str(self.mThreadNumber)) 
		os.system('bash shutdown.sh')

	def Run(self):
		self.GenerateConfigXmlFile()
		self.mMonitor.start()
		startCmd = './jmeter -n -t ' + self.mConfigXmlFile + ' -l ' + self.mSampleLogFile
		os.system(startCmd)


class TestCase:

	def __init__(self, name):
		self.mName = name
		self.mTable = Table(name, ['Thread_number', 'Average(ms)', '50%', '75%', '90%', '95%', '99%', 'Min', 'Max','Samples','Error_number', 'Error%', 'QPS'])
		self.mCaseResultFileList = []
		self.mHttpErrorCodeDic = {}
		self.mMaxQPS = 0
		self.mLatency99 = 0

	def GetCaseResultFileList(self):
		global gConfig
		for fileName in os.listdir(gConfig['test result path']):
			if fileName.replace('Jmeter_result_', '').startswith(self.mName):
				self.mCaseResultFileList.append(fileName)
		self.mCaseResultFileList = sorted(self.mCaseResultFileList)

	def ParseCaseResultLine(self, line):
		resultDic = {}
		resultList = line.split(',')

		if len(resultList) < 4:
			print '[warning] list length too short!'
			print resultList
			return {}

		if resultList[3] == 'Non HTTP response code: java.net.SocketTimeoutException,Non HTTP response message: Read timed out':
			resultDic['httpCode'] = 'Time out'
		else:
			try:
				resultDic['httpCode'] = resultList[3]
			except:
				print
				colorPrint('r', self.mName + ' getting httpCode error!!!')
				colorPrint('r', line)
				return {}

		try:	
			resultDic['latency'] = int(resultList[-1])
		except:
			print
			colorPrint('r', self.mName + ' getting latency error!!!')
			colorPrint('r', line)
			return {}
		
		try:	
			resultDic['timeStampMs'] = int(resultList[0])
		except:
			print
			colorPrint('r', self.mName + ' getting timeStampMs error!!!')
			colorPrint('r', line)
			return {}
		
		return resultDic

	def GetCaseTable(self):
		global gConfig
		self.GetCaseResultFileList()

		for fileName in self.mCaseResultFileList:	# one row in table

			threadNumber = fileName.split('_')[-1].split('.')[0]
			latencyList = []
			timeStampMsList = []
			errorNumber = 0
			sampleNumber = 0
			latencySum = 0

			caseResultFile = open(gConfig['test result path'] + fileName)
			caseResultLines = caseResultFile.readlines()
			colorPrint('g', 'opening result file ' + gConfig['test result path'] + fileName)
			colorPrint('g', 'result line number is  ' + str(len(caseResultLines)))
			if len(caseResultLines) == 0:
				continue

			for line in caseResultLines:

				sampleNumber += 1
				resultDic = self.ParseCaseResultLine(line)

				if resultDic == {}:
					continue

				latencyList.append(resultDic['latency'])
				latencySum += resultDic['latency']

				httpCode = resultDic['httpCode']
				if httpCode != '200':
					errorNumber += 1
					if httpCode not in self.mHttpErrorCodeDic.keys():
						self.mHttpErrorCodeDic[httpCode] = 1
					else:
						self.mHttpErrorCodeDic[httpCode] += 1

				timeStampMsList.append(resultDic['timeStampMs'])


			if sampleNumber == 0:
				tableRow = [0,0,0,0,0,0,0,0,0,0,0,0,0]
				self.mTable.AddRow(tableRow)
				caseResultFile.close()
				continue

			latencyList = sorted(latencyList)

			latencyAverage = 0.0
			try:
				latencyAverage = float(latencySum) / float(sampleNumber)
			except:
				colorPrint('r', self.mName + ' get latencyAverage fail!!!')
				colorPrint('r', 'sampleNumber = ' + str(sampleNumber) + '   latencySum = ' + str(latencySum))

			latency50 = latencyList[(int)(sampleNumber * 0.50)]
			latency75 = latencyList[(int)(sampleNumber * 0.75)]
			latency90 = latencyList[(int)(sampleNumber * 0.90)]
			latency95 = latencyList[(int)(sampleNumber * 0.95)]
			latency99 = latencyList[(int)(sampleNumber * 0.99)]
			latencyMin = latencyList[0]
			latencyMax = latencyList[-1]

			self.mLatency99 = latency99

			errorRatio = 0.0
			try:
				errorRatio = float(100 * errorNumber) / float(sampleNumber)
			except:
				colorPrint('r', self.mName + ' get errorRatio fail!!!')
				colorPrint('r', 'sampleNumber = ' + str(sampleNumber) + '   errorNumber = ' + str(errorNumber))

			sortedTimeStampMsList = sorted(timeStampMsList)
			timeThroughSecond     = float(sortedTimeStampMsList[-1] - sortedTimeStampMsList[0]) / float(1000)

			QPS = 0.0
			try:
				QPS = float(sampleNumber - errorNumber) / float(timeThroughSecond)
			except:
				colorPrint('r', self.mName + ' get QPS fail!!!')
				colorPrint('r', 'sampleNumber = ' + str(sampleNumber) + '   timeThroughSecond = ' + str(timeThroughSecond))

			if QPS > self.mMaxQPS:
				self.mMaxQPS = QPS


			tableRow = [threadNumber, latencyAverage, latency50, latency75, latency90, latency95, latency99, latencyMin, latencyMax,sampleNumber,errorNumber, errorRatio, QPS]
			self.mTable.AddRow(tableRow)

			caseResultFile.close()

		return self.mTable



class TestController:

	def LoadConfig(self):

		global gConfig
		global gCaseTestTimeSDic

		configJson = open('test_config.json').read()
		configDic = json.loads(configJson)
		for blockKey, block in configDic.items():
			for key, value in block.items():
				if key in gConfig:
					gConfig[key] = value

		testBlock = configDic['test']
		for testCaseName in gConfig['test case list']:
			gCaseTestTimeSDic[testCaseName] = testBlock['default test time s']
		for testCaseName, testTimeS in testBlock['set case test time s'].items():
			gCaseTestTimeSDic[testCaseName] = testTimeS

		for key, value in gConfig.items():
			print '{0:.<50}'.format(key), value

		print

		for key, value in gCaseTestTimeSDic.items():
			print '{0:.<50}'.format(key), value


	def __init__(self):

		global gConfig
		self.LoadConfig()

		self.mTestCaseDic = {}
		for testCaseName in gConfig['test case list']:
			self.mTestCaseDic[testCaseName] = TestCase(testCaseName)

		if not os.path.isdir(gConfig['jmeter jmx path']):
			os.mkdir(gConfig['jmeter jmx path'])
		if not os.path.isdir(gConfig['test result path']):
			os.mkdir(gConfig['test result path'])

	def CleanResultFolder(self):
		if os.path.isdir(gConfig['test result path']):
			for resultFileName in os.listdir(gConfig['test result path']):
				clearCmd = 'rm ' + gConfig['test result path'] + resultFileName
				os.system(clearCmd)


	def RunTest(self):
		global gStartTime
		global gFinishTime

		gStartTime = time.ctime()
		gStartClockS = time.clock()

		for caseName in self.mTestCaseDic.keys():
			colorPrint('b', caseName+'begins....')
			for threadNumber in range(gConfig['thread number min'], gConfig['thread number max'] + 1, gConfig['thread number step']):
				jmeter = Jmeter(threadNumber, caseName)
				jmeter.GenerateConfigXmlFile()
				jmeter.Run()
				# time.sleep(gCaseTestTimeSDic[jmeter.mCaseName])
				# jmeter.Terminate()
				time.sleep(5)
				jmeter.mMonitor.Terminate()

		# jmeter = Jmeter(1, 'terminator')
		# jmeter.Terminate()


		gFinishTime = time.ctime()
		gFinishClock = time.clock()


	def GetReport(self):
		global gConfig
		global gStartTime
		global gFinishTime
		global gStartClockS
		global gFinishClockS

		for resultFile in os.listdir(gConfig['test result path']):
			tempFile = open(gConfig['test result path'] + resultFile)
			tempFile.close()

		testInfoBlock = Block('test info')
		testInfoBlock.AddItem('Start Time', gStartTime)
		testInfoBlock.AddItem('Finish Time', gFinishTime)
		testInfoBlock.AddItem('Time Through', str(gStartClockS - gFinishClockS))
		testInfoBlock.AddItem('Test Name', gConfig['test name'])
		testInfoBlock.AddItem('IP', gConfig['ip'])
		testInfoBlock.AddItem('Port', gConfig['port'])
		testInfoBlock.AddItem('Url', gConfig['url'])

		errorBlock    = Block('error')
		summaryBlock  = Block('summary')
		testCaseBlock = Block('test case')

		for caseName, testCase in self.mTestCaseDic.items():
		
			testCaseBlock.AddTable(testCase.GetCaseTable())
		
			summaryBlock.AddItem('caseName', caseName)
			summaryBlock.AddItem('Max QPS', testCase.mMaxQPS)
			summaryBlock.AddItem('99% Latency(ms)', testCase.mLatency99)
			summaryBlock.AddItem('', '')

			testCase.mHttpErrorCodeDic = sorted(testCase.mHttpErrorCodeDic.items(), key=lambda e:e[1], reverse=True)
			for items in testCase.mHttpErrorCodeDic:
				errorBlock.AddItem(str(items[0]), str(items[1]))


		report = Report(gConfig['test report path'])
		report.AddBlock(testInfoBlock)
		report.AddBlock(summaryBlock)
		report.AddBlock(errorBlock)
		report.AddBlock(testCaseBlock)
		report.Output()



if __name__ == '__main__':

	myTest = TestController()

	try:
		myTest.CleanResultFolder()
		myTest.RunTest()
		pass
	except BaseException:
		gFinishTime = time.ctime()
		print
		colorPrint('r', 'interrupted')

	try:
		colorPrint('g', 'Getting report')
		myTest.GetReport()
	except BaseException, argument:
		colorPrint('r', 'Get report fail')
		colorPrint('r', str(argument)) 
		PrintException()
