class Item:

	def __init__(self, key, value):
		self.mKey = str(key)
		self.mValue = str(value)

	def ToString(self):
		targetString = '	' + '{0:.<75}'.format(self.mKey) + self.mValue
		return targetString



class Table:

	def __init__(self, name, keys):
		self.mName = name
		self.mKeys = list(keys)
		self.mDicList = []	# every row is a dict

	def AddRow(self, values):
		lenValue = len(values)
		lenKeys = len(self.mKeys)
		if lenValue != lenKeys:
			print 'Add Table row Error! ', lenValue, ' values but', lenKeys, ' keys!'
			return
		rowDic = {}
		for looper in range(lenValue):
			rowDic[self.mKeys[looper]] = str(values[looper])
		self.mDicList.append(rowDic)



class Block:

	def __init__(self, title):
		self.mTitle = '[' + title.upper() + ']'
		self.mItems = []
		self.mTables = []

	def AddItem(self, key, value):
		self.mItems.append(Item(key, value))

	def AddTable(self, table):
		self.mTables.append(table)



class Report:

	def __init__(self, outputPath):
		self.mBlocks = []
		self.mOutputPath = outputPath

	def AddBlock(self, block):
		self.mBlocks.append(block)

	def Output(self):
		outputFile = open(self.mOutputPath, 'w')
		for block in self.mBlocks:
			outputFile.write(block.mTitle + '\n')
			for item in block.mItems:
				outputFile.write(item.ToString() + '\n')
			outputFile.write('\n')
			for table in block.mTables:
				outputFile.write('[case]' + table.mName + '\n')
				for key in table.mKeys:
					outputFile.write('{0: ^15}'.format(key))
				outputFile.write('\n')
				for dic in table.mDicList:
					for key in table.mKeys:
						outputFile.write('{0: ^15}'.format(dic[key]))
					outputFile.write('\n')
				outputFile.write('{0:-<300}'.format('') + '\n')
			outputFile.write('\n')

			outputFile.write('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n')