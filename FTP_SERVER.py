import socket
import threading
import os
import sys
import stat
import datetime
import shutil

fileLock  = threading.Lock()
BUSYFILES = []
BUSYUPLOADS = []

def isUserNameValid(dataBase,userName):
	userName = userName
	userName = userName.rstrip()
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

def UploadFile(connectionMode,filename,commandSocket,act_dataConnection,pass_dataConnection,mode='rb'): 
	bufferSize= 8192 #Define the Buffer Size 8192
	print("Server Uploading File..")
	file = filename[filename.rfind('\\')+1:]
	fileSize = os.path.getsize(filename)

	#select the Mode:
	if connectionMode == "ACTIVE":
		dataConnection = act_dataConnection
	elif connectionMode == "PASSIVE":
		dataConnection = pass_dataConnection
	#end
	
	#Check if the File Exist before doing anything:
	if not os.path.exists(filename):
		message = "550 File not found in CurrentDir.\r\n"
		commandSocket.send(message.encode())
		print("File not found")
		return
	#End_if
	
	#Check if the File is being used or Not:
	while True:#If the file is found in the BUSYFILES then wait here until is not BUSY
		try:
			found_at = BUSYFILES.index(filename) 
		except: #index throw an exception whe utem not found in the list
			break
		#End_try
	#End_While
	
	#Now add the file to BUSYFILES list because Thread is going to use it:
	BUSYUPLOADS.append(filename)
	
	try:
		#dataConnection.connect((clientIP, dataPort))
		message = "150 Data connection ready, sending "+file+" ("+str(os.path.getsize(filename))+" bytes)\r\n"
		commandSocket.send(message.encode())
		
		#Now open the File for Transferring:
		#fileLock.acquire()
		#print('A Thread has locked the access to the File: '+file)
		print("Opening the file")
		with open(filename, mode) as theFile:
			bytesToSend = theFile.read(bufferSize)
			dataConnection.send(bytesToSend)
			while bytesToSend:
				prevBytes   = bytesToSend
				bytesToSend = theFile.read(bufferSize)
				dataConnection.send(bytesToSend)
				if not bytesToSend:
					break
			#End_While
		#End_With
		print("Server Done uploding")
		
		#Close the File and Dat connection:
		theFile.close()
		#Now remove the file from BUSYFILES list because Thread is done with it:
		#use try exception block in case the error occur at run time while deleting
		#
		
		try:
			BUSYUPLOADS.remove(filename)		
		except:
			pass
		#End
		message = "226 Transfer completed Closing data connection.\r\n"
		commandSocket.send(message.encode())
		dataConnection.send(("").encode())
	except:
		message = "425 Failed to open data connection.\r\n"
		print(message)
		commandSocket.send(message.encode())
	#End_Try_Except
	#dataConnection.close()
	return
#End_Upload

def DownloadFile(connectionMode,filename,commandSocket,act_dataConnection,pass_dataConnection): 
	bufferSize = 8192 #Define the Buffer Size
	print("Directory: "+filename)
	print("Server Downloading File...")
	
	#select the Mode:
	if connectionMode == "ACTIVE":
		dataConnection = act_dataConnection
	elif connectionMode == "PASSIVE":
		dataConnection = pass_dataConnection
	#end
	
	#Check if the File is being used or Not:
	while True:#If the file is found in the BUSYFILES then wait here until is not BUSY
		try:
			found_at = BUSYFILES.index(filename) 
		except: #index throw an exception whe utem not found in the list
			break
			#End_try
	#End_While
	while True:#If the file is found in the BUSYFILES then wait here until is not BUSY
		try:
			found_at = BUSYUPLOADS.index(filename) 
		except: #index throw an exception whe utem not found in the list
			break
		#End_try
	#End_While
	
	#Now add the file to BUSYFILES list because Thread is going to use it:
	BUSYFILES.append(filename)
	
	#fileLock.acquire()
	#print('A Thread has locked the access to the File: ')	
	if os.path.isfile(filename): #If the file already Exist deny the fine to avoid overwriting
		print("Path already Exist...")
		message = "553 File exist on the remote site, File will get Overwritten.\r\n"
		commandSocket.send(message.encode())
		theFile = open(filename,'wb')
	else: #otherwise create the file to write to
		print("Path not Exist...")
		print(filename)
		theFile = open(filename,'wb')	
		message = "150 File status okay; about to open data connection.\r\n"
		commandSocket.send(message.encode())
	#End_if
	
	print("We are getting there...")
	

	try:		
		#Now open the File for Downloading:
		print('opening file...')
		bytesToSave = dataConnection.recv(bufferSize)
		#theFile = open(filename, 'wb')
		print('Writing to file...')
		while bytesToSave:
			theFile.write(bytesToSave)
			bytesToSave = dataConnection.recv(bufferSize)
		#End_While
		 
		#Close the File and Dat connection:
		theFile.close()
		#Now remove the file from BUSYFILES list because Thread is done with it:
		#use try exception block in case the error occur at run time while deleting
		#dataConnection.close()
		try:
			BUSYFILES.remove(filename)		
		except:
			pass
		#End
		#fileLock.release()
		print('A Thread has released the access to the File')
		message = "226 Transfer completed Closing data connection.\r\n"
		commandSocket.send(message.encode())
		print("Download complete")
	except:
		message = "425 Failed to open data connection.\r\n"
		print(message)
		commandSocket.send(message.encode())
	#End_Try_Except ecode
	dataConnection.send(("").encode())
	return
