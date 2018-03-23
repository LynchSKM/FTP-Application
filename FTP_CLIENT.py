import socket
import threading
import sys
import os



def initializeFTPConnection(serverName):
	'''
		initializeFTPConnection creates the TCP control connection
		socket required for the FTP Client to send commands to the 
		FTP Server.	Socket is binded the specified serverName.
	'''
	# Port number being used for TCP Control Connection socket:
	tcpControlConnectionPort = 21
	
	# Server Address where server listens for TCP connection:
	serverAddress = (serverName,tcpControlConnectionPort)
	print('Connecting to {} port {}'.format(*serverAddress))

	# Create Client TCP socket:
	tcpControlSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

	# Connect to the client socket to the port where the server is listening:
	tcpControlSocket.connect(serverAddress)
	
	# Print Server Response after connecting:
	print(tcpControlSocket.recv(8192).decode())
	print("===========================================")
	
	return tcpControlSocket
	
#------------------------------------------------------------	
def doLogin(tcpControlSocket, username, password):
	'''
		doLogin logs onto the FTP Server with the specified username 
		and password of the client. The commands are sent through the 
		TCP control connection socket.
	'''
	sendCommand(tcpControlSocket, 'USER', username)
	getServerResponse(tcpControlSocket)
	
	# Send password:
	sendCommand(tcpControlSocket, 'PASS', password)
	getServerResponse(tcpControlSocket)
	
	# Start at Parent Working Directory:
	sendCommand(tcpControlSocket, 'CDUP')
	getServerResponse(tcpControlSocket)
	
	# Obtain current working directory:
	sendCommand(tcpControlSocket, 'PWD')
	directory = getServerResponse(tcpControlSocket)
	
	listFilesInWorkingDirectory(tcpControlSocket)
	
	
#------------------------------------------------------------	
def createPassiveConnection(tcpControlSocket):
	'''
		createPassiveConnection creates a Passive Data Connection (USER-DTP).
		Determines the address and port used on the FTP-Server for the SERVER-DTP
		connection.
	'''
	print("========== CREATE DATA SOCKET ============")
	# Determine port used for Data Connection Socket on Server Side:
	sendCommand(tcpControlSocket, 'PASV')
	response = getServerResponse(tcpControlSocket)
	
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
	
	# Create Client Data Transmission Socket:
	# Server Address where server listens for TCP connection:
	serverDataTransmissionAddress = (serverName,serverTCPDataPort)
	print('Connecting to {} port {}'.format(*serverDataTransmissionAddress))

	# Create Client TCP Data socket:
	dataConnectionSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

	# Connect to the client socket to the port where the server is listening:
	dataConnectionSocket.connect(serverDataTransmissionAddress)
	
	print("========== DATA SOCKET CREATED ===========")
	
	return dataConnectionSocket
	
#------------------------------------------------------------	
def sendCommand(tcpControlSocket, command="NOOP", message=""):
	'''
		sendCommand sends a specified command and message, if any, to the FTP server.
		Default command send is NOOP.
	'''
	tcpControlSocket.sendall((command+' '+message+'\r\n').encode())	

#------------------------------------------------------------			
def getServerResponse(tcpControlSocket):
	'''
		getServerResponse retrieves the response message from the FTP server 
		after a command was sent by the client.
	'''
	receivedMessage = tcpControlSocket.recv(8192).decode("UTF-8")
	
	# Split response at first space:
	responseCode, message = receivedMessage.split(" ",1)
	print(receivedMessage)
	
	return responseCode, message
	
#------------------------------------------------------------	
def determineServerFileSeparator(pathName):
	'''
		determineServerFileSeparator obtains the file path separator used by 
		the FTP Server.
	'''
	indexFilePathSep = pathName.find('/')
	if indexFilePathSep==-1:
		filesep = r'\\'
	else:
		filesep = r'/'
	return filesep
	
