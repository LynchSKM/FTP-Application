import socket
import threading
import sys
import os

#class ClientProtocolInterpreter(threading.Thread):
	#def __init__(self, serverName, username, password):
		# Construct thread object and initialize values:
		#threading.Thread.__init__(self)
		# self.serverName = serverName
		# self.username   = username
		# self.password   = password
		
		# Ports used by server for FTP:
		# self.serverControlConnectionPort = 21
		# self.serverDataTransmissionPort  = 20
		
		# Create Server Address(es):
		# self.serverControlConnectionAddress = (self.serverName, self.serverControlConnectionPort)
		# self.serverDataTransmissionAddress  = (self.serverName, self.serverDataTransmissionPort)
		
		# def run(self):
#class FTPClient():

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
	sendCommand(tcpControlSocket, 'CDUP', "")
	getServerResponse(tcpControlSocket)
	
#------------------------------------------------------------	
def createPassiveConnection(tcpControlSocket):
	'''
		createPassiveConnection creates a Passive Data Connection (USER-DTP).
		Determines the address and port used on the FTP-Server for the SERVER-DTP
		connection.
	'''
	# Determine port used for Data Connection Socket on Server Side:
	sendCommand(tcpControlSocket, 'PASV')
	getServerResponse(tcpControlSocket)
	
#------------------------------------------------------------	
def sendCommand(tcpControlSocket, command, message):
	'''
		sendCommand sends a specified command and message, if any, to the FTP server.
	'''
	tcpControlSocket.sendall((command+' '+message+'\r \n').encode())	

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
	
	return message, responseCode
	
#------------------------------------------------------------	
def determineServerFileSeparator(pathName):
	'''
		determineServerFileSeparator obtains the file path separator used by 
		the FTP Server.
	'''
	indexFilePathSep = pathName.find('/')
	if indexFilePathSep==-1:
		filesep = r'"\"'
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
	# Obtain current working directory:
	sendCommand(tcpControlSocket, 'PWD','')
	downloadPath = getServerResponse(tcpControlSocket)
	
	filesep = determineServerFileSeparator(downloadPath)
	
	# Send 
	type = 'I'
	sendCommand(tcpControlSocket, 'TYPE', type)
	response = getServerResponse(tcpControlSocket)
	
	# Data connection socket is opened to begin file transmission:
	dataConnectionSocket = createPassiveConnection(tcpControlSocket)
	
	
	# Download requested file:
	filename = downloadPath+file
	sendCommand(tcpControlSocket, 'RETR', filename)
	response = getServerResponse(tcpControlSocket)
	
	# Obtain file path separator:
	# indexFilePathSep = outputPath.rfind("\")
	# if indexFilePathSep==-1:
	#	# indexFilePathSep = outputPath.rfind("/")
	#
	
	# Create file path with file name to save file on disk:
	filesep = r'/'
	filename = outputPath+filesep+file
	
	#if type.upper()=='I':
	# Write binary file to file path:
	with open(filename, 'wb') as currentDownload:
		downloadedData = tcpControlSocket.recv(8192)
		
		while downloadedData:
			currentDownload.write(downloadedData)
			downloadedData = dataConnectionSocket.recv(8192)
		
		# Close the file:
		currentDownload.close()
	# Print Server Response after download completion:
	response = getServerResponse(tcpControlSocket)
	
	#elif type.upper() == 'ASCII':
	dataConnectionSocket.close()
	
#------------------------------------------------------------
def upload(tcpControlSocket, file, currentDirectory):
	'''
		upload is responsible for uploading a selected file
		to the server through the data connection socket.
		
		It first obtains the current directory of focus on the server
		and then sends the TYPE command. After a successful response
		the STOR command is sent and the selected file is uploaded.
	'''
	# Obtain current working directory:
	sendCommand(tcpControlSocket, 'PWD','')
	uploadPath = getServerResponse(tcpControlSocket)
	
	# Check file path separator:
	filesep = determineServerFileSeparator(uploadPath)
	
	# Send  
	type = 'I'  # Binary 
	sendCommand(tcpControlSocket, 'TYPE', type)
	response = getServerResponse(tcpControlSocket)
	
	# Data connection socket is opened to begin file transmission:
	dataConnectionSocket = createPassiveConnection(tcpControlSocket)
	
	# Create filename:
	filename = uploadPath+filesep+file
	
	# Upload selected file:
	sendCommand(tcpControlSocket, 'STOR', filename)
	response = getServerResponse(tcpControlSocket)
	
	# Upload file:
	filesep = r'/'
	filename = currentDirectory+filesep+file
	
	#if type.upper()=='I':
	# Write binary file to file path:
	with open(filename, 'rb') as currentUpload:
		uploadedData = currentUpload.read()
		
		while uploadedData:
			print("Reading file...")
			dataConnectionSocket.sendall(uploadedData)
			uploadedData = currentUpload.read(8192)
			
		# Close the file:
		currentUpload.close()
		
	# Print Server Response after download completion:
	response = getServerResponse(tcpControlSocket)

	#elif type.upper() == 'ASCII':
	dataConnectionSocket.close()
	
#------------------------------------------------------------	 
def doLogout(tcpControlSocket):
	'''
		doLogout is responsible for sending the Logout command
		QUIT to the FTP server.
	'''
	sendCommand(tcpControlSocket, 'QUIT', "")
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
	#listFilesInWorkingDirectory(tcpControlSocket, newPathName)
#------------------------------------------------------------
def listFilesInWorkingDirectory(tcpControlSocket, pathName):
	'''
		listFilesInWorkingDirectory is responsible for retrieving the 
		list of files in the specified pathName.
		
		It returns the list sent by the server over the data connection socket.
	'''
	# Obtain current working directory:
	#sendCommand(tcpControlSocket, 'PWD','')
	#activeDirectory = getServerResponse(tcpControlSocket)
	
	sendCommand(tcpControlSocket, 'LIST', pathName)
	response = getServerResponse(tcpControlSocket)

	
	dataConnectionSocket = createPassiveConnection(tcpControlSocket)
	
	tempFilename = 'directoryList.txt'
	with open(tempFilename, 'w') as currentList:
		dataList = dataConnectionSocket.recv(8192)
		
		while dataList:
			print("Receiving List of Directory "+pathName+" ...")
			currentList.wirte(dataList)
			dataList = dataConnectionSocket.recv(8192)
			
		# Close the file:
		currentList.close()
		
	# Print Server Response after download completion:
	response = getServerResponse(tcpControlSocket)

	#elif type.upper() == 'ASCII':
	dataConnectionSocket.close()
	
	with open(tempFilename, 'r') as currentList:
		listDirec = currentList.read()
		
		# Close the file:
		currentList.close()
	# Return list of files in Directory:
	return listDirec
#------------------------------------------------------------
def main():
	# Server Name:
	hostServerName = 'ELEN4017.ug.eie.wits.ac.za'
	#hostServerName = '127.0.0.1'
	print("============== INITIALIZE ===============")
	tcpControlSocket = initializeFTPConnection(hostServerName)
	
	# Login:
	username = 'group6'
	password = 'reiph9Ju'
	doLogin(tcpControlSocket, username, password)
	
	# Obtain Data connection port used by the server:
	#dataConnectionSocket = createPassiveConnection(tcpControlSocket)
	
	# Upload Image:
	
	# Download Image:
	
	# Terminate the connection:
	doLogout(tcpControlSocket)
	#terminateConnection(tcpControlSocket, dataConnectionSocket)

if __name__ == '__main__':
	main()