#End_Upload

def clientLogIn(clientIP,commandSocket,DataBase):
	print("We are loggin in...\n") 
	request  = commandSocket.recv(7168).decode()#.strip("\r\n") #Expecting a User Name
	request  = request.rstrip()
	command  = request.split() 
	userName = command[-1]
	userName = ''.join(userName.split())
	print(clientIP+" Request: "+request)	#command[1] -> username 
	print("ftp CC: "+command[0])
	print("ftp DD: "+userName)
	
	if command[0].upper() == "USER":	#command[0] -> FTP command
		if isUserNameValid(DataBase,userName): 
			message = "331 Password required to access user account "+userName+".\r\n"
			commandSocket.send(message.encode())
			request = commandSocket.recv(7168).decode().rstrip() #Expecting a User Password	
			command = request.split() #command[1] -> userPassword
			userPassword = command[-1].rstrip() #command[1] -> userPassword
			print(clientIP+" Request: "+request)
			print("ftp C:"+command[0]+"\n")
			print("ftp D:"+userPassword+"\n")
			
			if command[0].upper()=="PASS":
				if isUserPassWordValid(DataBase,userName,userPassword):
					message = "230 Logged in.\r\n"
					commandSocket.send(message.encode())
					print("Client Logged in")
					UserPath = os.getcwd()+'\\'+userName
					_ = ftp_MakeDir(UserPath)
					return True,userName
				else:
					message = "502 incorrect password for  "+userName+".\r\n"
					commandSocket.send(message.encode())
					return False,'error'
				#End_if
			else:
				message = "502 Command "+command[0]+" not implemented.\r\n"
				commandSocket.send(message.encode())
				return False				
		else:
			message = "332 UserName "+userName+" not registered. Need account for log in.\r\n"
			commandSocket.send(message.encode())
			return False,'error'
		#End_Else
	else:
		message = "502 Command "+command[0]+"not implemented.\r\n"
		commandSocket.send(message.encode())
		return False,'error'
#End_LogIn	

def ftp_NLST(directory):
	valid = os.path.isdir(directory)	#Check if the specified Directory exist
	if valid:
		items = os.listdir(directory)	#get a list of all the items in the specified directory
		response = items#"200 "+ " ".join(items)		#Join the item list into a space seperated string
		return response
	else:
		response = []
		response.append("450 directory '"+directory+"' not found.\r\n")
		return response
	#end if
#End_LIST

def ftp_MakeDir(directory):
	if not os.path.exists(directory):
		os.makedirs(directory)	
		response = "200 Okay Directory created.\r\n"
	else:
		response = "550 Directory NOT created.\r\n"
	#endIf
	return response
#End Function
	
def ftp_Size(directory):
	valid = os.path.exists(directory)
	if valid:
		fileSize = os.path.getsize(directory)
		response = "213 " + str(fileSize)+"\r\n"
	else:
		response = "450 directory not found.\r\n"
	#End_If
	
	return response
#end Size:
def ftp_STRU():
	return "200 F\r\n"
#End_Stru
def ftp_MODE():
	return "200 S\r\r"
#End MOde	
def ftp_DEL(directory):
	print('Deleting From Dir: '+directory)
	print("Server Deleting a file...")
	try:
		if os.path.isfile(directory): 
			print('issa FILE')
			os.unlink(directory)
			response = "220 Ok File deleted.\r\n"
		elif os.path.isdir(directory): 
			print('issa DIR')
			shutil.rmtree(directory)
			response = "220 Ok File deleted.\r\n"
		else:
			response = "450 directory NOT found.\r\n"
		#End_If	
	except:
		print('is NOT found')
		print('Failed to delete')
		response = "450 directory NOT deleted.\r\n"
	#End_Try
	
	print("Server has deleted a file...")
	return response