#------------------------------------------------------------	
def download(tcpControlSocket, file, outputPath):
	'''
		download is responsible for the retrieval of a file from the server.
		The PWD command is used to obtain the current directory of focus on the server.
		The TYPE command is sent. Upon a successful response from the command RETR the 
		file is download to the client and saved at a user specified output path.
	'''
	print("============ DOWNLOADING ===============")
	# Obtain current working directory:
	sendCommand(tcpControlSocket, 'PWD')
	response = getServerResponse(tcpControlSocket)
	downloadPath = response[1]
	
	indexFirstElement = response[1].find('"')
	indexLastElement  = response[1].rfind('"')
	downloadPath = downloadPath[indexFirstElement+1:indexLastElement]
	
	# Get file path separator:
	filesep = determineServerFileSeparator(downloadPath)
	
	# Send 
	type = 'I'
	sendCommand(tcpControlSocket, 'TYPE', type)
	response = getServerResponse(tcpControlSocket)
	
	# Data connection socket is opened to begin file transmission:
	dataConnectionSocket = createPassiveConnection(tcpControlSocket)
	
	# Download requested file:
	if downloadPath=='/':
		filesep = ''
	filename = downloadPath+filesep+file
	
	sendCommand(tcpControlSocket, 'RETR', filename)
	response = getServerResponse(tcpControlSocket)
	responseCode = response[1]

	# Create file path with file name to save file on disk:
	filesep ='/'
	filename = outputPath+filesep+file
	
	#if type.upper()=='I':
	# Write binary file to file path:
	downloadedData = dataConnectionSocket.recv(8192)

	with open(filename, 'wb') as currentDownload:
		print("Starting Download...")
		while downloadedData:
			currentDownload.write(downloadedData)
			downloadedData = dataConnectionSocket.recv(8192)
		
		# Close the file:
		currentDownload.close()
		
	#elif type.upper() == 'ASCII':
	# Done downloading:
	print('Downloading Complete')
	
	# close data connection socket:
	dataConnectionSocket.close()
	
	# Print Server Response after download completion:
	response = getServerResponse(tcpControlSocket)
	print("========= DOWNLOADING DONE ============")
	
#------------------------------------------------------------
def upload(tcpControlSocket, file, currentDirectory=""):
	'''
		upload is responsible for uploading a selected file
		to the server through the data connection socket.
		
		It first obtains the current directory of focus on the server
		and then sends the TYPE command. After a successful response
		the STOR command is sent and the selected file is uploaded.
	'''
	print("============== UPLOADING ==================")
	# Obtain current working directory:
	sendCommand(tcpControlSocket, 'PWD')
	response = getServerResponse(tcpControlSocket)
	uploadPath = response[1]
	
	indexFirstElement = response[1].find('"')
	indexLastElement  = response[1].rfind('"')
	uploadPath = uploadPath[indexFirstElement+1:indexLastElement]
	
	# Check file path separator:
	filesep = determineServerFileSeparator(uploadPath)
	
	# Send  
	type = 'I'  # Binary 
	sendCommand(tcpControlSocket, 'TYPE', type)
	response = getServerResponse(tcpControlSocket)
	
	# Data connection socket is opened to begin file transmission:
	dataConnectionSocket = createPassiveConnection(tcpControlSocket)
	
	# Create filename:
	if uploadPath=='/':
		filesep = ''
	filename = uploadPath+filesep+file
	print("I want to upload {}".format(filename))
	
	# Upload selected file:
	sendCommand(tcpControlSocket, 'STOR', filename)
	response = getServerResponse(tcpControlSocket)
	
	# Upload file:
	currentDirectory = currentDirectory.replace("\\","/")
	currentDirectory = currentDirectory.replace('"','')
	filesep = '/'
	filename = [currentDirectory, filesep, file]
	filename = "".join(filename)
	
	#if type.upper()=='I':
	# Write binary file to file path:
	with open(filename, 'rb') as currentUpload:
		uploadedData = currentUpload.read(8192)
		
		while uploadedData:
			print("Reading file...")
			dataConnectionSocket.send(uploadedData)
			uploadedData = currentUpload.read(8192)
		# Close the file:
		currentUpload.close()
	
	#elif type.upper() == 'ASCII':
	# Done uploading:
	print("Done Uploading {}!".format(file))
	
	# Close Data Connection Socket:
	dataConnectionSocket.close()
	
	# Get FTP Server Response:
	response = getServerResponse(tcpControlSocket)
	print("============ UPLOADING DONE ===============")
	
