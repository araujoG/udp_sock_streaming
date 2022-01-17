import socket
import select
import sys
import threading

class ManagerModule:
  def __init__(self):
    self.port = 5000
    self.manager_socket = self.start_manager()
    self.list_of_clients = []
    # self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # self.sock.bind(('', 9999))
    # self.sock.listen(5)
    # self.conn, self.addr = self.sock.accept()
    # self.conn.send(b'Welcome to the server!')
    # self.data = self.conn.recv(1024)
    # print(self.data)
    # self.conn.close()
  
  def start_manager(self):
    addr = ("", self.port)
    
    manager_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    manager_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    manager_socket.bind(addr)
    manager_socket.listen(5)

    print("Manager is listening on port:", self.port)

    return manager_socket

  def clientthread(self, conn, addr):
    
    print("Connection from:", addr)

    # sends a message to the client whose user object is conn
    conn.send(b"Welcome to this chatroom!")
    print("mensagem enviada")
 
    while True:
      try:
        message = conn.recv(2048)
        message = message.decode()
        if message != "":

          print ("<" + addr[0] + "> " + message)

          # Calls broadcast function to send message to all
          message_to_send = "<" + addr[0] + "> " + message
          self.broadcast(message_to_send, conn)

        else:
            """message may have no content if the connection
            is broken, in this case we remove the connection"""
            self.remove(conn)

      except:
          continue

  def broadcast(self, message, connection):
    for clients in self.list_of_clients:
      if clients!=connection:
        try:
          clients.send(message)
        except:
          clients.close()

          # if the link is broken, we remove the client
          self.remove(clients)
  
  def remove(self, connection):
    if connection in self.list_of_clients:
        self.list_of_clients.remove(connection)

  def serve_clients(self):
    while True:
      conn, addr = self.manager_socket.accept()
 
      self.list_of_clients.append(conn)

      print (addr[0] + " connected")

      self.clientthread(conn,addr)

def main():
  server = ManagerModule()
  server.serve_clients()

if __name__ == "__main__":
    main()

# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# s.bind(('localhost', 50000))
# s.listen(1)
# conn, addr = s.accept()
# while 1:
#     data = conn.recv(1024)
#     if not data:
#         break
#     conn.sendall(data)
# conn.close()