#End_Del

def ftp_LIST(directory):
	valid = os.path.isdir(directory)	#Check if the specified Directory exist
	if valid:
		items = os.listdir(directory)	#get a list of all the items in the specified directory
		response = []
		for file in items:
			newPath = os.path.join(directory,file)
			dateM 	= datetime.datetime.fromtimestamp(os.path.getmtime(newPath)).strftime('%b %d %H:%M')
			#dateM   = dateM.replace("/", ' ') 
			theSize = os.path.getsize(newPath)
			ty	    = str(stat.filemode(os.stat(newPath).st_mode))+'\t'+'1 4006 \t 4000\t\t'+str(theSize)+'\t'+str(dateM)+'\t'+file 
			response.append(ty)
		#response = items#"200 "+ " ".join(items)		#Join the item list into a space seperated string
		return response
	else:
		response = []
		response.append("450 directory '"+directory+"' not found.\r\n")
		return response
	#end if
#End_LIST

def ftp_CWD(requestedDir,HomeDir, CurrentDir,request):
	print('Home Dir: '+HomeDir)
	print('Current Dir: '+CurrentDir)
	print('requested Dir: '+requestedDir)
	
	indexLastElement = request.rfind('\\')
	if indexLastElement != -1:
		ftpData = (request[indexLastElement+1:]).strip('\\').strip('/')
		newPath = HomeDir+requestedDir
	else:
		ftpData = (ftpData.strip('/')).strip('\\')
		newPath = CurrentDir+'\\'+ftpData
	#EndElse	
	
	print('Final Path: '+newPath)
	#Check if the request Directory Exist in the Current directory
	valid = os.path.isdir(newPath) 
	if valid:
		response = "200 CWD changed \r\n"
	else:
		response = "450 requested Dir not found in the Home Dir.\r\n"
	#End_if	
	return (response,newPath)
#End_CWD

def PORT(data):
	listT = data.split(',')
	upper = int(listT[4]) 
	lower = int(listT[5])
	clientIp = '.'.join(listT[:4])
	clientPort = 256*upper + lower
	clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	for i in range(0, 5):
		try:
			clientSocket.connect((clientIp,clientPort))
			break
		except:
			pass
		#End_try
	#End_For
	message = "220 Entering Active Connection...\r\n"
	return clientSocket,message
	
def ftp_CDUP(CurrentDir,HomeDir):
	if CurrentDir == HomeDir:
		return HomeDir
	else:
		lastIndex = CurrentDir.rfind('\\')
		newDir = CurrentDir[:lastIndex]
		return newDir
	
def ftp_PWD(homeDir,currDir):
	print('Home Dir: '+homeDir)
	print('Current Dir: '+currDir)
	
	lastFolder = homeDir.split('\\')
	lastFolder = lastFolder[-1]
	if currDir.find(homeDir) != -1:
		currDir  = currDir.replace(homeDir,'')
		response = '200 "\\'+currDir+'"\r\n'
		return response
	else:
		return "200 \\ \r\n"
#End_PWD
def syntexError():
	return "501 Syntax error in parameters or arguments.\r\n"
def ftp_PASV(passDataSocket):
	print("Handling Passive Request")
	try:
		passDataSocket.listen()
	except:
		pass
		
	deviceIPaddr = socket.gethostbyname(socket.gethostname())
	deviceIPaddr = deviceIPaddr.replace('.',',')
	
	#deviceIPaddr = '127,0,0,1'
	
	port  = passDataSocket.getsockname()[1]
	port  = "{0:b}".format(port).zfill(16)
	upper = int(port[:8],2)
	lower = int(port[8:],2)
	
	#upper = 0
	#lower = 20
	
	address = deviceIPaddr+','+str(upper)+','+str(lower)
	response = '227 Entering Passive Mode ('+address+')\r\n'
	return response