#------------------------------------------------------------	 
def doLogout(tcpControlSocket):
	'''
		doLogout is responsible for sending the Logout command
		QUIT to the FTP server.
	'''
	sendCommand(tcpControlSocket, 'QUIT')
	getServerResponse(tcpControlSocket)

#------------------------------------------------------------		
def terminateConnection(tcpControlSocket, dataConnectionSocket):
	'''
		terminateConnection closes the sockets being used but logs the 
		user out first.
	'''
	doLogout(tcpControlSocket)
	tcpControlSocket.close()
	dataConnectionSocket.close()
	print("All connections have been closed.")

#------------------------------------------------------------
def changeWorkingDirectory(tcpControlSocket, newPathName):
	'''
		changeWorkingDirectory is responsible for implementing the CWD FTP command.
		
		The client will change the current working directory and the function will then
		request a new list of the items in the new directory.
	'''
	sendCommand(tcpControlSocket, 'CWD', newPathName)
	getServerResponse(tcpControlSocket)
	
	# Update list:
	listFilesInWorkingDirectory(tcpControlSocket, newPathName)
#------------------------------------------------------------
def listFilesInWorkingDirectory(tcpControlSocket, pathName=""):
	'''
		listFilesInWorkingDirectory is responsible for retrieving the 
		list of files in the specified pathName.
		
		It returns the list sent by the server over the data connection socket.
	'''
	# Obtain current working directory:
	#sendCommand(tcpControlSocket, 'PWD','')
	#activeDirectory = getServerResponse(tcpControlSocket)
	print("============= GETTING LIST ================")
	dataConnectionSocket = createPassiveConnection(tcpControlSocket)
	
	#sendCommand(tcpControlSocket, 'LIST', pathName)
	sendCommand(tcpControlSocket, 'NLST', pathName)
	response = getServerResponse(tcpControlSocket)

	
	tempFilename = 'directoryList.txt'
	with open(tempFilename, 'w') as currentList:
		dataList = dataConnectionSocket.recv(8192).decode()
		print(dataList)
		while dataList:
			print("Receiving List of Directory "+pathName+" ...")
			currentList.write(dataList)
			dataList = dataConnectionSocket.recv(8192).decode()
			
		# Close the file:
		currentList.close()
	#elif type.upper() == 'ASCII':
	dataConnectionSocket.close()
	
	# Print Server Response after download completion:
	response = getServerResponse(tcpControlSocket)
	
	with open(tempFilename, 'r') as currentList:
		listDirec = currentList.read()
		
		# Close the file:
		currentList.close()
	# Return list of files in Directory:
	print('=========== FILES/FOLDERS ===========')
	print(listDirec)
	print("============= LIST DONE ================")
	
	return listDirec
#------------------------------------------------------------
def main():
	# Server Name:
	hostServerName = 'ELEN4017.ug.eie.wits.ac.za'
	hostServerName = '127.0.0.1'
	print("============== INITIALIZE ===============")
	tcpControlSocket = initializeFTPConnection(hostServerName)
	
	# Login:
	username = 'group6'
	
	password = 'reiph9Ju'
	doLogin(tcpControlSocket, username, password)
	
	# Change directory:
	changeWorkingDirectory(tcpControlSocket, '/files/')
	
	# Obtain Data connection port used by the server:
	#dataConnectionSocket = createPassiveConnection(tcpControlSocket)
	
	# Download file:
	saveFileInDirectory = r'C:/Users/Lynch-Stephen/Documents/Lecture Notes/4th year/ELEN4017A/Project/temp'
	file = 'rfc959.pdf'
	download(tcpControlSocket, file, saveFileInDirectory)
	
	# Upload file:
	#currentDirectory = r'"C:Users\Lynch-Stephen\Documents\Lecture Notes\4th year\ELEN4017A\Project"'
	currentDirectory = r'C:/Users/Lynch-Stephen/Documents/Lecture Notes/4th year/ELEN4017A/Project/temp'
	file = 'rfc959.pdf'
	upload(tcpControlSocket, file, currentDirectory)
	listFilesInWorkingDirectory(tcpControlSocket)
	
	
	# Terminate the connection:
	doLogout(tcpControlSocket)
	#terminateConnection(tcpControlSocket, dataConnectionSocket)

if __name__ == '__main__':
	main()
