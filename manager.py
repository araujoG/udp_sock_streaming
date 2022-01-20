import socket
import select
import sys
import threading
from user import User

class ManagerModule:
  def __init__(self):
    self.port = 5000
    self.client_socket = self.start_manager()
    self.list_of_clients = []
    self.streaming_connection_up = 0
  
  def start_manager(self):
    addr = ("", self.port)
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client_socket.bind(addr)
    client_socket.listen(100)

    print("Manager is listening on port:", self.port)

    return client_socket

  def streaming_thread(self,conn,addr):
    while True:
      try:
        message = conn.recv(2048)
        message = message.decode()
        print(f"RECEBIDO '{message}' DO SERVIDOR DE STREAMING")
        if message.startswith("GET_USER_INFORMATION"):
          print(f"RECEBIDO '{message}' DO SERVIDOR DE STREAMING")
          id = message.split(" ")[1]
          if id.isnumeric():
            id = int(id)
            info1 = User.get_user_information(id)
            info = f"USER_INFORMATION {info1}"
            
            if info1:
              msg = info
            else:
              msg = "USER_NOT_FOUND"

            print(f"ENVIANDO '{msg}' PARA O SERVIDOR DE STREAMING")
            
            conn.send(msg.encode())
        if(message == "REQUEST_GROUP"):
          id = message.split(" ")[1]
          if id.isnumeric():
            id = int(id)
            group = User.get_group_ip(id)

            if group:
              msg = group
            else:
              msg = "NO_GROUP"

            print(f"ENVIANDO '{msg}' PARA O SERVIDOR DE STREAMING")

            conn.send(msg.encode())

      except socket.timeout:
        continue    
  

  def client_thread(self, conn, addr):
    print("Connection from:", addr)
    while True:
      try:
        message = conn.recv(2048)
        message = message.decode()
        print(f".RECEBIDO '{message}' DE {addr[0]}")
        if message.startswith("ENTRAR_NA_APP"):
          print(f"RECEBIDO 'ENTRAR_NA_APP' DE {addr[0]}")
          _msg, nome, tipo, ip = message.split(" ")
          user = User.get_user_by_ip(ip)
          if user == None:
            print(f"ENVIANDO 'ENTRAR_NA_APP_ACK' PARA {addr[0]}")
            user = User(nome, tipo, ip)
            user.save()
            conn.send(b"ENTRAR_NA_APP_ACK")
            user = User.get_user_by_ip(ip)
          id, nome, tipo, _ip = user.split(" ")
          msg = f"STATUS_DO_USUARIO {id} {nome} {tipo}"
          print(f"ENVIANDO '{msg}' PARA {addr[0]}")
          conn.send(msg.encode())
          print(f"ENVIOU '{msg}' PARA {addr[0]}")
          print("entrou na app")
        elif message == "SAIR_DA_APP":
          print(f"RECEBIDO 'SAIR_DA_APP' DE {addr[0]}")
          User.remove_by_ip(addr[0])
          print(f"ENVIANDO 'SAIR_DA_APP_ACK' PARA {addr[0]}")
          conn.send(b"SAIR_DA_APP_ACK")
          self.remove(conn)
          break
        elif message.startswith("CRIAR_GRUPO"):
          _,id = message.split(" ")
          id = int(id)
          User.add_group_to_user(id)
          print(f"ENVIANDO 'CRIAR_GRUPO_ACK' PARA {addr[0]}")
          conn.send(b"CRIAR_GRUPO_ACK")
          print(f"ENVIOU 'CRIAR_GRUPO_ACK' PARA {addr[0]}")
        elif message.startswith("VER_GRUPO"):
          _,id = message.split(" ")
          id = int(id)
          users = User.show_group(id)
          msg = f'GRUPO_DE_STREAMING {users}'
          print(f"ENVIANDO {msg} PARA {addr[0]}")
          conn.send(msg.encode())
          print(f"ENVIOU {msg} PARA {addr[0]}")
        elif message.startswith("ADD_USUARIO_GRUPO"):
          _,id,id_add = message.split(" ")
          id = int(id)
          id_add = int(id_add)
          _ = User.add_user_to_group(id,id_add)
          msg = f'ADD_USUARIO_GRUPO_ACK'
          print(f"ENVIANDO {msg} PARA {addr[0]}")
          conn.send(msg.encode())
          print(f"ENVIOU {msg} PARA {addr[0]}")
        elif message.startswith("REMOVER_USUARIO_GRUPO"):
          _,id,id_remove = message.split(" ")
          id = int(id)
          id_remove = int(id_remove)
          _ = User.remove_user_from_group(id,id_remove)
          msg = f'REMOVER_USUARIO_GRUPO_ACK'
          print(f"ENVIANDO {msg} PARA {addr[0]}")
          conn.send(msg.encode())
          print(f"ENVIOU {msg} PARA {addr[0]}")
        elif message == "LISTA_USUARIOS":
          users = User.return_users(addr[0])
          msg = f'LISTA_USUARIOS {users}'
          print(f"ENVIANDO {msg} PARA {addr[0]}")
          conn.send(msg.encode())
          print(f"ENVIOU {msg} PARA {addr[0]}")
        # if message != "":
        #   print ("<" + addr[0] + "> " + message)

        #   # Calls broadcast function to send message to all
        #   message_to_send = "<" + addr[0] + "> " + message
        #   self.broadcast(message_to_send, conn)

        # else:
        #     """message may have no content if the connection
        #     is broken, in this case we remove the connection"""
        #     self.remove(conn)

      except socket.timeout:
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
        print("CONEXÃO REMOVIDA")

  def serve_clients(self):
    while True:
      conn, addr = self.client_socket.accept()
      if(self.streaming_connection_up == 0):
        self.streaming_connection_up = 1
        streamingThread = threading.Thread(target=self.streaming_thread, args=(conn, addr))
        streamingThread.start()

      else:
        self.list_of_clients.append(conn)

        print (addr[0] + " connected")

        client_thread = threading.Thread(target=self.client_thread, args=(conn, addr))
        client_thread.start()

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