#end_PASS
def ClientHandler(DataBase,clientIP,commandSocket,dataSocket):
	LANHost = socket.gethostbyname(socket.gethostname())
	PassivedataSocket = socket.socket()
	PassivedataSocket.bind((LANHost,0))
	
	bufferSize = 7168
	passiveConnection = None
	activeConnection  = None
	fileMODE = "rb"
	NewAddress=''
	dataMODE = "PASSIVE"
	
	#Send the Hello Message:
	message = "220 Hello, Nchabeleng File Service.\r\n"
	commandSocket.send(message.encode())
	
	#User Validation Process:
	print('user trying to log in')
	loggedin = False
	user = 'error'
	while not loggedin:
		loggedin,user = clientLogIn(clientIP,commandSocket,DataBase)
	#End_Log in
	print('user has logged in')
	
	#Set the Current Directory for the Client
	HomeDirectory 	 = os.path.join(os.getcwd(),user) #Se the CLIENT to use hi folder
	WorkingDirectory = HomeDirectory
	print("Home dir= "+HomeDirectory)
	print("Current dir= "+WorkingDirectory)	
	
	#Interaction Client
	while True:
		try:
			request  = (commandSocket.recv(bufferSize).decode()).rstrip()
			while not request:
				request  = (commandSocket.recv(bufferSize).decode()).rstrip()
			
			print("==============================================================================")
			command  = request.split(' ', 1)
			print('\n\n'+clientIP+" "+request)
			ftpCommand  = (command[0].rstrip()).upper()
			ftpData		= command[-1].rstrip()
				
				
			print("ftp C= "+ftpCommand)
			print("ftp D= "+ftpData)
			#commandSocket.send(".".encode())
			if   ftpCommand=="QUIT":
				message = "221 Goodbye.\r\n"
				commandSocket.send(message.encode())			
				break
			
			elif ftpCommand=="STRU":
				message = ftp_STRU()
				commandSocket.send(message.encode())
				
			elif ftpCommand=="MODE":
				message = ftp_MODE()
				commandSocket.send(message.encode())
			
			elif ftpCommand=="MKD":
				if ftpCommand==ftpData:
					message = syntexError()
					commandSocket.send(message.encode())
				else:
					ftpData  = (ftpData.strip('\\')).strip('/')
					filePath = os.path.join(WorkingDirectory,ftpData)
					message  = ftp_MakeDir(filePath)
					commandSocket.send(message.encode())
			
			elif ftpCommand=="SIZE":
				if ftpCommand==ftpData:
					message = syntexError()
					commandSocket.send(message.encode())
				else:
					ftpData  = (ftpData.strip('\\')).strip('/')
					filePath = os.path.join(HomeDirectory,ftpData)
					message  = ftp_Size(filePath)
					commandSocket.send(message.encode())

			elif ftpCommand=="DELE":
				if ftpCommand==ftpData:
					message = syntexError()
					commandSocket.send(message.encode())
				else:
					indexLastElement = request.rfind('\\')
					if indexLastElement != -1:
						ftpData = request[indexLastElement+1:]
					else:
						ftpData = (ftpData.strip('/')).strip('\\')
					#EndElse
					filePath = WorkingDirectory+"\\"+ftpData
					print("path: "+filePath)
					
					#message = "200 Okay deleting a Folder.\r\n"
					#commandSocket.send(message.encode())
					#filePath = os.path.join(HomeDirectory,ftpData)
					message  = ftp_DEL(filePath)
					commandSocket.send(message.encode())					
				
			elif ftpCommand=="PASV":
				PassivedataSocket.listen(5)
				message = ftp_PASV(PassivedataSocket)
				commandSocket.send(message.encode())
				print("trying to accept connection")
				dataMODE = "PASSIVE"
				passiveConnection,NewAddress = PassivedataSocket.accept()
				print("Data connection was Accepted "+str(NewAddress))
			
			elif ftpCommand=="PORT":
				dataMODE = "ACTIVE"
				ftpData = ftpData.rstrip().strip('/').strip('\\')
				activeConnection,message = PORT(ftpData)
				commandSocket.send(message.encode())
				
			elif ftpCommand=="STOR":
				print("We are going to STORE bbe...")
				if ftpCommand==ftpData:
					message = syntexError()
					commandSocket.send(message.encode())
				else:
					indexLastElement = request.rfind('\\')
					
					if indexLastElement!=-1:
						ftpData = request[indexLastElement+1:]
					path = os.path.join(WorkingDirectory,ftpData)
					print("path: "+path)
					DownloadFile(dataMODE,path,commandSocket,activeConnection,passiveConnection)
					passiveConnection.close()
					
			elif ftpCommand=="RETR":
				if ftpCommand==ftpData:
					message = syntexError()
					commandSocket.send(message.encode())
				else:
					#ftpData = ftpData.split('\\')
					#ftpData = ftpData[-1]
					indexLastElement = request.rfind('\\')
					if indexLastElement != -1:
						ftpData = request[indexLastElement+1:]
					else:
						ftpData = (ftpData.strip('/')).strip('\\')
					#EndElse
					path = WorkingDirectory+"\\"+ftpData
					print("path: "+path)
					UploadFile(dataMODE,path,commandSocket,activeConnection,passiveConnection)
					#commandSocket.send("\r\n".encode())
					passiveConnection.close()
					
			elif ftpCommand=="TYPE":
				if ftpCommand==ftpData:
					message = syntexError()
					commandSocket.send(message.encode())
				else:
					ftpData = ftpData.rstrip()
					if ftpData.upper() == "I":
						fileMODE = 'rb'
					elif ftpData.upper() == "A": 
						fileMODE = 'r'
					#endIf
					
					message = "200 Ok the "+ftpData+" Type has been selected.\r\n"
					commandSocket.send(message.encode())
					
			elif ftpCommand=="CWD":
				if ftpCommand==ftpData:
					message = syntexError()
					commandSocket.send(message.encode())
				else:				
					message,WorkingDirectory = ftp_CWD(ftpData,HomeDirectory,WorkingDirectory,request)
					commandSocket.send(message.encode())
			
			elif ftpCommand=="PWD":
				message = ftp_PWD(HomeDirectory,WorkingDirectory)
				commandSocket.send(message.encode())
			
			elif ftpCommand=="NLST":
				message = '200 List being send to Dataconnection.\r\n'
				commandSocket.send(message.encode())
				message = ftp_NLST(WorkingDirectory)
				for item in message:
					passiveConnection.sendall((item+'\r\n').encode())
				passiveConnection.send(("").encode())
				message = '200 Listing completed.\r\n'
				commandSocket.send(message.encode())	
				passiveConnection.close()
				print("Listing completed...")

			elif ftpCommand=="LIST":
				message = '200 List being send to Dataconnection.\n'
				commandSocket.send(message.encode())
				message = ftp_LIST(WorkingDirectory)
				for item in message:
					passiveConnection.sendall((item+'\r\n').encode())
				#passiveConnection.send(("\r\n").encode())
				message = '200 Listing completed.\r\n'
				commandSocket.send(message.encode())	
				passiveConnection.close()
				print("Listing completed...")
				
			elif ftpCommand=="CDUP":
				WorkingDirectory = ftp_CDUP(WorkingDirectory,HomeDirectory)
				message = ftp_PWD(HomeDirectory,WorkingDirectory)
				commandSocket.send(message.encode())
			
			elif ftpCommand=="NOOP":
				message = "200 Okay "+clientIP+'\r\n'
				commandSocket.send(message.encode())
			
			else:
				message = "502 Command "+ftpCommand+" not implemented.\r\n"
				commandSocket.send(message.encode())
			#End if:
		except socket.error as e: #If fail to receive then the conncection has been closed
			print("Command Socket has been forced to Closed.")
			break
		#End_While_Interaction
	
	print("Done servicing Client "+clientIP)
	commandSocket.close()
