import socket
import threading
import sys
import os

from PyQt5 import QtCore, QtGui, QtWidgets  #QDir, Qt
from clientUI import Ui_clientUIMain
#---------------------- INTERFACE -------------------------
class clientInterface(Ui_clientUIMain):
	def __init__(self, ftpClientUIMain, ftpClient):
		Ui_clientUIMain.__init__(self)
		self.setupUi(ftpClientUIMain)
		self.ftpClient = ftpClient
		
		self.pushButtonLogout.setEnabled(False)
		
		#==================== Tree View (Model based) ==============================
		# Set up tree view for client directory:
		self.clientDirectoryModel = QtWidgets.QFileSystemModel()
		
		# You can setRootPath to any path.
		self.clientDirectoryModel.setRootPath(QtCore.QDir.rootPath())
		#self.treeViewClientDirectory = QtWidgets.QTreeView()
		self.treeViewClientDirectory.setModel(self.clientDirectoryModel)
		self.treeViewClientDirectory.setRootIndex(self.clientDirectoryModel.setRootPath(QtCore.QDir.rootPath()))
		self.pathSelectedItem = QtCore.QDir.rootPath()
		#====================== End Tree View ========================
		
		
		#================== Table View (Item based) ==================
		
		#====================== End Table View ========================
		
		
		#=============== Connect Widgets to Functions =================
		# Connect push buttons clicked action to respective functions:
		self.pushButtonLogin.clicked.connect(self.pushButtonLoginClicked)
		self.pushButtonLogout.clicked.connect(self.pushButtonLogoutClicked)
		self.pushButtonRootDirectory.clicked.connect(self.pushButtonRootDirectoryClicked)
		self.pushButtonUpload.clicked.connect(self.pushButtonUploadClicked)
		self.pushButtonDownload.clicked.connect(self.pushButtonDownloadClicked)
		self.pushButtonCreateDirectory.clicked.connect(self.pushButtonCreateDirectoryClicked)
		self.pushButtonDeleteDirectory.clicked.connect(self.pushButtonDeleteDirectoryClicked)
		
		self.treeViewClientDirectory.clicked.connect(self.treeViewClientDirectoryClicked)
		self.tableWidgetServerDirectory.doubleClicked.connect(self.getSelectedItem)
		
		#==============================================================
		
	def pushButtonLoginClicked(self):
		hostServerName = self.lineEditHostName.text()
		username 	   = self.lineEditUsername.text()
		password	   = self.lineEditPassword.text()
		
		# Login:
		hostServerName = 'Julius-HP'
		username = 'group6'
		password = 'reiph9Ju'
		try:
			self.ftpClient.login(hostServerName, username, password)
			self.pushButtonLogout.setEnabled(True)
			self.pushButtonRootDirectoryClicked()
			self.labelStatus.setText('Login successful.')
		except:
			self.labelStatus.setText('Login unsuccessful.')
	
	def pushButtonLogoutClicked(self):
		# Logout:
		try:
			#tLogin = threading.Thread(target=self.ftpClient.login, args=(hostServerName, username))
			#tLogin.start()
			self.ftpClient.logout()
			self.pushButtonLogout.setEnabled(False)
			self.tableWidgetServerDirectory.setRowCount(0) 
			self.labelStatus.setText('Logout successful.')
		except:
			self.labelStatus.setText('Logout unsuccessful.')
	
	def updateServerDirectoryWidget(self):
		try:
			self.tableWidgetServerDirectory.setRowCount(0)
			listOfFilesInDirectory = self.ftpClient.updateDirectoryList()
			
			# set column count
			self.tableWidgetServerDirectory.setColumnCount(4)
			
			# Set Row Count:
			self.tableWidgetServerDirectory.setRowCount(len(listOfFilesInDirectory)+1)
			# Default:
			self.tableWidgetServerDirectory.setItem(0,0, QtWidgets.QTableWidgetItem(".."))
			
			row = 1
			col = 0
			for item in listOfFilesInDirectory:
				for fileProperty in item:
					self.tableWidgetServerDirectory.setItem(row,col, QtWidgets.QTableWidgetItem(fileProperty))
					col = col+1
				row = row+1
				col = 0
				
			self.tableWidgetServerDirectory.setHorizontalHeaderItem(0, QtWidgets.QTableWidgetItem("Filename"))
			self.tableWidgetServerDirectory.setHorizontalHeaderItem(1, QtWidgets.QTableWidgetItem("Size"))
			self.tableWidgetServerDirectory.setHorizontalHeaderItem(2, QtWidgets.QTableWidgetItem("Last Modified"))
			self.tableWidgetServerDirectory.setHorizontalHeaderItem(3, QtWidgets.QTableWidgetItem("Permissions"))
		except:
			self.labelStatus.setText('Unable to update Server Directory.')
	
	
	def parentDirectoryClicked(self):
		try:
			self.ftpClient.changeToParentDirectory()
			self.updateServerDirectoryWidget()
			self.labelStatus.setText('Directory successfully changed to Parent Directory!')
		except:
			self.labelStatus.setText('Unable to change to Parent Directory!')
	
	def pushButtonRootDirectoryClicked(self):
		try:
			self.ftpClient.changeToRootDirectory()
			self.updateServerDirectoryWidget()
			self.labelStatus.setText('Directory successfully changed to Root Directory!')
		except:
			self.labelStatus.setText('Unable to change to Root Directory!')
	
	def changeWorkingDirectoryClicked(self, pathName):
		try:
			self.ftpClient.changeWorkingDirectory(pathName)
			self.updateServerDirectoryWidget()
			self.labelStatus.setText('Directory successfully changed!')
		except:
			self.labelStatus.setText('Unable to change Directory!')
	
	def pushButtonCreateDirectoryClicked(self):
		try:
			folderName = self.lineEditNewDirectory.text()
			if folderName!='':
				self.ftpClient.createDirectory(folderName)
				self.updateServerDirectoryWidget()
				
				self.labelStatus.setText('New directory created!')
		except:
			self.labelStatus.setText('Unable to create directory!')
	
	
	def pushButtonDeleteDirectoryClicked(self):
		try:
			for currentQTableWidgetRow in self.tableWidgetServerDirectory.selectionModel().selectedRows():
				if currentQTableWidgetRow.row()!=0:
					filename = self.tableWidgetServerDirectory.item(currentQTableWidgetRow.row(), 0).text()
					self.ftpClient.deleteDirectory(filename)
					
			self.updateServerDirectoryWidget()
			self.labelStatus.setText('Directory deleted!')
		except:
			self.labelStatus.setText('Unable to delete directory!')
	
	def treeViewClientDirectoryClicked(self, signal):
		self.pathSelectedItem = self.treeViewClientDirectory.model().filePath(signal)
		#print(self.pathSelectedItem)
		
	def pushButtonUploadClicked(self):
		try:
			# Check if selected item is not a folder:
			fileUpload = self.pathSelectedItem
			if not os.path.isdir(fileUpload) and os.path.exists(fileUpload):
				temp = fileUpload.rsplit('/')
				self.currentDirectory = temp[0]
				selectedFile = temp[1]
				self.ftpClient.upload(selectedFile, self.currentDirectory)
				self.labelUploadStatus.setText('File upload complete.')
				self.updateServerDirectoryWidget()
			else:
				self.labelUploadStatus.setText('Cannot upload folders!')
		except:
			self.labelUploadStatus.setText('Upload failed.')
	
	def getSelectedItem(self):
		try:
			for currentQTableWidgetRow in self.tableWidgetServerDirectory.selectionModel().selectedRows():
				if currentQTableWidgetRow.row()!=0:
					self.pushButtonDownloadClicked()
				else:
					self.parentDirectoryClicked()
		except:
			self.labelDownloadStatus.setText('Cannot select file/folder.')
	
	def pushButtonDownloadClicked(self):
		try:
			
			# Check selected table item:
			for currentQTableWidgetRow in self.tableWidgetServerDirectory.selectionModel().selectedRows():
				if currentQTableWidgetRow.row()!=0:
					filename = self.tableWidgetServerDirectory.item(currentQTableWidgetRow.row(), 0).text()

					filePermissions = self.tableWidgetServerDirectory.item(currentQTableWidgetRow.row(), 3).text()
					
					if filePermissions.find('x') is -1:
						temp = self.pathSelectedItem.rsplit('/')
						currentDirectory = temp[0]
						self.saveFileInDirectory = str(QtWidgets.QFileDialog.getExistingDirectory(None, "Save File In Directory", currentDirectory,\
						QtWidgets.QFileDialog.ShowDirsOnly))
						
						# Download and save the file:
						self.labelDownloadStatus.setText('Downloading...')
						self.ftpClient.download(filename, self.saveFileInDirectory)
						self.labelDownloadStatus.setText('Download complete.')
					else:
						self.changeWorkingDirectoryClicked(filename)

		except:
			# Download failed:
			self.labelDownloadStatus.setText('Download failed.')
