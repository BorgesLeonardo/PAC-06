from flask import Flask, render_template, jsonify
import cv2
import threading
import serial
import serial.tools.list_ports
import time
import os
import ia
from config_bd import get_database
import datetime
import logging

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Inicializa a câmera
camera = cv2.VideoCapture(0)

# Lock para sincronizar o acesso à câmera
camera_lock = threading.Lock()

# Inicializa o modelo de IA
model = ia.initialize_model()

# Variáveis para o status de processamento
processing_status = {
    "status": "idle",
    "image_url": "",
    "message": "Por favor, aproxime-se do sensor para iniciar a captura."
}

distance_threshold = 20
person_present = False  # Flag para indicar se a pessoa está próxima do sensor

def encontrar_arduino():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        logging.info(f"Verificando porta {port.device}: {port.description}")
        try:
            s = serial.Serial(port.device, 9600, timeout=1)
            time.sleep(2)
            s.reset_input_buffer()
            line = s.readline().decode('utf-8', errors='ignore').strip()
            if "ARDUINO_READY" in line:
                logging.info(f"Arduino encontrado na porta: {port.device}")
                s.write(b'PYTHON_READY\n')
                s.close()
                return port.device
            s.close()
        except Exception as e:
            logging.error(f"Erro ao verificar porta {port.device}: {e}")
            continue
    logging.error("Arduino não encontrado. Verifique a conexão e tente novamente.")
    return None

def enviar_comando_arduino(comando):
    try:
        arduino.write((comando + '\n').encode())
    except Exception as e:
        logging.error(f"Erro ao enviar comando para o Arduino: {e}")

def listen_serial():
    global processing_status
    global person_present
    while True:
        if arduino.in_waiting > 0:
            line = arduino.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("DISTANCE:"):
                try:
                    distance = int(line.split(":")[1])
                    logging.info(f"Distância recebida: {distance} cm")
                    if distance < distance_threshold:
                        if not person_present:
                            person_present = True
                            if processing_status["status"] == "idle":
                                processing_status["status"] = "processing"
                                processing_status["message"] = "Capturando imagem..."
                                threading.Thread(target=process_image_from_trigger).start()
                    else:
                        if person_present:
                            person_present = False
                            if processing_status["status"] != "idle":
                                processing_status["status"] = "idle"
                                processing_status["message"] = "Por favor, aproxime-se do sensor para iniciar a captura."
                                processing_status["image_url"] = ""
                except ValueError:
                    pass

def process_image_from_trigger():
    global processing_status
    with camera_lock:
        # Captura a imagem quando um rosto e olhos são detectados
        captured_frame = ia.capture_image_when_face_and_eyes_detected(camera)

    if captured_frame is None:
        logging.error("Não foi possível capturar uma imagem válida.")
        processing_status["status"] = "error"
        processing_status["message"] = "Erro na captura da imagem."
        return

    # Salva a imagem capturada
    image_path = "static/captured_image.jpg"
    try:
        cv2.imwrite(image_path, captured_frame)
        logging.info(f"Imagem salva em: {os.path.abspath(image_path)}")
        processing_status["image_url"] = '/static/captured_image.jpg'
    except Exception as e:
        logging.error(f"Erro ao salvar a imagem: {e}")
        processing_status["status"] = "error"
        processing_status["message"] = "Erro ao salvar a imagem."
        return

    # Salva a imagem no banco de dados
    try:
        db = get_database()
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            db.captured_images.insert_one({
                "timestamp": datetime.datetime.now(),
                "image": image_data
            })
        logging.info("Imagem enviada para o banco de dados.")
    except Exception as e:
        logging.error(f"Erro ao salvar a imagem no banco de dados: {e}")
        processing_status["status"] = "error"
        processing_status["message"] = "Erro ao salvar a imagem no banco de dados."
        return

    # Atualiza o status para exibir a imagem capturada imediatamente
    processing_status["status"] = "image_captured"
    processing_status["message"] = "Imagem capturada, processando reconhecimento..."

    # **Atualiza o status para indicar que o reconhecimento está sendo processado**
    processing_status["status"] = "recognition_processing"
    processing_status["message"] = "Processando o reconhecimento..."

    # Envia comando ao Arduino para piscar o LED vermelho
    enviar_comando_arduino('PROCESSANDO')

    # Processa a imagem usando a IA para reconhecimento
    identificado, best_image_path, similaridade = ia.process_image(captured_frame, model)

    # Atualiza o status após o processamento
    if identificado:
        resultado = "Acesso Permitido"
        processing_status["status"] = "approved"
        processing_status["message"] = "Acesso Permitido"
        enviar_comando_arduino('LIBERAR')
    else:
        resultado = "Acesso Negado"
        processing_status["status"] = "denied"
        processing_status["message"] = "Acesso Negado"
        enviar_comando_arduino('RECUSAR')

    logging.info(f"Resultado: {resultado}")

    # Opcional: Aguarda alguns segundos antes de permitir nova captura
    time.sleep(5)
    # Não resetamos processing_status["status"] aqui, pois a lógica no listen_serial() controla isso

@app.route('/')
def index():
    return render_template('status.html')

@app.route('/check_status')
def check_status():
    #logging.debug("Status atual:", processing_status)  # Para depuração
    return jsonify(processing_status)

if __name__ == '__main__':
    porta_serial = encontrar_arduino()
    if porta_serial is None:
        logging.error("Não foi possível encontrar o Arduino.")
        exit(1)

    arduino = serial.Serial(porta_serial, 9600, timeout=1)
    time.sleep(2)
    arduino.write(b'PYTHON_READY\n')

    serial_thread = threading.Thread(target=listen_serial)
    serial_thread.daemon = True
    serial_thread.start()

    # Teste de conexão com o banco de dados
    try:
        db = get_database()
        collections = db.list_collection_names()
        logging.info(f"Conexão com o banco de dados estabelecida. Coleções existentes: {collections}")
    except Exception as e:
        logging.error(f"Erro ao conectar ao banco de dados: {e}")
        exit(1)

    try:
        app.run(debug=True, use_reloader=False)
    finally:
        camera.release()
        arduino.close()
