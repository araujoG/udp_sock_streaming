import queue
import sys
import socket
import struct
from tkinter import *
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading
import time
import threading, wave, pyaudio


class ClientModule:
    MAX_DGRAM_SIZE = 2 ** 16  # tamanho maximo de um datagrama udp

    def __init__(self, server_addr):
        # iniciando socket do cliente
        self.client_socket = self.start_client()
        # porta utilizada pelo servidor
        self.server_port = 6000
        # endereco ipv4 do servidor
        self.server_addr = server_addr

        self.mainWindow = Tk()
        self.mainWindow.title("Streaming")
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

        self.data = b""

    # Inicializa o socket do client
    def start_client(self):
        port = 5000
        addr = ("", port)

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.bind(addr)

        return client_socket

    # Solicita o stream de um video de nome video_name e resolução resolution
    def request_stream(self, video_name, resolution):
        message = f"{'REPRODUZIR_VIDEO'} {video_name} {resolution}"
        message = message.encode()
        self.client_socket.sendto(message, (self.server_addr, self.server_port))

        print(f"ENVIANDO PARA SERVIDOR DE STREAMING - {message}")

        video_thread = threading.Thread(target=self.video_frame_decode())
        # audio_thread = threading.Thread(target=self.audio_run())
        video_thread.daemon = True
        # audio_thread.daemon = True
        video_thread.start()
        # audio_thread.start()

    # Solicita o streaming do video selecionado
    def stream_selected_video(self):
        self.request_stream(self.video_name.get(), self.resolution.get())

    def audio_run(self):
        stream, p = self.audio_frame_decode()
        while (not self.finished):
            frame = self.audio_frame_list.get()
            stream.write(frame)

        stream.stop_stream()
        stream.close()
        p.terminate()

    def audio_frame_decode(self):
        # self.client_socket.sendto(b'Ack', (self.server_addr, self.server_port))
        # criamos um objeto pyaudio para manipular o arquivo
        p = pyaudio.PyAudio()
        # criamos um fluxo de áudio. os dados para a geração do do fluxo são obtidos
        # a partir do próprio arquivo wave aberto anteriormente
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        stream = p.open(format=FORMAT,  # p.get_format_from_width(2),
                        channels=2,
                        rate=44100,
                        output=True,
                        frames_per_buffer=CHUNK)
        # lemos <chunck> bytes por vez do stream e o enviamos <write> para o dispositivo
        # padrão de saída de audio. Quando termina de ler sai fora do loop
        # audio_data = []
        # self.client_socket.settimeout(1)
        return stream, p

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

        audio_thread = threading.Thread(target=self.audio_run)
        audio_thread.start()

        # Callback para quando a janela foi encerrad pelo botão superior
        self.playerWindow.protocol("WM_DELETE_WINDOW", self.finish_streaming)
        self.playerWindow.mainloop()

        # Aguarda até as duas threads terminarem
        windowThread.join()
        bufferThread.join()

        print("reiniciando variaveis")
        self.finished = False
        self.buffered = False

        self.playerWindow.destroy()

    # Encerra o loop da janela do player e indica que o streaming deve ser interrrompido
    def finish_streaming(self):
        self.finished = True
        # quit ou destroy devem sempre ser mantidos na main thread
        self.playerWindow.quit()

    # Carrega a janela principal da aplicação
    def main_window(self):
        texto = Label(
            self.mainWindow, text="Selecione um vídeo e uma resolução para reproduzir"
        )
        texto.pack(padx="10", pady="10")
        # Carrega a lista de vídeos do servidor
        OPTIONS = self.request_answer("LISTAR_VIDEOS").split("\n")

        self.video_name.set(OPTIONS[0])

        bottomframe = Frame(self.mainWindow)
        bottomframe.pack(side=BOTTOM)

        inputframe = Frame(self.mainWindow)
        inputframe.pack(side=BOTTOM, padx=10)

        w = OptionMenu(inputframe, self.video_name, *OPTIONS)
        w.pack(side=LEFT)

        a_list = ["240p", "480p", "720p"]
        spinbox = Spinbox(inputframe, values=a_list, textvariable=self.resolution)
        spinbox.pack(side=LEFT)

        submit_button = Button(
            bottomframe, text="Reproduzir", command=self.stream_selected_video
        )
        submit_button.pack(side=BOTTOM, padx=10, pady=10)

        self.mainWindow.mainloop()

    def receive_frames(self):
        while not self.finished:
            try:
                frame_segment, _ = self.client_socket.recvfrom(self.MAX_DGRAM_SIZE)
            except socket.timeout:
                self.finished = True
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
        self.image1 = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)  # to RGB
        self.image1 = Image.fromarray(self.image1)
        self.image1 = ImageTk.PhotoImage(image=self.image1)
        self.canvas.config(width=self.image1.width(), height=self.image1.height())
        self.canvas.create_image(0, 0, anchor=NW, image=self.image1)
        if not self.finished:
            self.playerWindow.after(self.interval, self.update_image)

    # Finaliza o streamming no servidor
    def close_stream(self):
        # envia pacote para parar com o envio dos pacotes do video para o servidor
        print("parando streaming")
        message = b"PARAR_STREAMING"
        self.client_socket.sendto(message, (self.server_addr, self.server_port))
        # time.sleep(1)
        # resgatando possivel pacote que "sobrou" do envio do video do servidor
        try:
            _, _ = self.client_socket.recvfrom(self.MAX_DGRAM_SIZE)
        except socket.timeout:
            pass
        return

    # Solicita uma resposta para o server através de uma request(mensagem)
    def request_answer(self, request):
        message = request.encode()
        self.client_socket.sendto(message, (self.server_addr, self.server_port))
        # esperando resposta do servidor
        answer, _ = self.client_socket.recvfrom(4096)
        return answer.decode("utf-8")


def main():
    if len(sys.argv) > 1:
        # endereco ipv4 do servidor de streaming por argumento
        server_addr = sys.argv[1]
        client = ClientModule(server_addr)
        # iniciando servico de comunicacao com o servidor
        client.main_window()


if __name__ == "__main__":
    main()