#------------------- END INTERFACE-------------------------

class clientProtocolInterpreter():
	def __init__(self, bufferSize=8192):
		# Port number being used for TCP Control Connection socket:
		self.tcpControlConnectionPort = 21
		self.bufferSize = bufferSize
		self.listInDirectory = []
		self.rootDirectory = ''
	def initializeFTPConnection(self, serverName):
		'''
			initializeFTPConnection creates the TCP control connection
			socket required for the FTP Client to send commands to the 
			FTP Server.	Socket is binded the specified serverName.
		'''
		
		# Server Address where server listens for TCP connection:
		serverAddress = (serverName,self.tcpControlConnectionPort)
		self.serverAddress = serverAddress
		print('Connecting to {} port {}'.format(*serverAddress))

		# Create Client TCP socket:
		self.tcpControlSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		
		# Connect to the client socket to the port where the server is listening:
		self.tcpControlSocket.connect(serverAddress)
		
		# Print Server Response after connecting:
		print(self.tcpControlSocket.recv(self.bufferSize).decode())
		print("===========================================")
		
		return self.tcpControlSocket 
	#
	#------------------------------------------------------------	
	def doLogin(self, username='', password=''):
		'''
			doLogin logs onto the FTP Server with the specified username 
			and password of the client. The commands are sent through the 
			TCP control connection socket.
			
			param username
			param password
		'''
		
		self.sendCommand('USER', username)
		self.getServerResponse()
		
		# Send password:
		self.sendCommand('PASS', password)
		self.getServerResponse()
		
		# Start at Parent Working Directory:
		self.changeToParentDirectory()
		# Obtain current working directory:
		self.rootDirectory = self.printWorkingDirectory()
	#------------------------------------------------------------	
	def sendCommand(self, command="NOOP", message=""):
		'''
			sendCommand sends a specified command and message, if any, to the FTP server.
			Default command send is NOOP.
			
			param command
			param message
		'''
		self.tcpControlSocket.sendall((command+' '+message+'\r\n').encode())	

	#------------------------------------------------------------			
	def getServerResponse(self):
		'''
			getServerResponse retrieves the response message from the FTP server 
			after a command was sent by the client.
		'''
		
		receivedMessage = self.tcpControlSocket.recv(self.bufferSize).decode("UTF-8").rstrip()
		print(receivedMessage)
		# Split response at first space:
		responseCode, message = receivedMessage.split(" ",1)	
		
		return responseCode, message
		
	#------------------------------------------------------------
	def doLogout(self):
		'''
			doLogout is responsible for sending the Logout command
			QUIT to the FTP server.
		'''
		self.sendCommand('QUIT')
		self.getServerResponse()
	
	#------------------------------------------------------------
	def changeToRootDirectory(self):
		'''
			changeToRootDirectory changes the working directory on the 
			FTP Server to the Root Directory.
		'''
		self.changeWorkingDirectory(self.rootDirectory)
	
	#------------------------------------------------------------
	def changeToParentDirectory(self):
		'''
			changeToParentDirectory changes the working directory on the FTP Server
			to the Parent Directory.
		'''
		self.sendCommand('CDUP')
		self.getServerResponse()
		
	#------------------------------------------------------------
	def printWorkingDirectory(self):
		'''
			printWorkingDirectory sends the FTP PWD command and will display
			the current directory in focus on the FTP Server.
		'''
		# Obtain current working directory:
		self.sendCommand('PWD')
		response = self.getServerResponse()
		self.activeDirectory = response[1]
		
		indexFirstElement 	   = response[1].find('"')
		indexLastElement  	   = response[1].rfind('"')
	
		if indexFirstElement!=-1 and indexLastElement!=-1:
			self.activeDirectory   = self.activeDirectory[indexFirstElement+1:indexLastElement]
		
		return self.activeDirectory
	#------------------------------------------------------------
	def changeWorkingDirectory(self, newPathName):
		'''
			changeWorkingDirectory implements the CWD FTP command.
			
			The client will change the current working directory and the function will then
			request a new list of the items in the new directory.
		'''
		# Get current directory:
		currentDirectory = self.printWorkingDirectory()
		if currentDirectory!=self.rootDirectory:
			newPathName = os.path.join(currentDirectory, newPathName)
		
		# Change working directory:
		self.sendCommand('CWD', newPathName)
		self.getServerResponse()
		
	#------------------------------------------------------------
	def makeWorkingDirectory(self, newDirectoryName):
		'''
			makeWorkingDirectory implements the MKD FTP command.
			
			The client will create a new directory in the current working directory and
			the function will then request a new list of the items in the updated directory.
		'''
		# Get current directory:
		currentDirectory = self.printWorkingDirectory()
		newDirectoryName = os.path.join(currentDirectory, newDirectoryName)
		print(newDirectoryName)
		# Make the directory:
		self.sendCommand('MKD', newDirectoryName)
		self.getServerResponse()
		
	#------------------------------------------------------------
	def deleteDirectory(self, directoryName):
		'''
			deleteDirectory implements the DELE FTP command.
			
			The client will delete a directory in the current working directory and the function
			will then request an updated list of the items in the directory.
		'''
		# Get current directory:
		currentDirectory = self.printWorkingDirectory()
		directoryName = os.path.join(currentDirectory, directoryName)
		
		self.sendCommand('DELE', directoryName)
		self.getServerResponse()
		
	#------------------------------------------------------------
	def modifyListDetails(self, dataList):
		'''
			modifyListDetails 
		'''
		filePermission = 0
		filenameIndex  = 8
		fileSizeIndex  = 4
		fileLastModifiedIndexFirst = 5
		fileLastModifiedIndexLast  = 8
		
		# Split into columns:
		temp = dataList.split()
		
		tempList = [' '.join(temp[filenameIndex:]),' '.join(temp[fileSizeIndex:fileSizeIndex+1]),\
		' '.join(temp[fileLastModifiedIndexFirst:fileLastModifiedIndexLast]),\
		' '.join(temp[filePermission:filePermission+1])]
		tempList = list(filter(None, tempList))
		
		self.listInDirectory.append(tempList)
	
	#------------------------------------------------------------
	def listFilesInWorkingDirectory(self, clientDTP, pathName=""):
		'''
			listFilesInWorkingDirectory is responsible for retrieving the 
			list of files in the specified pathName.
			
			It returns the list sent by the server over the data connection socket.
		'''
		# Obtain current working directory:
		#activeDirectory = printWorkingDirectory(tcpControlSocket)
		print("============= GETTING LIST ================")
		dataConnectionSocket = clientDTP.createPassiveConnection(self)
		
		self.sendCommand('LIST', pathName)
		response = self.getServerResponse()

		dataList = dataConnectionSocket.recv(self.bufferSize).decode().rstrip()
		print("Receiving List of Directory "+pathName+" ...")
		self.listInDirectory = []
		while dataList:
			
			tempDataList = dataList.split('\r')
			for item in tempDataList:
				item = item.strip().rstrip()
				self.modifyListDetails(item)
			dataList = dataConnectionSocket.recv(self.bufferSize).decode().rstrip()

		dataConnectionSocket.close()
		
		# Print Server Response after download completion:
		response = self.getServerResponse()
		
		return self.listInDirectory
	
	#------------------------------------------------------------	
	
	def getFileSize(self, filename):
		'''
			getFileSize implements FTP SIZE command.
			param tcpControlSocket
			param filename
			return file size in bytes and in megabytes
		'''
		self.sendCommand('SIZE', filename)
		response  = self.getServerResponse()
		
		# Response is in bytes:
		fileSize  = float(response[1])
		mbSize    = 1048576
		fileSizeInMbv = 0
		# Convert to megabytes when file is larger than a megabyte
		if fileSize >= mbSize:
			fileSizeInMb = fileSize/mbSize
		return fileSize, fileSizeInMb

