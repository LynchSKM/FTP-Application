import socket
import threading
import os

fileLock = threading.Lock()

def isUserNameValid(dataBase,userName):
	#Open the DataBase:
	file = open(dataBase, 'r')
	Data = file.readlines()
	file.close()
	for user in Data:
		registeredUserName,registeredUserPass = user.split()
		if userName == registeredUserName:
			return True
		#End_If
	#Enf_For
	return False
#End_User Validation

def isUserPassWordValid(dataBase,userName,passWord):
	#Open the DataBase:
	file = open(dataBase, 'r')
	Data = file.readlines()
	file.close()
	for user in Data:
		registeredUserName,registeredUserPass = user.split()
		if userName == registeredUserName and passWord==registeredUserPass:
			return True
		#End_If
	#Enf_For
	return False
#End_User Validation

def UploadFile(filename,commandSocket,dataPort,clientIP,dataSocket): 
	bufferSize= 7168 #Define the Buffer Size
	print("Server Uploading File..")
	
	#Check if the File Exist before doing anything:
	if not os.path.exists(filename):
		message = "550 File not found in CurrentDir."
		commandSocket.send(message.ecode())
		return
	#End_if
		
	#Try to Establish Data connection if File Exist:
	#dataSocket = socket.socket()
	dataConnection,address = dataSocket.accept()
	try:
		dataConnection.connect((clientIP, dataPort))
		message = "225 Data connection open; transfer in progress."
		commandSocket.send(message.ecode())
		
		#Now open the File for Transferring:
		fileLock.acquire()
		with open(filename, 'rb') as theFile:
			bytesToSend = theFile.read(bufferSize)
			dataConnection.send(bytesToSend)
			while bytesToSend != "":
				bytesToSend = theFile.read(bufferSize)
				dataConnection.send(bytesToSend)
			#End_While
		#End_With
		
		#Close the File and Dat connection:
		theFile.close()
		fileLock.release()
		message = "226 Transfer completed Closing data connection."
		commandSocket.send(message.ecode())
		dataConnection.close()
	except:
		message = "425 Failed to open data connection on ("+clientIP+","+dataPort+")."
		print(message)
		commandSocket.send(message.ecode())
		return
	#End_Try_Except
#End_Upload

def DownloadFile(filename,commandSocket,dataPort=20,clientIP='127.0.0.1'): 
	bufferSize = 7168 #Define the Buffer Size
	print("Server Downloading File..")
	
	if os.path.exists(filename): #If the file already Exist deny the fine to avoid overwriting
		message = "553 File not name not allowed, try renaming it."
		commandSocket.send(message.ecode())
		return
	else: #otherwise create the file to write to
		os.makedirs(filename)
		message = "150 File status okay; about to open data connection."
		commandSocket.send(message.ecode())
	#End_if
		
		
	#Try to Establish Data connection:
	#dataSocket = socket.socket()
	dataConnection,address = dataSocket.accept()
	try:
		dataConnection.connect((clientIP, dataPort))
		message = "225 Data connection open; transfer in ready."
		commandSocket.send(message.ecode())
		
		#Now open the File for Downloading:
		bytesToSave = dataConnection.recv(bufferSize)
		theFile = open(filename, 'wb')
		while bytesToSave:
			theFile.write(bytesToSave)
			bytesToSave = dataConnection.recv(bufferSize)
		#End_While
		
		#Close the File and Dat connection:
		theFile.close()
		message = "226 Transfer completed Closing data connection."
		commandSocket.send(message.ecode())
		dataConnection.close()
	except:
		message = "425 Failed to open data connection on ("+clientIP+","+dataPort+")."
		print(message)
		commandSocket.send(message.ecode())
		return
	#End_Try_Except
#End_Upload

def clientLogIn(clientIP,commandSocket,DataBase):
	print("We are loggin in...\n") 
	request  = commandSocket.recv(7168).decode().rstrip() #Expecting a User Name
	print(clientIP+" Request: "+request)
	command  = request.split() 
	userName = command[-1] 				#command[1] -> username 
	if command[0].upper() == "USER":	#command[0] -> FTP command
		if isUserNameValid(DataBase,userName): 
			message = "331 Password required to access user account "+userName
			commandSocket.send(message.encode())
			request = commandSocket.recv(7168).decode().rstrip() #Expecting a User Password
			print(clientIP+" Request: "+request)
			command = request.split() #command[1] -> userPassword
			userPassword = command[-1] #command[1] -> username
			if command[0].upper()=="PASS":
				if isUserPassWordValid(DataBase,userName,userPassword):
					message = "230 Logged in."
					commandSocket.send(message.encode())
					print("Client Logged in")
					return True
				else:
					message = "502 incorrect password for  "+userName
					commandSocket.send(message.encode())
					return False
				#End_if
			else:
				message = "502 Command "+command[0]+" not implemented."
				commandSocket.send(message.encode())
				return False				
		else:
			message = "332 UserName "+userName+" not registered. Need account for log in"
			commandSocket.send(message.encode())
			return False
		#End_Else
	else:
		message = "502 Command "+command[0]+"not implemented."
		commandSocket.send(message.encode())
		return False
#End_LogIn	

