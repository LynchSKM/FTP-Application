import socket
import threading
import sys
import os
import time
import traceback

from PyQt5 import QtCore, QtGui, QtWidgets  #QDir, Qt
from clientUI import Ui_clientUIMain

commandLock  = threading.Lock()
BUSYFILES = []
#----------------------------------------------------------
class workerThreadSignals(QtCore.QObject):
    '''
    Defines the signals available from a running worker thread.

    The supported signals are:

    finished
        No data

    error
        `tuple` (exctype, value, traceback.format_exc() )
		
    progress
        No data but will read the progress value from global list BUSYFILES for
		the file download or upload:

    '''
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(tuple)
    fileProgress = QtCore.pyqtSignal()
	
class workerThread(QtCore.QRunnable):
    '''
    workerThread Worker thread

    Inherits from QtCore.QRunnable to handle worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(workerThread, self).__init__()

        # Store the constructor arguments will be used later for processing:
        self.functionToProcess = fn
        self.args = args
        
        self.signals = workerThreadSignals()
		# Add the callback to our key word arguments (kwargs):
        kwargs['progress_callback'] = self.signals.fileProgress
        self.kwargs = kwargs

    @QtCore.pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''
		# Try to perform the operation:
        try:
            self.functionToProcess(*self.args, **self.kwargs)
        except:
			# If an exception is raised it will trace back to where the error occurred
			# and call the function connection to the error emit worker signal.
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
			# The thread will emit the signal that it is complete.
            self.signals.finished.emit()  # Complete
			
#---------------------- INTERFACE -------------------------
class clientInterface(Ui_clientUIMain):
	def __init__(self, ftpClientUIMain, ftpClient):
		Ui_clientUIMain.__init__(self)
		self.setupUi(ftpClientUIMain)
		self.ftpClient = ftpClient
		
		self.pushButtonLogout.setEnabled(False)
		
		self.progressBarUpload.hide()
		self.progressBarDownload.hide()
		self.threadpool = QtCore.QThreadPool()
		#==================== Tree View (Model based) ==============================
		# Set up tree view for client directory:
		self.clientDirectoryModel = QtWidgets.QFileSystemModel()
		
		# You can setRootPath to any path.
		self.clientDirectoryModel.setRootPath(QtCore.QDir.rootPath())
		#self.treeViewClientDirectory = QtWidgets.QTreeView()
		self.treeViewClientDirectory.setModel(self.clientDirectoryModel)
		self.treeViewClientDirectory.setRootIndex(self.clientDirectoryModel.setRootPath(QtCore.QDir.rootPath()))
		self.pathSelectedItem = QtCore.QDir.rootPath()
		self.treeViewClientDirectory.header().resizeSection(0, 300)
		#====================== End Tree View ========================
		
		
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
		# exit action
		self.action_Exit.toggled.connect(self.actionExitApp)
		self.action_Exit.triggered.connect(self.actionExitApp)
		self.action_Exit_2.toggled.connect(self.actionExitApp)
		self.action_Exit_2.triggered.connect(self.actionExitApp)
	
		#==============================================================
	def loginSuccessful(self):
		'''
		loginSuccessful Will be called when a loginWorkerThread has successfully finished.
		'''
		try:
			self.pushButtonRootDirectoryClicked()
			self.pushButtonLogout.setEnabled(True)
			
			self.labelStatus.setText('Login successful.')
			self.treeViewClientDirectory.setEnabled(True)
		except:
			pass
	def loginFailed(self):
		'''
		loginFailed will be called if the loginWorkerThread could not successfully be executed.
		'''
		self.labelStatus.setText('Login failed.')
		
	def pushButtonLoginClicked(self):
		'''
		pushButtonLoginClicked is the code executed when the Login button is clicked.
		The ftpClient.login() function is threaded here to avoid the lock up of the GUI.
		'''
		hostServerName = self.lineEditHostName.text()
		username 	   = self.lineEditUsername.text()
		password	   = self.lineEditPassword.text()
		self.labelStatus.setText('Not Logged into any server.')
		# Login:
		#hostServerName = 'ELEN4017.ug.eie.wits.ac.za'
		#username = 'group6'
		#password = 'reiph9Ju'
		try:
			
			loginWorker = workerThread(self.ftpClient.login, hostServerName, username, password)
			loginWorker.signals.finished.connect(self.loginSuccessful)
			loginWorker.signals.error.connect(self.loginFailed)
			self.threadpool.start(loginWorker)
		except:
			pass
			
	def pushButtonLogoutClicked(self):
		'''
		pushButtonLogoutClicked is the code executed when the Logout button is clicked.
		The ftpClient.logout() function is called here. This operation will only occur 
		if there are no files being uploaded or downloaded.
		'''
		# Logout:
		try:
			if not BUSYFILES:
				self.ftpClient.logout()
				self.pushButtonLogout.setEnabled(False)
				self.tableWidgetServerDirectory.setRowCount(0) 
				self.labelStatus.setText('Logout successful.')
			else:
				self.labelStatus.setText('Cannot Logout. Busy '+BUSYFILES[0][1])
		except:
			self.labelStatus.setText('Logout unsuccessful.')
	
	def updateServerDirectoryWidget(self, listOfFilesInDirectory):
		'''
		updateServerDirectoryWidget update the tableWidgetServerDirectory with the 
		list found in listOfFilesInDirectory.
		:param listOfFilesInDirectory 
			Is a list of lists which contains the file permissions, size, date modified, and filename
		'''
		try:
			self.tableWidgetServerDirectory.setRowCount(0)
			
			# set column count
			self.tableWidgetServerDirectory.setColumnCount(4)
			
			# Set Row Count:
			self.tableWidgetServerDirectory.setRowCount(len(listOfFilesInDirectory)+1)
			# Default:
			self.tableWidgetServerDirectory.setItem(0,0, QtWidgets.QTableWidgetItem(".."))
			self.tableWidgetServerDirectory.setColumnWidth(0, 230)
			
			row = 1
			col = 0
			for item in listOfFilesInDirectory:
				for fileProperty in item:
					fileTypeIco = None
					if col==0:
						if item[3].find('x') is -1:
							tempFilename = fileProperty.lower()
							if tempFilename.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
								fileTypeIco = "assets/image.ico"
							elif tempFilename.endswith(('.mp4', '.wmv', '.mkv', '.avi')):
								fileTypeIco = "assets/video.ico"
							else:
								fileTypeIco = "assets/file.ico"
						else:
							fileTypeIco = "assets/folder.ico"
					
					tempItem = QtWidgets.QTableWidgetItem(QtGui.QIcon(QtGui.QPixmap(fileTypeIco)), fileProperty)
					self.tableWidgetServerDirectory.setItem(row,col, tempItem)
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
		'''
		parentDirectoryClicked calls the ftpClient.changeToParentDirectory() which 
		calls the Client PI's implementation of FTP command CDUP. The tableWidgetServerDirectory 
		is also updated if the operation is successful. This process will only occur if there 
		are no files being uploaded or downloaded.
		'''
		try:
			if not BUSYFILES:
				self.ftpClient.changeToParentDirectory()
				updatedList = self.ftpClient.updateDirectoryList()
				self.updateServerDirectoryWidget(updatedList)
				self.labelStatus.setText('Directory successfully changed to Parent Directory!')
			else:
				self.labelStatus.setText('Cannot change to parent directory. Busy '+BUSYFILES[0][1])
		except:
			self.labelStatus.setText('Unable to change to Parent Directory!')
	
	def pushButtonRootDirectoryClicked(self):
		'''
		pushButtonRootDirectoryClicked calls ftpClient.changeToRootDirectory(). The Client PI 
		will send CDUP HOME to the server. The tableWidgetServerDirectory is also updated if the 
		operation is successful. This operation will only occur if there are no files being uploaded or downloaded.
		'''
		try:
			if not BUSYFILES:
				self.ftpClient.changeToRootDirectory()
				
				updatedList = self.ftpClient.updateDirectoryList()
				self.updateServerDirectoryWidget(updatedList)
				
				self.labelStatus.setText('Directory successfully changed to Root Directory!')
			else:
				self.labelStatus.setText('Cannot change to root directory. Busy '+BUSYFILES[0][1])
		except:
			self.labelStatus.setText('Unable to change to Root Directory!')
	
	def changeWorkingDirectoryClicked(self, pathName):
		'''
		changeWorkingDirectoryClicked calls the ftpClient.changeWorkingDirectory() which 
		calls the Client PI's implementation of FTP command CWD. The tableWidgetServerDirectory 
		is also updated if the operation is successful. This process will only occur if there 
		are no files being uploaded or downloaded.
		
		:param pathName
		'''
		try:
			if not BUSYFILES:
				self.ftpClient.changeWorkingDirectory(pathName)
				
				updatedList = self.ftpClient.updateDirectoryList()
				self.updateServerDirectoryWidget(updatedList)
				
				self.labelStatus.setText('Directory successfully changed!')
			else:
				self.labelStatus.setText('Cannot delete. Busy '+BUSYFILES[0][1])
		except:
			self.labelStatus.setText('Unable to change Directory!')
	
	def pushButtonCreateDirectoryClicked(self):
		'''
		pushButtonCreateDirectoryClicked calls the ftpClient.createDirectory() which 
		calls the Client PI's implementation of FTP command MKD. The tableWidgetServerDirectory 
		is also updated if the operation is successful. This process will only occur if there 
		are no files being uploaded or downloaded.
		'''
		try:
			if not BUSYFILES:
				folderName = self.lineEditNewDirectory.text()
				if folderName!='':
					self.ftpClient.createDirectory(folderName)
					
					updatedList = self.ftpClient.updateDirectoryList()
					self.updateServerDirectoryWidget(updatedList)
					
					self.labelStatus.setText('New directory created!')
			else:
				self.labelStatus.setText('Cannot create directory. Busy '+BUSYFILES[0][1])
		except:
			self.labelStatus.setText('Unable to create directory!')
	
	
	def pushButtonDeleteDirectoryClicked(self):
		'''
		pushButtonDeleteDirectoryClicked calls the ftpClient.deleteDirectory() which 
		calls the Client PI's implementation of FTP command DELE and in future. The tableWidgetServerDirectory 
		is also updated if the operation is successful. This process will only occur if there 
		are no files being uploaded or downloaded.
		'''
		try:
			if not BUSYFILES:
				for currentQTableWidgetRow in self.tableWidgetServerDirectory.selectionModel().selectedRows():
					if currentQTableWidgetRow.row()!=0:
						filename = self.tableWidgetServerDirectory.item(currentQTableWidgetRow.row(), 0).text()
						self.ftpClient.deleteDirectory(filename)
						
				updatedList = self.ftpClient.updateDirectoryList()
				self.updateServerDirectoryWidget(updatedList)
			else:
				self.labelStatus.setText('Cannot delete. Busy '+BUSYFILES[0][1])
			
		except:
			self.labelStatus.setText('Unable to delete directory!')
	
	def treeViewClientDirectoryClicked(self, signal):
		'''
		treeViewClientDirectoryClicked update the member self.pathSelectedItem which 
		will contain the selected file from the TreeView Widgets.
		:param signal is the PyQt signal send whenever the treeView is clicked.
		'''
		self.pathSelectedItem = self.treeViewClientDirectory.model().filePath(signal)
		
		print(self.pathSelectedItem)
		
	def pushButtonUploadClicked(self):
		'''
		pushButtonUploadClicked will initiate a thread for ftpClient.upload() function.
		If it cannot upload an error message is displayed on a label on the GUI.
		'''
		try:
			# Check if selected item is not a folder:
			fileUpload = self.pathSelectedItem
			
			# Pass the download for execution;
			uploadWorker = workerThread(self.ftpClient.upload, fileUpload)
			uploadWorker.signals.finished.connect(self.uploadDownloadthreadComplete)
			uploadWorker.signals.error.connect(self.uploadFailed)
			uploadWorker.signals.fileProgress.connect(self.updateProgressBars)
			
			# Execute thread:
			self.threadpool.start(uploadWorker)
		except:
			self.labelUploadStatus.setText('Upload failed.')
	
	def getSelectedItem(self):
		'''
		getSelectedItem will determine which file or folder on the User has selected on 
		the tableWidgetServerDirectory. It will call parentDirectoryClicked if a folder is double clicked 
		and it will call pushButtonDownloadClicked if a file is double clicked.
		'''
		#try:
		for currentQTableWidgetRow in self.tableWidgetServerDirectory.selectionModel().selectedRows():

			if currentQTableWidgetRow.row()!=0:
				filePermissions = self.tableWidgetServerDirectory.item(currentQTableWidgetRow.row(), 3).text()
				if filePermissions.find('x') is -1:
					self.pushButtonDownloadClicked()
				else:
					self.changeWorkingDirectoryClicked(self.tableWidgetServerDirectory.item(currentQTableWidgetRow.row(), 0).text())
			else:
				self.parentDirectoryClicked()
		#except:
			#self.labelDownloadStatus.setText('Cannot select file/folder.')
	
	def pushButtonDownloadClicked(self):
		'''
		pushButtonDownloadClicked will thread the ftpClient.download function. It will obtain the 
		selected item on the tableWidgetServerDirectory. File downloads are only supported thus any folder 
		requests will be ignored.
		'''
		try:
			
			# Check selected table item:
			for currentQTableWidgetRow in self.tableWidgetServerDirectory.selectionModel().selectedRows():
				if currentQTableWidgetRow.row()!=0:
					filename = self.tableWidgetServerDirectory.item(currentQTableWidgetRow.row(), 0).text()

					temp = self.pathSelectedItem.rsplit('/')
					currentDirectory = temp[0]
					try:
						self.saveFileInDirectory = str(QtWidgets.QFileDialog.getExistingDirectory(None, "Save File In Directory", currentDirectory,\
						QtWidgets.QFileDialog.ShowDirsOnly))
						
						# Download and save the file:
						# Pass the download for execution;
						downloadWorker = workerThread(self.ftpClient.download, filename, self.saveFileInDirectory)
						
						# Create signals that will be used to indicate certain events that occur in the thread:
						downloadWorker.signals.finished.connect(self.uploadDownloadthreadComplete)
						downloadWorker.signals.error.connect(self.downloadFailed)
						downloadWorker.signals.fileProgress.connect(self.updateProgressBars)
						# Execute thread:
						self.threadpool.start(downloadWorker)
					except:
						self.ftpClient.checkServerStatus()
						self.tableWidgetServerDirectory.setEnabled(True)

		except:
			# Download failed:
			self.ftpClient.checkServerStatus()
			
	def uploadDownloadthreadComplete(self):
		'''
		uploadDownloadthreadComplete is called when ever a workerThread signals it is complete.
		It hides the progress bars.
		'''
		self.updateServerDirectoryWidget(self.ftpClient.listOfFiles)
		
		self.progressBarUpload.hide()
		self.labelDownloadStatus.setText('')
		self.labelUploadStatus.setText('')
		self.progressBarDownload.hide()
		self.tableWidgetServerDirectory.setEnabled(True)
	def updateProgressBars(self):
		'''
		updateProgressBars will update the value of the progress bar for the current 
		operation in BUSYFILES list, while a file uploads or downloads.
		'''
		if BUSYFILES[0][1].upper()=='DOWNLOADING':
			self.progressBarDownload.show()
			self.labelDownloadStatus.setText('Downloading '+BUSYFILES[0][0])
			self.progressBarDownload.setValue(BUSYFILES[0][2])
		else:
			self.progressBarUpload.show()
			self.labelUploadStatus.setText('Uploading '+BUSYFILES[0][0])
			self.progressBarUpload.setValue(BUSYFILES[0][2])
	def downloadFailed(self):
		self.labelStatus.setText('Download failed.')
	
	def uploadFailed(self):
		self.labelStatus.setText('Upload failed.')
	def actionExitApp(self):
		try:
			
			self.terminateConnection()
		except:
			pass
	def terminateConnection(self):
		try:
			self.ftpClient.terminateConnection()
			self.labelStatus.setText('Disconnected from Server.')
		except:
			self.labelStatus.setText('Disconnect failed.')

#------------------- END INTERFACE-------------------------
	
class clientProtocolInterpreter():
	def __init__(self, bufferSize=8192):
		# Port number being used for TCP Control Connection socket:
		self.tcpControlConnectionPort = 21
		self.bufferSize = bufferSize
		self.listOfFiles = []
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
		try:
			#
			#self.tcpControlSocket.settimeout(5)
			self.tcpControlSocket.connect(serverAddress)
			
			# Print Server Response after connecting:
			print(self.tcpControlSocket.recv(self.bufferSize).decode())
			print("===========================================")
		except:
			pass
		
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
		response = self.getServerResponse()
		responseCode = response[0]
		
		tempErrorCodes = ['530', '500', '501', '421']
		if responseCode not in tempErrorCodes:
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
	def changeToRootDirectory(self, filesep):
		'''
			changeToRootDirectory changes the working directory on the 
			FTP Server to the Root Directory.
		'''
		print('The Root Directory: '+self.rootDirectory)
		self.changeWorkingDirectory(self.rootDirectory, filesep)
	
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
	def changeWorkingDirectory(self, newPathName, filesep):
		'''
			changeWorkingDirectory implements the CWD FTP command.
			
			The client will change the current working directory and the function will then
			request a new list of the items in the new directory.
		'''
		# Get current directory:
		currentDirectory = self.printWorkingDirectory()
		if newPathName!=self.rootDirectory:
		
			if currentDirectory!=self.rootDirectory:
				newPathName = currentDirectory+filesep+newPathName
				
		# Change working directory:
		self.sendCommand('CWD', newPathName)
		self.getServerResponse()
		
	#------------------------------------------------------------
	def makeWorkingDirectory(self, newDirectoryName, filesep):
		'''
			makeWorkingDirectory implements the MKD FTP command.
			
			The client will create a new directory in the current working directory and
			the function will then request a new list of the items in the updated directory.
		'''
		# Get current directory:
		currentDirectory = self.printWorkingDirectory()
		newDirectoryName = currentDirectory+filesep+newDirectoryName
		print(newDirectoryName)
		# Make the directory:
		self.sendCommand('MKD', newDirectoryName)
		self.getServerResponse()
		
	#------------------------------------------------------------
	def deleteDirectory(self, pathName, filesep):
		'''
			deleteDirectory implements the DELE FTP command.
			
			The client will delete a file in the current working directory and the function
			will then request an updated list of the items in the directory.
		'''
		# Get current directory:
		currentDirectory = self.printWorkingDirectory()
		pathName = currentDirectory+filesep+pathName
		print('Deleting... '+pathName)
		
		self.sendCommand('DELE', pathName)
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

		# Select file name:
		filename = ' '.join(temp[filenameIndex:])
		
		# Select file size:
		fileSize = float(' '.join(temp[fileSizeIndex:fileSizeIndex+1]))
		tempFileSize = self.processFileSize(fileSize)
		fileSize = str(tempFileSize[0])+' '+tempFileSize[1] 
	
		# Select last modified details:
		lastModified = ' '.join(temp[fileLastModifiedIndexFirst:fileLastModifiedIndexLast])
		
		# Select permissions:
		permissions = ' '.join(temp[filePermission:filePermission+1])
		
		# add to list:
		tempList = [filename, fileSize, lastModified, permissions]
		
		# Remove empty fields:
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
	def processFileSize(self, fileSize):
		# Response is in bytes:
		
		kbSize        = 1024
		mbSize        = kbSize**2
		newFileSize   = 0
		sizeType	  = 'Bytes'
		# Convert to megabytes when file is larger than a megabyte
		if fileSize < kbSize:
			newFileSize = fileSize
		elif fileSize >= kbSize and fileSize < mbSize:
			newFileSize = fileSize/kbSize
			sizeType    = 'KB'
		elif fileSize >= mbSize:
			newFileSize = fileSize/mbSize
			sizeType = 'MB'
		
		newFileSize = round(newFileSize,2)
		return newFileSize, sizeType
	
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
		fileSizeInBytes = 0
		fileSize  = 0
		# Response is in bytes:
		try:
			fileSizeInBytes  = float(response[1])
			fileSize  = self.processFileSize(fileSizeInBytes)
		except:
			fileSizeInBytes = 0
			fileSize  = 0
		
		return fileSizeInBytes, fileSize

#------------------------------------------------------------

class clientDataTransferProcess():
	def __init__(self, bufferSize=8192):
		# Port number being used for TCP Data Connection socket:
		self.tcpDataConnectionPort = 20
		self.bufferSize = bufferSize
		self.listOfFiles = []
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
		pathName = pathName.replace(temp, r'\\')
		indexFilePathSep = pathName.find('/')
		if indexFilePathSep==-1:
			filesep = r'\\'
		else:
			filesep = r'/'
		return filesep, pathName
	
	#------------------------------------------------------------	
	def download(self, clientPI, file, outputPath, progress_callback=None):
		'''
			download is responsible for the retrieval of a file from the server.
			The PWD command is used to obtain the current directory of focus on the server.
			The TYPE command is sent. Upon a successful response from the command RETR the 
			file is download to the client and saved at a user specified output path.
			:param clientPI
			:param file
			:param outputPath
		'''
		print("============ DOWNLOADING ===============")
		commandLock.acquire()
		#progressState = []
		fileInProcess = [file, 'DOWNLOADING', []]
		BUSYFILES.append(fileInProcess)
		
		# Obtain current working directory:
		downloadPath = clientPI.printWorkingDirectory()
		
		# Get file path separator:
		filesep, downloadPath = self.determineServerFileSeparator(downloadPath)
		print(downloadPath)
		
		# Download requested file:
		if downloadPath=='/' or downloadPath=='\\\\' or downloadPath=='\\':
			filesep = ''
		filename = downloadPath+filesep+file
		print(filename)
		# File Size:
		fileSize = clientPI.getFileSize(filename)
		print(fileSize[0])
		# Send :
		if file.lower().endswith(('.txt', '.cpp', '.c', '.py', '.m')):
			type = 'ASCII'
		else:
			type = 'I'
	
		clientPI.sendCommand('TYPE', type)
		response = clientPI.getServerResponse()
		
		# Data connection socket is opened to begin file transmission:
		self.createPassiveConnection(clientPI)
		
		clientPI.sendCommand('RETR', filename)
		response = clientPI.getServerResponse()
		responseCode = response[0]
		tempErrorCodes = ['450', '550', '500', '501', '421', '530']
		if responseCode not in tempErrorCodes:
			# Create file path with file name to save file on disk:
			filesep ='/'
			filename = outputPath+filesep+file
			
			if type.upper()=='I':
				mode = 'wb'
			elif type.upper() == 'ASCII':
				mode = 'w'
		
			# Write file to file path:
			try:
				BUSYFILES[0][2] = 0
				downloadedData  = self.dataConnectionSocket.recv(self.bufferSize)
				fileProgress    = self.bufferSize 
				with open(filename, mode) as currentDownload:
					print("Downloading...")
					while downloadedData:
						if fileSize[0]!=0:
							BUSYFILES[0][2] = (fileProgress/fileSize[0])*100
							if progress_callback!=None:
								progress_callback.emit()
						currentDownload.write(downloadedData)
						downloadedData = self.dataConnectionSocket.recv(self.bufferSize)
						fileProgress  = fileProgress+self.bufferSize 
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
				#print('Connection closed. Failed to download.')
				# close data connection socket:
				self.dataConnectionSocket.close()
				response = clientPI.getServerResponse()
			
		try:
			del BUSYFILES[:]
		except:
			pass
		
		# Update List:
		self.listOfFiles = clientPI.listFilesInWorkingDirectory(self)
		
		commandLock.release()
		return self.listOfFiles
	#------------------------------------------------------------
	def upload(self, clientPI, file, currentDirectory="", progress_callback=None):
		'''
			upload is responsible for uploading a selected file
			to the server through the data connection socket.
			
			It first obtains the current directory of focus on the server
			and then sends the TYPE command. After a successful response
			the STOR command is sent and the selected file is uploaded.
			
			:param clientPI
			:param file
			:param currentDirectory
		'''
		commandLock.acquire()
		print("============== UPLOADING ==================")
		# Obtain current working directory:
		uploadPath = clientPI.printWorkingDirectory()
		
		fileInProcess = [file, 'UPLOADING', []]
		BUSYFILES.append(fileInProcess)
		
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
		print("I want to upload {}".format(filename))
		
		# Upload selected file:
		clientPI.sendCommand('STOR', filename)
		response = clientPI.getServerResponse()
		responseCode = response[0]
		
		tempErrorCodes = ['532', '450', '452', '553', '500', '501', '421', '530']
		if responseCode not in tempErrorCodes:
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
				# Determine file size:
				fileSize     = os.path.getsize(filename)
				fileProgress = 0
				BUSYFILES[0][2] = 0
				
				# Begin reading from the file:
				with open(filename, mode) as currentUpload:
					uploadedData = currentUpload.read(self.bufferSize)
					print("Uploading file...")
					while uploadedData:
						BUSYFILES[0][2] = (fileProgress/fileSize)*100
						self.dataConnectionSocket.send(uploadedData)
						if progress_callback!=None:
							progress_callback.emit()
						uploadedData    = currentUpload.read(self.bufferSize)
						fileProgress    = fileProgress+self.bufferSize
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
			
		try:
			del BUSYFILES[:]
		except:
			pass
		# Update List:
		self.listOfFiles = clientPI.listFilesInWorkingDirectory(self)
		commandLock.release()
		return self.listOfFiles
#------------------------------------------------------------

class FTPClient():
	def __init__(self, bufferSize=8192):
		self.clientPI  = clientProtocolInterpreter(bufferSize)
		self.clientDTP = clientDataTransferProcess(bufferSize)
		self.listOfFiles = []
	def login(self, hostname, username='anonymous', password='', progress_callback=None):
		'''
		login will execute the Client PI initializeFTPConnection and if it is successful 
		it will try to login.
		:param hostname
		:param username
		:param password
		'''
		commandLock.acquire()
		try:
			self.clientPI.initializeFTPConnection(hostname)
			self.clientPI.doLogin(username, password)
		except:
			pass
		commandLock.release()	
	def changeToRootDirectory(self):
		'''
			changeToRootDirectory tell the Client PI to change to 
			the Root Directory.
		'''
		filesep = self.clientDTP.determineServerFileSeparator(self.clientPI.rootDirectory)
		self.clientPI.changeToRootDirectory(filesep[0])
	
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
			
			:param pathName
		'''
		filesep = self.clientDTP.determineServerFileSeparator(self.clientPI.rootDirectory)
		self.clientPI.changeWorkingDirectory(pathName,filesep[0])
	
	def deleteDirectory(self, directoryName):
		'''
			deleteDirectory will tell the Client PI to delete a specified 
			file on the FTP Server.
			
			:param directoryName
		'''
		
		filesep = self.clientDTP.determineServerFileSeparator(self.clientPI.rootDirectory)
		self.clientPI.deleteDirectory(directoryName, filesep[0])
	
	def createDirectory(self, newDirectoryName):
		'''
			createDirectory will tell the Client PI to make a new directory 
			on the FTP Server.
			
			:param newDirectoryName
		'''
		filesep = self.clientDTP.determineServerFileSeparator(self.clientPI.rootDirectory)
		self.clientPI.makeWorkingDirectory(newDirectoryName,filesep[0])
	
	def upload(self, fileUpload, progress_callback=None):
		'''
			upload will call Client DTP to open a Passive Data Connection 
			to upload the requested file and save it in the specified path
			on the FTP Server.
			
			:param file
			:param currentDirectory
		'''
		print(fileUpload)
		if not os.path.isdir(fileUpload) and os.path.exists(fileUpload):
			lastIndex = fileUpload.rfind('/')
			currentDirectory = fileUpload[0:lastIndex]
			print("Where to get file: "+currentDirectory)
			selectedFile = fileUpload[lastIndex+1:]
			print('The file selected: '+selectedFile)
			self.listOfFiles = self.clientDTP.upload(self.clientPI, selectedFile, currentDirectory, progress_callback)
		else:
			message = 'Cannot upload folders.'
			return message
		
	def download(self, file, outputPath, progress_callback=None):
		'''
			download will call the Client DTP to open a Passive Data Connection 
			to download the requested file and save it in the specified path.
			
			:param file
			:param outputPath
		'''
		# Search for file in list:
		tempList = self.listOfFiles
		fileFoundAtIndex = [(i, tempList.index(file))
		for i, tempList in enumerate(tempList)
		if file in tempList]
		
		# Obtain permissions:
		rowIndex = fileFoundAtIndex[0][0]
		filePermissions = self.listOfFiles[rowIndex][3]
		
		# If it's a folder it cannot be downloaded:
		if filePermissions.find('x') is -1:
			self.listOfFiles = self.clientDTP.download(self.clientPI, file, outputPath, progress_callback)
	
		
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
	
	def checkServerStatus(self):
		'''
		checkServerStatus will send the FTP NOOP command.
		'''
		self.clientPI.sendCommand()
		self.clientPI.getServerResponse()
		
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
	