#------------------------------------------------------------

class clientDataTransferProcess():
	def __init__(self, bufferSize=8192):
		# Port number being used for TCP Data Connection socket:
		self.tcpDataConnectionPort = 20
		self.bufferSize = bufferSize
	#------------------------------------------------------------	
	def createPassiveConnection(self, clientPI):
		'''
			createPassiveConnection creates a Passive Data Connection (USER-DTP).
			Determines the address and port used on the FTP-Server for the SERVER-DTP
			connection.
		'''
		print("========== CREATE DATA SOCKET ============")
		# Determine port used for Data Connection Socket on Server Side:
		clientPI.sendCommand('PASV')
		response = clientPI.getServerResponse()
		
		if response[0]=="200" or response[0] == "227":
			#
			indexFirstBracket = response[1].find("(")
			indexLastBracket  = response[1].rfind(")")
			dataPortAddress   = response[1]
			
			# Copy IP Address and Port number:
			dataPortAddress   = dataPortAddress[indexFirstBracket+1:indexLastBracket]
			
			# Split into IP address and use other numbers to calculate the data port:
			serverAddress     = dataPortAddress.split(",")
			tempServerName    = serverAddress[0:4]
			
			temp = ""
			for i in range(len(tempServerName)-1):
				temp = temp+tempServerName[i]+'.'
			
			# ServerName should now contain FTP server's IP Address:
			serverName = temp+tempServerName[-1]
			
			# Determine port being used using formula [0]*256+[1]:
			tempServerDataPort = serverAddress[4:]
			serverTCPDataPort  = int((int(tempServerDataPort[0]) * 256) + int(tempServerDataPort[1]))
		else: # Use default port:
			serverTCPDataPort = self.tcpDataConnectionPort
			temp = clientPI.tcpControlSocket.getpeername() # Returns server name and port binded to socket 
			serverName = str(temp[0])
		# Create Client Data Transmission Socket:
		# Server Address where server listens for TCP connection:
		self.serverDataTransmissionAddress = (serverName,serverTCPDataPort)
		print('Connecting to {} port {}'.format(*self.serverDataTransmissionAddress))

		# Create Client TCP Data socket:
		self.dataConnectionSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

		# Connect to the client socket to the port where the server is listening:
		self.dataConnectionSocket.connect(self.serverDataTransmissionAddress)
		
		print("========== DATA SOCKET CREATED ===========")
		
		return self.dataConnectionSocket	
	#------------------------------------------------------------	
	def determineServerFileSeparator(self, pathName):
		'''
			determineServerFileSeparator obtains the file path separator used by 
			the FTP Server.
		'''
		temp = r'\\\\'
		pathName = pathName.replace(r'\\', temp)
		indexFilePathSep = pathName.find('/')
		if indexFilePathSep==-1:
			filesep = r'\\'
		else:
			filesep = r'/'
		return filesep, pathName
	
	#------------------------------------------------------------	
	def download(self, clientPI, file, outputPath):
		'''
			download is responsible for the retrieval of a file from the server.
			The PWD command is used to obtain the current directory of focus on the server.
			The TYPE command is sent. Upon a successful response from the command RETR the 
			file is download to the client and saved at a user specified output path.
		'''
		print("============ DOWNLOADING ===============")
		# Obtain current working directory:
		downloadPath = clientPI.printWorkingDirectory()
		
		# Get file path separator:
		filesep, downloadPath = self.determineServerFileSeparator(downloadPath)
		print(downloadPath)
		
		# Send :
		type = 'I'
	
		clientPI.sendCommand('TYPE', type)
		response = clientPI.getServerResponse()
		
		# Data connection socket is opened to begin file transmission:
		self.createPassiveConnection(clientPI)
		
		# Download requested file:
		if downloadPath=='/':
			filesep = ''
		filename = downloadPath+filesep+file
		
		clientPI.sendCommand('RETR', filename)
		response = clientPI.getServerResponse()
		responseCode = response[1]

		# Create file path with file name to save file on disk:
		filesep ='/'
		filename = outputPath+filesep+file
		
		if type.upper()=='I':
			mode = 'wb'
		elif type.upper() == 'ASCII':
			mode = 'w'
			
		# Write file to file path:
		try:
			downloadedData = self.dataConnectionSocket.recv(self.bufferSize)

			with open(filename, mode) as currentDownload:
				print("Downloading...")
				while downloadedData:
					currentDownload.write(downloadedData)
					downloadedData = self.dataConnectionSocket.recv(self.bufferSize)
				
				# Close the file:
				currentDownload.close()
				
			
			# Done downloading:
			print('Downloading Complete')
			
			# close data connection socket:
			self.dataConnectionSocket.close()
			
			# Print Server Response after download completion:
			response = clientPI.getServerResponse()
			print("========= DOWNLOADING DONE ============")
		except:
			print('Connection closed. Failed to download.')
			# close data connection socket:
			self.dataConnectionSocket.close()
			response = clientPI.getServerResponse()
	#------------------------------------------------------------
	def upload(self, clientPI, file, currentDirectory=""):
		'''
			upload is responsible for uploading a selected file
			to the server through the data connection socket.
			
			It first obtains the current directory of focus on the server
			and then sends the TYPE command. After a successful response
			the STOR command is sent and the selected file is uploaded.
		'''
		print("============== UPLOADING ==================")
		# Obtain current working directory:
		uploadPath = clientPI.printWorkingDirectory()
		
		# Check file path separator:
		filesep, uploadPath = self.determineServerFileSeparator(uploadPath)
		print(uploadPath)
		
		# Send  
		type = 'I'  # Binary 
		clientPI.sendCommand('TYPE', type)
		response = clientPI.getServerResponse()
		
		# Data connection socket is opened to begin file transmission:
		self.createPassiveConnection(clientPI)
		
		# Create filename:
		if uploadPath=='/':
			filesep = ''
		filename = uploadPath+filesep+file
		print(filename)
		print("I want to upload {}".format(filename))
		
		# Upload selected file:
		clientPI.sendCommand('STOR', filename)
		response = clientPI.getServerResponse()
		
		# Upload file:
		indexFilePathSep = currentDirectory.find('\\\\')
		if indexFilePathSep==-1:
			temp = currentDirectory.find('\\')
			if temp==-1:
				currentDirectory = currentDirectory.replace("\\","/")
				currentDirectory = currentDirectory.replace('"','')
		else:
			currentDirectory = currentDirectory.replace("\\\\","/")
		
		filesep = r'/'
		filename = [r'',currentDirectory, filesep, file]
		filename = ''.join(filename)
		filename = os.path.normpath(filename)
		
		if type.upper()=='I':
			mode = 'rb'
		elif type.upper() == 'ASCII':
			mode = 'r'
			
		# Read selected file:
		try:
			with open(filename, mode) as currentUpload:
				uploadedData = currentUpload.read(self.bufferSize)
				print("Uploading file...")
				while uploadedData:
					self.dataConnectionSocket.send(uploadedData)
					uploadedData = currentUpload.read(self.bufferSize)
				# Close the file:
				currentUpload.close()
			# Done uploading:
			print("Done Uploading {}!".format(file))
			
			# Close Data Connection Socket:
			self.dataConnectionSocket.close()

			# Get FTP Server Response:
			response = clientPI.getServerResponse()
			print("============ UPLOADING DONE ===============")
		except:
			print("Connection closed. Failed to upload.")
			self.dataConnectionSocket.close()
			
			# Get FTP Server Response:
			clientPI.getServerResponse()
