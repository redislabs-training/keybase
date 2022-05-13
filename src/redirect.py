#!/usr/bin/python

#
# This script written by Eli Fulkerson.
# http://www.elifulkerson.com for more.
#

from socket import *
from select import *

HOST = ''
PORT = 80
TARGET = "https://target-website.com"

class Connection:
    """
    An accepted connection.
    """
    def __init__(self, socket, address):
        self.socket = socket
        self.ip = address[0]

    def sendline(self, data):
        self.socket.send((data + "\r\n").encode())

    def fileno(self):
        return self.socket.fileno()

class ConnectionHandler:
    """
    Maintains all connections.
    """
    def __init__(self):
        self.listener = socket(AF_INET, SOCK_STREAM)
        self.listener.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.listener.bind((HOST, PORT))
        self.listener.listen(32)
        print ("HTTP 302 Redirector is active and listening on port " + str(PORT) + ".")

    def run(self):
        """
        Listen for incoming connections on PORT.  When a connection is recieved, send a 302
        redirect and then close the socket.
        """
        # Accept an incoming connection.
        conn = select( [self.listener], [], [], 0.1)[0]

        if conn:
            socket, address = self.listener.accept()
            conn = Connection(socket, address)
            
            # burn some time so that the client and server don't have a timing error
            trash = conn.socket.recv(1024)

            # send our https redirect
            conn.sendline("HTTP/1.1 302 Encryption Required")
            conn.sendline("Location: " + TARGET)
            conn.sendline("Connection: close")
            conn.sendline("Cache-control: private")
            conn.sendline("")
            conn.sendline("<html><body>Encryption Required.  Please go to <a href='" + TARGET + "'>" + TARGET + "</a> for this service.</body></html>")
            conn.sendline("")

            # kick em out
            conn.socket.close

connections = ConnectionHandler()
while 1:
    connections.run()