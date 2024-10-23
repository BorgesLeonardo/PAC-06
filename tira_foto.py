import serial
import time
import cv2

# Configura a comunicação serial
porta_serial = 'COM3'  # Ajuste para a porta correta (Windows) ou '/dev/ttyACM0' (Linux)
baud_rate = 9600  # Mesma taxa configurada no Arduino
arduino = serial.Serial(porta_serial, baud_rate, timeout=1)

# Aguarda o Arduino estar pronto
time.sleep(2)

def tirar_foto():
    # Inicializa a captura da câmera (0 para a primeira webcam conectada)
    camera = cv2.VideoCapture(0)

    # Lê a imagem da câmera
    ret, frame = camera.read()

    if ret:
        # Define o caminho completo para salvar a foto
        caminho_foto = 'C:/Users/Wuelliton/Pictures/foto_tirada.jpg'
        
        # Salva a imagem capturada no arquivo especificado
        cv2.imwrite(caminho_foto, frame)
        print(f"Foto capturada e salva como '{caminho_foto}'")
    else:
        print("Erro ao capturar a imagem")

    # Libera a câmera
    camera.release()

while True:
    if arduino.in_waiting > 0:
        try:
            # Tente decodificar usando ISO-8859-1
            comando = arduino.readline().decode('ISO-8859-1').strip()
            print(f"Comando recebido: {comando}")

            if comando == "TAKE_PHOTO":
                tirar_foto()  # Chama a função para tirar a foto
        except UnicodeDecodeError as e:
            print(f"Erro ao decodificar: {e}")