#------------------------------------------------------------
class FTPClient():
	def __init__(self, bufferSize=8192):
		self.clientPI  = clientProtocolInterpreter(bufferSize)
		self.clientDTP = clientDataTransferProcess(bufferSize)
	
	def login(self, hostname, username='', password=''):
		self.clientPI.initializeFTPConnection(hostname)
		self.clientPI.doLogin(username, password)
	
	def changeToRootDirectory(self):
		'''
			changeToRootDirectory tell the Client PI to change to 
			the Root Directory.
		'''
		self.clientPI.changeToRootDirectory()
	
	def changeToParentDirectory(self):
		'''
			changeToParentDirectory will tell the Client PI to change to 
			the Parent Directory.
		'''
		self.clientPI.changeToParentDirectory()
	
	def changeWorkingDirectory(self, pathName):
		'''
			changeWorkingDirectory will tell the Client PI to change the 
			working directory on the FTP Server to a specified path.
			
			param pathName
		'''
		self.clientPI.changeWorkingDirectory(pathName)
	
	def deleteDirectory(self, directoryName):
		'''
			deleteDirectory will tell the Client PI to delete a specified 
			directory on the FTP Server.
			
			param directoryName
		'''
		self.clientPI.deleteDirectory(directoryName)
	
	def createDirectory(self, newDirectoryName):
		'''
			createDirectory will tell the Client PI to make a new directory 
			on the FTP Server.
			
			param newDirectoryName
		'''
		self.clientPI.makeWorkingDirectory(newDirectoryName)
	
	def upload(self, file, currentDirectory):
		'''
			upload will call Client DTP to open a Passive Data Connection 
			to upload the requested file and save it in the specified path
			on the FTP Server.
			
			param file
			param currentDirectory
		'''
		self.clientDTP.upload(self.clientPI, file, currentDirectory)
		
	def download(self, file, outputPath):
		'''
			download will call the Client DTP to open a Passive Data Connection 
			to download the requested file and save it in the specified path.
			
			param file
			param outputPath
		'''
		self.clientDTP.download(self.clientPI, file, outputPath)
		
	def updateDirectoryList(self):
		'''
			updateDirectoryList will request for the items in current working directory
			on the server.
		'''
		# call
		directory   = self.clientPI.printWorkingDirectory()
		listOfFiles = self.clientPI.listFilesInWorkingDirectory(self.clientDTP, directory)
		
		self.listOfFiles = listOfFiles
		return self.listOfFiles
		
	def logout(self):
		'''
			logout will log out the user from the FTP Server.
		'''
		self.clientPI.doLogout()
	#------------------------------------------------------------
	def terminateConnection(self):
		'''
			terminateConnection closes the sockets being used but logs the 
			user out first.
		'''
		self.clientPI.doLogout()
		
		try:
			self.clientPI.tcpControlSocket.close()
			self.clientDTP.dataConnectionSocket.close()
			print("All connections have been closed.")
		except:
			print("Termination unsuccessful.")
