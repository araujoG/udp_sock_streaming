from ast import arg
import queue
import select
import sys
import socket
import struct
from tkinter import *
from turtle import right
import cv2
import numpy as np
from PIL import Image, ImageTk
import time
import threading, wave, pyaudio
from user import User


class ClientModule:
    MAX_DGRAM_SIZE = 2 ** 16  # tamanho maximo de um datagrama udp

    def __init__(self, server_addr):
        # iniciando socket do cliente
        self.client_socket = None
        # porta utilizada pelo servidor
        self.server_port = 6000
        # endereco ipv4 do servidor
        self.server_addr = server_addr

        self.manager_socket = None
        self.manager_port = 5000

        self.exit_flag = False

        # Iniciando main window
        self.mainWindow = Tk()
        self.mainWindow.title("Streaming")
        self.username = StringVar()

        # Frames da janela principal
        self.mainWindowFrame = None
        self.managerFrame = None
        self.manage_group_button = None
        self.create_group_button = None
        self.notificationframe = None
        self.notification = None
        self.notification_interval = 2000
        self.notification_color = ""
        self.notification_group = False

        # Janela de Gerenciamento de Grupo
        self.groupManagerWindow = None
        self.groupManagerFrame = None
        self.reload_manager = True
        self.available_users = None
        self.user_to_add = StringVar()
        self.my_group = None
        self.user_to_remove = StringVar()
        self.is_grouped = None
        self.group_owner = None

        # Janela de seleção de vídeo
        self.resolution = StringVar()
        self.video_name = StringVar()

        self.audio_frame_list = queue.Queue(maxsize=2000)

        # intervalo de atualização dos frames do player
        self.interval = 20
        # imagem recebida do servidor
        self.image = None
        # imagem renderizada no player
        self.image1 = None
        self.buffered = False
        self.finished = False
        self.finish_audio = False

         # ID USUARIO
        self.user_id = None
        self.user_name = None
        self.user_type = None

        self.data = b""
        self.start_client()

    # Inicializa o socket do client
    def start_client(self):
        port = 5030 # 5050
        addr = ("", port)

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.bind(addr)

        self.manager_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.manager_socket.connect((self.server_addr, self.manager_port))

    # Carrega a janela principal da aplicação
    def open_main_window(self):
        self.mainWindowFrame = Frame(self.mainWindow)
        self.mainWindowFrame.pack(side=TOP)

        inputframe = Frame(self.mainWindowFrame)
        inputframe.pack(side=TOP, padx=10)

        L1 = Label(inputframe, text="User Name")
        L1.pack( side = TOP)
        E1 = Entry(inputframe, bd = 1, textvariable = self.username)
        E1.pack(side = TOP)

        bottomframe = Frame(self.mainWindowFrame)
        bottomframe.pack(side=TOP)

        premium_button = Button(
            bottomframe, text="Entrar como Premium", command=self.open_premium_window
        )
        premium_button.pack(side=LEFT, padx=10, pady=10)

        guest_button = Button(
            bottomframe, text="Entrar como Convidado", command=self.open_guest_window
        )
        guest_button.pack(side=LEFT, padx=10, pady=10)

        self.notificationframe = Frame(self.mainWindowFrame)

        managerListenThread = threading.Thread(target=self.receive_from_manager)
        managerListenThread.start()

        self.mainWindow.after(self.interval, self.update_notification)
        self.mainWindow.protocol("WM_DELETE_WINDOW", lambda arg="SAIR_DA_APP": self.send_msg_manager(arg))
        self.mainWindow.mainloop()

        print("depois da mainloop")
        self.mainWindow.destroy()
        self.exit_flag = True

    def open_premium_window(self):
        if self.username.get().replace(" ", "") == "":
            self.notification_color = "red"
            self.notification = "Nome de usuário inválido"
            return
        self.login(self.username.get(), 1)
        while(self.user_type == None):
            continue

        self.show_group()

        while(self.my_group == None):
            continue

        print("----------------")
        print(f"available_users: {self.available_users}")
        print(f"my_group: {self.my_group}")
        print("----------------")

        self.mainWindowFrame.destroy()
        self.mainWindowFrame = Frame(self.mainWindow)
        self.mainWindow.title(f"Streaming {self.user_type}")
        self.mainWindowFrame.pack(side=TOP)

        userinfoframe = Frame(self.mainWindowFrame)
        userinfoframe.pack(side=TOP, padx="5")

        rightframe = Frame(userinfoframe)
        rightframe.pack(side=RIGHT, padx=("15","5"))

        nome = Label(
            rightframe, text=f"NOME: {self.user_name}", fg="blue"
        )
        nome.pack(side=BOTTOM)
        
        id = Label(
            rightframe, text=f"ID: {self.user_id}", fg="blue"
        )
        id.pack(side=TOP)

        titulo = Label(
            userinfoframe, text="Selecione um vídeo e uma resolução para reproduzir"
        )
        titulo.pack(pady="10")

        # Carrega a lista de vídeos do servidor
        OPTIONS = self.request_answer("LISTAR_VIDEOS").split("\n")

        self.video_name.set(OPTIONS[0])

        inputframe = Frame(self.mainWindowFrame)
        inputframe.pack(side=TOP, padx=10)

        listframe = Frame(inputframe)
        listframe.pack(side=BOTTOM)

        L1 = Label(listframe, text="Lista de Vídeos:")
        L1.pack(side = LEFT)

        w = OptionMenu(listframe, self.video_name, *OPTIONS)
        w.pack(side=RIGHT, padx="10")

        resolutionframe = Frame(inputframe)
        resolutionframe.pack(side=BOTTOM, pady="10")

        a_list = ["240p", "480p", "720p"]
        L2 = Label(resolutionframe, text="Resolução do Vídeo:")
        L2.pack(side = LEFT, padx="10")

        spinbox = Spinbox(resolutionframe, values=a_list, textvariable=self.resolution)
        spinbox.pack(side=RIGHT)

        playframe = Frame(self.mainWindowFrame)
        playframe.pack(side=TOP, pady=("10", "0"))

        play_button = Button(
            playframe, text="Reproduzir Vídeo", command=self.stream_selected_video
        )
        play_button.pack(side=LEFT, padx="10")

        play_group_button = Button(
            playframe, text="Reproduzir p/ Grupo", command=self.request_stream_group
        )
        play_group_button.pack(side=RIGHT, padx="10")

        self.notificationframe = Frame(self.mainWindowFrame)
        self.notificationframe.pack(side=BOTTOM)

        # guestThread = threading.Thread(target=self.wait_stream)
        # guestThread.start()
        
        self.display_group_button()

    def update_notification(self):
        if self.notification == None:
            self.mainWindow.after(self.interval, self.update_notification)
        else:
            self.notificationframe.destroy()
            self.notificationframe = Frame(self.mainWindowFrame)
            self.notificationframe.pack(side=BOTTOM)

            n = Label(self.notificationframe, text=f"{self.notification}", fg=self.notification_color)
            n.pack(side = LEFT, pady="5")
            
            if self.username.get().replace(" ", "") != "": 
                self.display_group_button()

            self.notification = None
            self.mainWindow.after(self.interval, self.update_notification)
            self.mainWindow.after(self.notification_interval, self.remove_notification)

    def remove_notification(self):
        self.notificationframe.destroy()
        self.notificationframe = Frame(self.mainWindowFrame)
        self.notificationframe.pack(side=BOTTOM)

    def display_group_button(self):
        if self.managerFrame != None:
            print("DESTRUINDO MANAGER FRAME")
            self.managerFrame.destroy()
        self.managerFrame = Frame(self.mainWindowFrame)
        self.managerFrame.pack(side=TOP, pady=("15", "0"))

        if(self.is_grouped):
            if(self.group_owner):
                self.manage_group_button = Button(
                    self.managerFrame, text="Gerenciar Grupo", command=self.open_group_manager_window
                )
                self.manage_group_button.pack(side=RIGHT, pady="5")

                self.show_group_button = Button(
                    self.managerFrame, text="Ver Grupo", command=self.show_group_notification
                )
                self.show_group_button.pack(side=RIGHT, pady="5", padx="5")
            else:
                self.show_group_button = Button(
                    self.managerFrame, text="Ver Grupo", command=self.show_group_notification
                )
                self.show_group_button.pack(side=BOTTOM, pady="5", padx="5")
        else:
            self.create_group_button = Button(
                self.managerFrame, text="Criar Grupo", command=self.create_group
            )
            self.create_group_button.pack(side=BOTTOM, pady="5")

    def open_group_manager_window(self):
        self.groupManagerWindow = Toplevel(self.mainWindow)

        self.groupManagerFrame = Frame(self.groupManagerWindow)
        self.groupManagerFrame.pack(side=BOTTOM, padx="10", pady="10")

        self.available_users = None 
        self.my_group = None

        self.groupManagerFrame.destroy()
        self.groupManagerFrame = Frame(self.groupManagerWindow)
        self.groupManagerFrame.pack(side=BOTTOM, padx="10", pady="10")

        self.show_group()
        self.show_available_users()

        while(self.available_users == None or self.my_group == None):
            continue

        print("----------------")
        print(f"available_users: {self.available_users}")
        print(f"my_group: {self.my_group}")
        print("----------------")

        self.user_to_add.set(self.available_users[0])
        self.user_to_remove.set(self.my_group[0])

        addFrame = Frame(self.groupManagerFrame)
        addFrame.pack(side=LEFT, padx="10", pady="10")

        L1 = Label(addFrame, text="Selecione um usuário para adicionar ao grupo:")
        L1.pack(side = TOP, pady="10")

        available = OptionMenu(addFrame, self.user_to_add, *self.available_users)
        available.pack(side=TOP, padx="10")

        add_button = Button(
            addFrame, text="Adicionar do Grupo", command=self.add_user_to_group
        )
        add_button.pack(side=TOP, padx="10", pady="10")

        removeFrame = Frame(self.groupManagerFrame)
        removeFrame.pack(side=LEFT, padx="10", pady="10")

        L2 = Label(removeFrame, text="Selecione um usuário para remover do grupo:")
        L2.pack(side = TOP, pady="10")

        in_group = OptionMenu(removeFrame, self.user_to_remove, *self.my_group)
        in_group.pack(side=TOP, padx="10")

        remove_button = Button(
            removeFrame, text="Remover do Grupo", command=self.remove_user_from_group
        )
        remove_button.pack(side=TOP, padx="10", pady="10")

        self.groupManagerWindow.protocol("WM_DELETE_WINDOW", self.close_group_manager_window)
        self.groupManagerWindow.mainloop()
        print("ANTES DESTROY MANAGER WINDOW")
        self.groupManagerWindow.destroy()

    def load_group_manager_frame(self):
        self.available_users = None 
        self.my_group = None

        self.groupManagerFrame.destroy()
        self.groupManagerFrame = Frame(self.groupManagerWindow)
        self.groupManagerFrame.pack(side=BOTTOM, padx="10", pady="10")

        self.show_group()
        self.show_available_users()

        while(self.available_users == None or self.my_group == None):
            continue

        print("----------------")
        print(f"available_users: {self.available_users}")
        print(f"my_group: {self.my_group}")
        print("----------------")

        self.user_to_add.set(self.available_users[0])
        self.user_to_remove.set(self.my_group[0])

        addFrame = Frame(self.groupManagerFrame)
        addFrame.pack(side=LEFT, padx="10", pady="10")

        L1 = Label(addFrame, text="Selecione um usuário para adicionar ao grupo:")
        L1.pack(side = TOP, pady="10")

        available = OptionMenu(addFrame, self.user_to_add, *self.available_users)
        available.pack(side=TOP, padx="10")

        add_button = Button(
            addFrame, text="Adicionar do Grupo", command=self.add_user_to_group
        )
        add_button.pack(side=TOP, padx="10", pady="10")

        removeFrame = Frame(self.groupManagerFrame)
        removeFrame.pack(side=LEFT, padx="10", pady="10")

        L2 = Label(removeFrame, text="Selecione um usuário para remover do grupo:")
        L2.pack(side = TOP, pady="10")

        in_group = OptionMenu(removeFrame, self.user_to_remove, *self.my_group)
        in_group.pack(side=TOP, padx="10")

        remove_button = Button(
            removeFrame, text="Remover do Grupo", command=self.remove_user_from_group
        )
        remove_button.pack(side=TOP, padx="10", pady="10")

        self.reload_manager = False
    
    def close_group_manager_window(self):
        print("REINICIANDO AVAILABLE_USERS E MY_GROUP")
        self.available_users = None
        self.my_group = None
        self.groupManagerWindow.quit()
    
    def open_guest_window(self):
        if self.username.get().replace(" ", "") == "":
            self.notification_color = "red"
            self.notification = "Nome de usuário inválido"
            return
        self.login(self.username.get(), 0)
        self.mainWindow.title("Streaming Premium")
        self.mainWindowFrame.destroy()
        self.mainWindowFrame = Frame(self.mainWindow)
        self.mainWindowFrame.pack(side=TOP)

        texto = Label(
            self.mainWindowFrame, text="Aguarde até que o streaming comece ..."
        )
        texto.pack(padx="10", pady="10")

        # Carrega a lista de vídeos do servidor
        OPTIONS = self.request_answer("LISTAR_VIDEOS").split("\n")

        self.video_name.set(OPTIONS[0])

        inputframe = Frame(self.mainWindowFrame)
        inputframe.pack(side=BOTTOM, padx=10)

        L1 = Label(inputframe, text="Lista de Vídeos:")
        L1.pack( side = LEFT)

        w = OptionMenu(inputframe, self.video_name, *OPTIONS)
        w.pack(side=RIGHT, padx="10", pady="10")

        guestThread = threading.Thread(target=self.wait_stream)
        guestThread.start()
   
    # Recebe os bytes do video através do servidor, decodifica e reproduz o vídeo
    def video_frame_decode(self):
        self.data = b""
        #time.sleep(2)
        while True:
            try:
                # verificao para ver se buffering esta acabando
                frame_segment, _ = self.client_socket.recvfrom(self.MAX_DGRAM_SIZE)
            except socket.timeout:
                continue
            if struct.unpack("B", frame_segment[0:1])[0] == 1:
                print("BUFFERING DONE")
                break

        # Inicia a thread que carrega os frames do buffer
        print("receive frames")

        # audio_buffer_thread = threading.Thread(target=self.audio_run,args=(audio_data,stream))
        bufferThread = threading.Thread(target=self.receive_frames)
        bufferThread.start()

        # A janela que contém o player do streaming é aberta
        self.playerWindow = Toplevel(self.mainWindow)

        self.canvas = Canvas(self.playerWindow, width=500, height=500)
        self.canvas.pack(side=TOP)

        submit_button = Button(
            self.playerWindow, text="Encerrar Streaming", command=self.finish_streaming
        )
        submit_button.pack(side=BOTTOM, padx=10, pady=10)

        # Inicia a thread que atualiza os frames do player
        windowThread = threading.Thread(target=self.update_image)
        windowThread.start()

        # audio_thread = threading.Thread(target=self.audio_run)
        # audio_thread.start()

        # Callback para quando a janela foi encerrada pelo botão superior
        self.playerWindow.protocol("WM_DELETE_WINDOW", self.finish_streaming)
        self.playerWindow.mainloop()

        # Aguarda até as tres threads terminarem
        windowThread.join()
        # audio_thread.join()
        bufferThread.join()

        print("reiniciando variaveis")
        self.finished = False
        self.finish_audio = False
        self.buffered = False

        self.playerWindow.destroy()

    def receive_frames(self):
        while not self.finished:
            try:
                frame_segment, _ = self.client_socket.recvfrom(self.MAX_DGRAM_SIZE)
            except socket.timeout:
                self.finished = True
                self.finish_audio = True
                self.close_stream()
                return

            # verificando se o segmento do frame atual eh maior que 1, se for adiciona seus dados a data
            message = struct.unpack("?", frame_segment[0:1])[0]
            if (message == True):
                frame_segment = frame_segment[1:]
                if struct.unpack("B", frame_segment[0:1])[0] > 1:
                    self.data += frame_segment[1:]
                # senao, comeca a realizar o decode dos bytes do video
                else:
                    self.data += frame_segment[1:]
                    self.image = cv2.imdecode(np.fromstring(self.data, dtype=np.uint8), 1)
                    if not self.buffered:
                        self.buffered = True
                    self.data = b""
            else:
                frame_segment = frame_segment[1:]
                self.audio_frame_list.put(frame_segment)

        self.close_stream()

    # Atualiza os frames na window que possui o player a cada self.interval até que o streamming seja finalizado
    def update_image(self):
        # Verifica se primeiro frame ja foi carregado
        if not self.buffered:
            self.playerWindow.after(self.interval, self.update_image)
            return
        try:
            self.image1 = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB) # to RGB
        except:
            while(self.image is None):
                pass
            self.image1 = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB) # to RGB
        self.image1 = Image.fromarray(self.image1)
        self.image1 = ImageTk.PhotoImage(image=self.image1)
        self.canvas.config(width=self.image1.width(), height=self.image1.height())
        self.canvas.create_image(0, 0, anchor=NW, image=self.image1)
        if not self.finished:
            self.playerWindow.after(self.interval, self.update_image)
    
    def audio_frame_decode(self):
        # self.client_socket.sendto(b'Ack', (self.server_addr, self.server_port))
        # criamos um objeto pyaudio para manipular o arquivo
        p = pyaudio.PyAudio()
        # criamos um fluxo de áudio. os dados para a geração do do fluxo são obtidos
        # a partir do próprio arquivo wave aberto anteriormente
        CHUNK = 1024
        FORMAT = pyaudio.paInt32
        stream = p.open(format=FORMAT,  # p.get_format_from_width(2),
                        channels=2,
                        rate=1411,
                        output=True,
                        frames_per_buffer=CHUNK)
        # lemos <chunck> bytes por vez do stream e o enviamos <write> para o dispositivo
        # padrão de saída de audio. Quando termina de ler sai fora do loop
        # audio_data = []
        # self.client_socket.settimeout(1)
        return stream, p

    # Reproduz o audio recebido do servidor
    def audio_run(self):
        stream, p = self.audio_frame_decode()
        while (not self.finish_audio):
            frame = self.audio_frame_list.get()
            stream.write(frame)
            print(".")
        print("pos loop audio")
        stream.stop_stream()
        print("pos stop stream")
        stream.close()
        print("pos close stream")
        p.terminate()
        self.audio_frame_list.queue.clear()
        print("fim audio")

    # Finaliza o streamming no servidor
    def close_stream(self):
        # envia pacote para parar com o envio dos pacotes do video para o servidor
        print("parando streaming")
        message = b"PARAR_STREAMING"
        print("mandando mensagem de parada")
        self.client_socket.sendto(message, (self.server_addr, self.server_port))
        print("mensagem de parada enviada")
        self.client_socket.settimeout(0.5)
        time.sleep(1)
        # resgatando possivel pacote que "sobrou" do envio do video do servidor
        try:
            _, _ = self.client_socket.recvfrom(self.MAX_DGRAM_SIZE)
        except socket.timeout:
            self.client_socket.settimeout(None)
        print("streamming parado")
        return
    
    # Encerra o loop da janela do player e indica que o streaming deve ser interrrompido
    def finish_streaming(self):
        self.finished = True
        self.finish_audio = True
        # quit ou destroy devem sempre ser mantidos na main thread
        self.playerWindow.quit()
    
    # Solicita o streaming do video selecionado
    def stream_selected_video(self):
        self.request_stream(self.video_name.get(), self.resolution.get())

    # Solicita o stream de um video de nome video_name e resolução resolution
    def request_stream(self, video_name, resolution):
        message = f"{'REPRODUZIR_VIDEO'} {video_name} {resolution} {self.user_id}" # ADICIONANDO USER_ID
        message = message.encode()
        self.client_socket.sendto(message, (self.server_addr, self.server_port))

        print(f"ENVIANDO PARA SERVIDOR DE STREAMING - {message}")

        message,_ = self.client_socket.recvfrom(2048)
        message = message.decode()
        print(f"RECEBIDO '{message}' DO SERVIDOR DE STREAMING")
        if("REPRODUZINDO" in message):
            pass
            video_thread = threading.Thread(target=self.video_frame_decode())
            # audio_thread = threading.Thread(target=self.audio_run())
            video_thread.daemon = True
            # audio_thread.daemon = True
            video_thread.start()
            # audio_thread.start()
        else:
            pass #MUDAR AQUI PARA MOSTRAR NOTIFICACAO CASO O USUARIO NAO FOR PREMIUM
    
    def wait_stream(self):
        stop = False
        while not stop:
            message,_ = self.client_socket.recvfrom(2048)
            message = message.decode()
            if message.startswith("REPRODUZINDO O VIDEO "):
                print(f"RECEBIDO '{message}' DO SERVIDOR DE STREAMING")
                video_thread = threading.Thread(target=self.video_frame_decode())
                video_thread.daemon = True
                video_thread.start()
                stop = True
            else:
                print("MSG INESPERADA, ERRO AO REPRODUZIR VIDEO")
    
    def request_stream_group(self):
        message = f"{'REPRODUZIR_VIDEO_GRUPO'} {self.video_name.get()} {self.resolution.get()} {self.user_id}" # ADICIONANDO USER_ID
        message = message.encode()
        self.client_socket.sendto(message, (self.server_addr, self.server_port))

        print(f"ENVIANDO PARA SERVIDOR DE STREAMING - {message}")

        message,_ = self.client_socket.recvfrom(2048)
        message = message.decode()
        print(f"RECEBIDO '{message}' DO SERVIDOR DE STREAMING")
        if("REPRODUZINDO" in message):
            pass
            video_thread = threading.Thread(target=self.video_frame_decode())
            # audio_thread = threading.Thread(target=self.audio_run())
            video_thread.daemon = True
            # audio_thread.daemon = True
            video_thread.start()
            # audio_thread.start()
        else:
            pass #MUDAR AQUI PARA MOSTRAR NOTIFICACAO CASO O USUARIO NAO FOR PREMIUM

    # Solicita uma resposta para o server através de uma request(mensagem)
    def request_answer(self, request):
        message = request.encode()
        self.client_socket.sendto(message, (self.server_addr, self.server_port))
        # esperando resposta do servidor
        answer, _ = self.client_socket.recvfrom(4096)
        return answer.decode("utf-8")

    def receive_from_manager(self):
        print(f"recebendo do manager como id:{self.user_id}")
        while not self.exit_flag:
            try:    
                message = self.manager_socket.recv(2048)
                print("msg recebida")
                message = message.decode()
                print(f"RECEBIDO '{message}' DO MANAGER")
                if message == "SAIR_DA_APP_ACK":
                    print("SAINDO ACK")
                    self.exit_flag = True
                    self.mainWindow.quit()
                elif message == "ENTRAR_NA_APP_ACK":
                    print("ENTRANDO ACK")
                    # TODO IR PARA A TELA LOGADA
                elif message.startswith("STATUS_DO_USUARIO"):
                    msg, self.user_id, self.user_name, self.user_type = message.split(" ")
                    if int(self.user_type):
                        self.user_type = "Premium"
                    else:
                        self.user_type = "Convidado"
                    print("MOSTRANDO STATUS DO USUARIO")
                elif message.startswith("CRIAR_GRUPO_ACK"):
                    print("GRUPO CRIADO ACK")
                    self.is_grouped = True
                    self.group_owner = True
                    self.display_group_button()
                    self.notification_color = "green"
                    self.notification = "Grupo criado com sucesso"
                elif message.startswith("GRUPO_DE_STREAMING"):
                    print(f"RECEBIDO {message} DO MANAGER")
                    message = message.replace("GRUPO_DE_STREAMING ","")
                    self.my_group = message.split(" ")
                    if len(self.my_group) < 2 and self.my_group[0] == "None":
                        self.my_group = ["Nenhum Disponível"]
                        self.is_grouped = False
                        self.group_owner = False
                    else:
                        if(self.my_group[0] == self.user_id):
                            self.group_owner = True
                        else:
                            self.group_owner = False
                        self.is_grouped = True
                        self.my_group = self.my_group[1:]
                        if self.my_group[0] == "None":
                            self.my_group = ["Nenhum Disponível"]
                    
                    if(self.notification_group):
                        self.notification_group = False
                        if self.my_group == ["Nenhum Disponível"]:
                            self.notification_color = "red"
                            self.notification = "Só tem você no seu grupo"
                        else:
                            self.notification = "Id dos outros membros: " + ", ".join(self.my_group)

                    print(f"ATUALIZANDO JANELA {self.my_group}")
                elif message.startswith("ADD_USUARIO_GRUPO_ACK"):
                    print("USUARIO ADICIONADO AO GRUPO")
                    self.is_grouped = True
                    self.notification_color = "green"
                    self.close_group_manager_window()
                    self.notification = "Usuário adicionado ao grupo"
                elif message.startswith("REMOVER_USUARIO_GRUPO_ACK"):
                    print("USUARIO REMOVIDO DO GRUPO")
                    self.is_grouped = True
                    self.notification_color = "red"
                    self.close_group_manager_window()
                    self.notification = "Usuário removido do grupo"
                elif message.startswith("LISTA_USUARIOS"):
                    print("RECEBIDO {message} DO MANAGER")
                    message = message.replace("LISTA_USUARIOS ","")
                    users = message.split(" ")
                    self.available_users = []
                    if len(users) > 1:
                        user = ""
                        for i in users:
                            if user == "":
                                user = i
                            else:
                                user += ": " + i
                                self.available_users.append(user)
                                user = ""
                    else:
                        self.available_users.append("Nenhum Disponível")
            except socket.timeout:
                continue
        self.manager_socket.close()
        print("fechou socket manager")

    def login(self, name, type): ##ESTA MOCKADO
        ip = self.manager_socket.getsockname()[0] ## get ip
        name = name.title().replace(" ", "")
        self.send_msg_manager(f"ENTRAR_NA_APP {name} {type} {ip}") ##ESTA MOCKADO  

    def send_msg_manager(self, msg):
        if(msg == "SAIR_DA_APP"):
            msg = f"{msg} {self.user_id}"
        print(f"ENVIANDO '{msg}' PARA O MANAGER")
        message = msg.encode()
        self.manager_socket.send(message)
        print(f"ENVIOU '{msg}' PARA O MANAGER")
    
    def create_group(self):
        message = f'CRIAR_GRUPO {self.user_id}'
        self.send_msg_manager(message)

    def show_available_users(self):
        message = 'LISTA_USUARIOS'
        self.send_msg_manager(message)
    
    def show_group(self):
        message = f'VER_GRUPO {self.user_id}'
        self.send_msg_manager(message)

    def show_group_notification(self):
        self.notification_group = True
        self.show_group()
    
    def add_user_to_group(self):
        data = self.user_to_add.get().split(":")
        if len(data) > 1 and data[0].isnumeric():
            print(f"ID VÁLIDO: {data[0]}")
            selected_id = data[0]
        else:
            selected_id = ""
            print(f"ID INVÁLIDO: {data[0]}")
            return
        message = f'ADD_USUARIO_GRUPO {self.user_id} {selected_id}'
        print(message)
        self.send_msg_manager(message)

    def remove_user_from_group(self):
        selected_id = self.user_to_remove.get()
        if not selected_id.isnumeric():
            print(f"ID INVÁLIDO: {selected_id}")
            return
        message = f'REMOVER_USUARIO_GRUPO {self.user_id} {selected_id}'
        print(message)
        self.send_msg_manager(message)

def main():
    if len(sys.argv) > 0:
        # endereco ipv4 do servidor de streaming por argumento
        server_addr = "127.0.0.1"
        client = ClientModule(server_addr)
        # iniciando servico de comunicacao com o servidor
        client.open_main_window()

if __name__ == "__main__":
    main()
