import socket
import threading
import os
import cv2
import pickle
import struct
import math
import time
import wave
import pyaudio
import moviepy.editor as mp
from numpy import array
from moviepy.editor import *


class ServerModule():
    MAX_DGRAM_SIZE = 2 ** 16  # tamanho maximo do pacote udp
    MAX_FRAME_DGRAM_SIZE = MAX_DGRAM_SIZE - 64  # evitar overflow no pacote
    MAX_AUDIO_DGRAM_SIZE = math.ceil(MAX_DGRAM_SIZE - (2 ** 16)/2)


    def __init__(self):
        self.port = 6000
        self.server_socket = self.start_server()  # iniciando socket da thread principal
        self.client_stop_list = []  # lista de request para parada de streaming

        self.serve_clients()  # iniciando servico

    # iniciando server
    def start_server(self):  # iniciando novo socket udp
        addr = ("", self.port)

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(addr)

        print(f"SERVIDOR INICIADO {addr}")
        return server_socket

    def serve_clients(self):
        print(f"ESPERANDO PRIMEIRO COMANDO DE CLIENTE")
        while (True):
            try:
                data, client_address = self.server_socket.recvfrom(1024)  # recebendo pacote com comando do cliente
                print(f"COMANDO DE CLIENTE RECEBIDO {client_address[0]} - {data.decode('utf-8')}")
                if ("PARAR_STREAMING" == data.decode('utf-8')):  # request de parada de streaming
                    self.client_stop_list.append(client_address[0])
                    print(f"RECEBENDO DE {client_address[0]} - PARAR_STREAMING")
                    continue
                else:
                    client_thread = threading.Thread(target=self.single_client_serving, args=(
                    data, client_address))  # iniciando thread para servir um cliente
                    client_thread.daemon = True  # thread independente
                    client_thread.start()
            except KeyboardInterrupt:
                break
                
    def single_client_serving(self,data,client_address): #iniciando servico de um cliente qualquer
        data = data.decode('utf-8')

        if ("LISTAR_VIDEOS" == data):  # listando videos para o cliente
            server_socket = self.start_server()
            print(f"RECEBIDO DE {client_address[0]}- LISTAR_VIDEOS\n")
            message = self.list_videos()
            print(f"ENVIANDO PARA {client_address[0]}")
            print(message)
            server_socket.sendto(message, client_address)

        if ("REPRODUZIR_VIDEO" in data):  # streaming de um video para o cliente
            print(f"RECEBIDO DE {client_address[0]}- REPRODUZIR_VIDEO\n")
            server_socket_video = self.start_server()
            server_socket_audio = self.start_server()
            splitted_data = data.split(' ')
            self.conversor_audio(splitted_data[1]+"_"+splitted_data[2]+".mp4")
            audio_thread = threading.Thread(target=self.play_audio, args=(data,client_address,server_socket_audio,splitted_data))
            video_thread = threading.Thread(target=self.play_video, args=(data,client_address,server_socket_video,splitted_data))
            audio_thread.start()
            video_thread.start()
        return

    def list_videos(self):  # resgatando lista de videos disponiveis
        filenames = os.listdir('./videos/')
        output = set()
        for file in filenames:
            output.add(file.strip(".mp4").split("_")[0])
        message = "\n".join(output)
        message = message.encode()
        return message

    def play_video(self, data, client_address, server_socket,splitted_data):
        video_name = splitted_data[1]
        resolution = splitted_data[2]
        video_string = './videos/' + video_name + '_' + resolution + '.mp4'  # path do video
        video = cv2.VideoCapture(video_string)  # utilizando opencv para comecar a realizar o envio do video
        video.open(video_string)  # abrindo o video para envio

        while (video.isOpened()):
            cv2.waitKey(30)  # esperando para controlar o fps
            ret, frame = video.read()  # retorno se tem algum frame / resgatando frame atual
            if (not ret):  # se video.read nao tiver retornado nenhum frame ou se o cliente tiver pedido a parada do streaming
                video.release()
                server_socket.close()  # liberando video
                return
            if (client_address[0] in self.client_stop_list):
                self.client_stop_list.remove(client_address[0])  # removendo cliente da lista de paradas
                video.release()
                server_socket.close()
                return
            self.framing_video(frame, client_address, server_socket)

    def framing_video(self, frame, client_address, server_socket):  # segmentacao e envio do video
        _, buff_frame_data = cv2.imencode('.jpg', frame)  # transformando frame atual em um .jpg
        data = buff_frame_data.tostring()  # array de bytes do frame
        size = len(data)  # tamanho do frame atual

        number_of_segments = math.ceil(size / self.MAX_FRAME_DGRAM_SIZE)  # numero de segmentos/pacotes udp que serao enviados no frame atual

        start_pos = 0
        ending_pos = 0

        while (number_of_segments):
            ending_pos = min(size, start_pos + self.MAX_FRAME_DGRAM_SIZE)  # atualizando posicao final para envio
            server_socket.sendto(struct.pack("?", True) + struct.pack("B", number_of_segments) + data[start_pos:ending_pos],
                                 client_address)  # primeiro byte de cada segmento indica o numero do segmento do frame atual
            print(f"ENVIANDO FRAME VIDEO PARA {client_address[0]}")
            start_pos = ending_pos
            number_of_segments -= 1  # atualizando numero do segmento a ser enviado

    def conversor_audio(self, video_name):  # para pegar o audio do video e vonverter em um arquivo wav
        my_clip = mp.VideoFileClip(r"./videos/" + video_name)  # para importar o video

        while video_name[-1] != ".":  # para deletar o mp4 do nome do arquivo
            video_name = video_name[:-1]

        video_name = video_name + "wav"  # adicionando o tipo do arquivo no final do nome

        my_clip.audio.write_audiofile(r"./audios/" + video_name)  # transforma o audio em um arquivo wav

    def play_audio(self, data, client_address, server_socket,splitted_data):  # roda o audio
        # chunck mostra quantos pontos iremos ler por vez no arquivo wave
        audio_name = splitted_data[1]
        resolution = splitted_data[2]
        audio_string = './audios/' + audio_name + '_' + resolution + '.wav'  # path do audio

        # abrimos um arquivo
        wavfile = wave.open(audio_string, 'rb')

        # criamos um objeto pyaudio para manipular o arquivo
        audioobj = pyaudio.PyAudio()

        # criamos um fluxo de áudio. os dados para a geração do do fluxo são obtidos
        # a partir do próprio arquivo wave aberto anteriormente
        CHUNK = 1024
        stream = audioobj.open(
            format=audioobj.get_format_from_width(wavfile.getsampwidth()),
            channels=wavfile.getnchannels(),
            rate=wavfile.getframerate(),
            input=True,
            frames_per_buffer=CHUNK)

        print(f"RECEBIDA CHAMADA AUDIO PARA {client_address[0]} {server_socket}")

        print(f"ENVIANDO FRAME AUDIO PARA {client_address[0]} {server_socket}")
        data = None
        sample_rate = wavfile.getframerate()
        cnt = 0
        while True:
            if(client_address[0] in self.client_stop_list):
                self.client_stop_list.remove(client_address[0])
                break
            frame = wavfile.readframes(CHUNK)
            print("ENVIANDO AUDIO PARA "+ client_address[0])
            server_socket.sendto(struct.pack("?", False) + frame, client_address)
            # time.sleep(0.8 * self.MAX_AUDIO_DGRAM_SIZE / sample_rate)
            if cnt > (wavfile.getnframes() / CHUNK):
                break
            cnt += 1

        # message = 'FIM_AUDIO'
        # message = message.encode()
        # server_socket.sendto(message, client_address)
        print(f"FIM AUDIO PARA {client_address[0]}")
        # para de enviar o fluxo para o dispositivo de saida
        stream.stop_stream()
        # fecha o fluxo
        stream.close()
        # libera os recursos dedicados ao obj de audio
        audioobj.terminate()
        # fecha o arquivo wave
        wavfile.close()
        
def main():
    ServerModule()

if __name__ == "__main__":
    main()