#------------------------------------------------------------
'''
def main():
	# Server Name:
	hostServerName = 'ELEN4017.ug.eie.wits.ac.za'
	#hostServerName = 'localhost'
	hostServerName = 'speedtest.tele2.net'
	
	#hostServerName = 'SEREPONG-PC'
	print("============== INITIALIZE ===============")
	#tcpControlSocket = initializeFTPConnection(hostServerName)
	#print(" {} port {}".format(*tcpControlSocket.getpeername()))
	
	# Login:
	username = 'group6'
	username = 'anonymous'
	password = 'reiph9Ju'
	
	#doLogin(tcpControlSocket, username, password)
	ftpClient = FTPClient(10240)
	ftpClient.login(hostServerName, username)
	#ftpClient.login(hostServerName, username, password)
	
	# Change directory:
	#ftpClient.changeWorkingDirectory('/Project/files')
	#ftpClient.changeWorkingDirectory('/upload')
	#ftpClient.updateDirectoryList()
	#changeWorkingDirectory(tcpControlSocket, '/files')
	
	# Obtain Data connection port used by the server:
	#dataConnectionSocket = createPassiveConnection(tcpControlSocket)
	
	# Upload file:
	#currentDirectory = r'C:Users\Lynch-Stephen\Documents\Lecture Notes\4th year\ELEN4017A\Project'
	currentDirectory = r'C:/Users/Lynch-Stephen/Documents/Lecture Notes/4th year/ELEN4017A/Project'
	#file = 'test video2.mp4'
	file = '22KB.zip'
	#ftpClient.upload(file, currentDirectory)
	#listFilesInWorkingDirectory(tcpControlSocket)
	
	# Download file:
	saveFileInDirectory = r'C:/Users/Lynch-Stephen/Documents/Lecture Notes/4th year/ELEN4017A/Project/temp'
	file = 'rfc959.pdf'
	#download(tcpControlSocket, file, saveFileInDirectory)
	
	
	# Terminate the connection:
	#doLogout(tcpControlSocket)
	#ftpClient.logout()
	#terminateConnection(tcpControlSocket, dataConnectionSocket)
'''
if __name__ == '__main__':
	#main()

	app = QtWidgets.QApplication(sys.argv)
	ftpClientUIMain = QtWidgets.QMainWindow()
	ftpClient = FTPClient(10240)
	prog = clientInterface(ftpClientUIMain, ftpClient)
	ftpClientUIMain.show()
	sys.exit(app.exec_())
	