#End_ClientHanlder
	
def Main():
	host    = '127.0.0.1'
	print('Local Host: '+host)
	print(socket.gethostname())
	LANHost = socket.gethostbyname(socket.gethostname())
	print("LAN Host: "+LANHost)
	commadPort = 21
	dataPort   = 20

	commandSocket = socket.socket()
	commandSocket.bind((LANHost,commadPort))
	commandSocket.listen(5)

	dataSocket = socket.socket()
	dataSocket.bind((LANHost,dataPort))

	#dataSocket.listen(5)
	#LANHost = socket.gethostbyname(socket.gethostname())
	#PassiveDataSocket = socket.socket()
	#PassiveDataSocket.bind((LANHost,0))
	#dataSocket.listen(5)
	#print('Host Port:' +str(PassiveDataSocket.getsockname()[1]))
	
	print("Server Started.")
	while True:
		clientSocket, clientAddr = commandSocket.accept()
		print("client connected ip:<" + str(clientAddr) + ">")
		t = threading.Thread(target=ClientHandler, args=("dataBase.txt",str(clientAddr),clientSocket,dataSocket))
		t.start()
    #End_While     
		 
	print("Server Down")
	commandSocket.close()

if __name__ == '__main__':
	#ftp_DEL('C:\\Users\\Ngwato\\Desktop\\4thYear\\Networks\\Project\\s.txt')
	#results = ftp_NLIST(os.getcwd())
	#for item in results:
	#	print(item+'\n')
		
	#info = os.stat('Front.jpg')
	#t = datetime.datetime.fromtimestamp(os.path.getmtime('Front.jpg')).strftime('%Y-%m-%d %H:%M:%S')

	Main()