def ftp_LIST(directory):
	valid = os.path.isdir(directory)	#Check if the specified Directory exist
	if valid:
		items = os.listdir(directory)	#get a list of all the items in the specified directory
		response = "200 "+ " ".join(items)		#Join the item list into a space seperated string
		return response
	else:
		response = "450 directory '"+directory+"' not found."
		return response
	#end if
#End_LIST

def ftp_CWD(requestedDir,HomeDir, CurrentDir):
	#Check if the request Directory Exist in the Current directory
	temp  = CurrentDir+requestedDir
	valid = os.path.isdir(temp) 
	if valid:
		newDirectory = temp
		response = "200 CWD changed to "+newDirectory
		return (response,newDirectory)
	else:#Check if the request Directory Exist in the Home directory
		temp  = HomeDir+requestedDir
		valid = os.path.isdir(temp)
		if valid:
			newDirectory = temp
			response = "200 CWD changed to "+newDirectory
			return (response,newDirectory)			
		else:
			newDirectory = CurrentDir
			response = "450 requested Dir not found in Current nor Home Dir"
			return (response,newDirectory)
		#End_if
	#End_if	
#End_CWD

def ftp_PWD(homeDir,currDir):
	lastFolder = homeDir.split('\\')
	lastFolder = lastFolder[-1]
	if currDir.find(homeDir) != -1:
		currDir  = currDir.replace(homeDir,'')
		response = "200 Current working dir is \\"+lastFolder+currDir
		return response
	else:
		return "200 Current working dir is \\"+lastFolder	
#End_PWD

def syntexError():
	return "501 Syntax error in parameters or arguments."
	
def ClientHandler(DataBase,clientIP,commandSocket,dataSocket):
	bufferSize = 7168
	
	#Set the Current Directory for the Client
	HomeDirectory 	 = os.getcwd() 
	WorkingDirectory = os.getcwd()
	print("Home dir= "+HomeDirectory)
	print("Current dir= "+WorkingDirectory)
	
	#Send the Hello Message:
	message = "220 Hello, this is the Nchabeleng File Service."
	commandSocket.send(message.encode())
	
	#User Validation Process:
	loggedin = False
	while not loggedin:
		loggedin = clientLogIn(clientIP,commandSocket,DataBase)
	#End_Log in
	
	#Interaction Client
	while True:
		try:
			request  = commandSocket.recv(bufferSize).decode().rstrip()
			command  = request.split()
			print(clientIP+" "+request)
			ftpCommand  = command[0]
			ftpData		= command[-1]
			print("ftp C= "+ftpCommand)
			print("ftp D= "+ftpData)
			#commandSocket.send(".".encode())
			if ftpCommand=="QUIT":
				message = "221 Goodbye."
				commandSocket.send(message.encode())			
				break
			elif ftpCommand=="STOR":
				if ftpCommand==ftpData:
					message = syntexError()
					commandSocket.send(message.encode())
				else:
					path = WorkingDirectory+ftpData
					DownloadFile(path,commandSocket,dataSocket)
			elif ftpCommand=="RETR":
				print("we are here..")
				if ftpCommand==ftpData:
					message = syntexError()
					commandSocket.send(message.encode())
				else:
					print("then here..")
					path = WorkingDirectory+ftpData
					UPloadFile(path,commandSocket,dataSocket)
					print("then finally here...")
			elif ftpCommand=="CWD":
				if ftpCommand==ftpData:
					message = syntexError()
					commandSocket.send(message.encode())
				else:
					message,WorkingDirectory = ftp_CWD(ftpData,HomeDirectory,WorkingDirectory)
					commandSocket.send(message.encode())
			elif ftpCommand=="PWD":
				message = ftp_PWD(HomeDirectory,WorkingDirectory)
				commandSocket.send(message.encode())
			elif ftpCommand=="LIST":
				message = ftp_LIST(WorkingDirectory)
				commandSocket.send(message.encode())
			elif ftpCommand=="CDUP":
				WorkingDirectory = HomeDirectory
				message = ftp_PWD(HomeDirectory,WorkingDirectory)
				commandSocket.send(message.encode())
			elif ftpCommand=="NOOP":
				message = "200 Okay "+clientIP
				commandSocket.send(message.encode())
			else:
				message = "502 Command "+ftpCommand+" not implemented."
				commandSocket.send(message.encode())
			#End if:
		except: #If fail to receive then the conncection has been closed
			print("Command Socket is Closed.")
			break
	#End_While_Interaction
	
	print("Done servicing Client "+clientIP)
	#commandSocket.close()
#End_ClientHanlder
	
def Main():
	host = '127.0.0.1'
	commadPort = 21
	dataPort   = 20

	commandSocket = socket.socket()
	commandSocket.bind((host,commadPort))
	commandSocket.listen(5)

	dataSocket = socket.socket()
	dataSocket.bind((host,dataPort))
	commandSocket.listen(5)
	print("Server Started.")
	while True:
		clientSocket, clientAddr = commandSocket.accept()
		print("client connected ip:<" + str(clientAddr) + ">")
		t = threading.Thread(target=ClientHandler, args=("dataBase.txt",str(clientAddr),clientSocket,dataSocket))
		#ClientHandler(DataBase,clientIP,commandSocket,dataSocket)
		t.start()
    #End_While     
		 
	print("Server Down")
	commandSocket.close()

if __name__ == '__main__':
    Main()