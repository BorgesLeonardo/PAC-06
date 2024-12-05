from flask import Flask, render_template, jsonify, request, redirect, url_for, Response, send_from_directory
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
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
import re

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

app = Flask(__name__)

# Inicializa a câmera
camera = cv2.VideoCapture(0)

# Lock para acesso à câmera
camera_lock = threading.Lock()

# Inicializa o modelo de IA
model = ia.initialize_model()

processing_status = {
    "status": "idle",
    "image_url": "",
    "plate_image_url": "",
    "message": "Aguardando detecção da placa do veículo.",
    "vehicle_plate": ""
}

vehicle_present = False
distance_threshold = 20

allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}

show_video_feed = False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def encontrar_arduino():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        logging.info(f"Verificando porta {port.device}: {port.description}")
        try:
            s = serial.Serial(port.device, 9600, timeout=1)
            time.sleep(2)
            s.reset_input_buffer()
            s.write(b'PYTHON_READY\n')
            s.close()
            return port.device
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
    global vehicle_present
    while True:
        if arduino.in_waiting > 0:
            line = arduino.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("DISTANCE:"):
                try:
                    distance = int(line.split(":")[1])
                    logging.info(f"Distância recebida: {distance} cm")
                    if distance < distance_threshold:
                        if not vehicle_present:
                            vehicle_present = True
                            if processing_status["status"] == "idle":
                                processing_status["status"] = "capturing_plate"
                                processing_status["message"] = "Capturando placa do veículo..."
                                threading.Thread(target=recognize_license_plate).start()
                    else:
                        if vehicle_present:
                            vehicle_present = False
                            if processing_status["status"] != "idle":
                                reset_processing_status()
                except ValueError:
                    pass

def gen_frames():
    while show_video_feed:
        with camera_lock:
            success, frame = camera.read()
            if not success:
                break
            else:
                # Desenhar sobreposição conforme o estado atual
                if processing_status["status"] == "capturing_plate":
                    # Desenhar retângulo com proporção 40:13
                    height, width, _ = frame.shape
                    rect_width = int(width * 0.8)
                    rect_height = int(rect_width * 13 / 40)
                    x = int((width - rect_width) / 2)
                    y = int((height - rect_height) / 2)
                    cv2.rectangle(frame, (x, y), (x + rect_width, y + rect_height), (0, 255, 0), 2)
                elif processing_status["status"] == "capturing_driver":
                    # Desenhar um círculo representando o rosto
                    height, width, _ = frame.shape
                    center_x = int(width / 2)
                    center_y = int(height / 2)
                    radius = int(min(width, height) * 0.3)
                    cv2.circle(frame, (center_x, center_y), radius, (0, 255, 0), 2)

                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    response = Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    # Desabilitar cache do vídeo
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

# Rota customizada para servir arquivos estáticos sem cache
@app.route('/static/<path:filename>')
def static_files(filename):
    response = send_from_directory('static', filename)
    # Desabilitar cache
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

def recognize_license_plate():
    global processing_status, show_video_feed
    processing_status["status"] = "capturing_plate"
    show_video_feed = True
    time.sleep(10)
    show_video_feed = False

    with camera_lock:
        ret, frame = camera.read()
        if not ret:
            logging.error("Erro ao capturar a imagem da câmera.")
            processing_status["status"] = "error"
            processing_status["message"] = "Erro ao capturar a imagem da câmera."
            return

        plate_image_path = "static/plate_image.jpg"
        try:
            cv2.imwrite(plate_image_path, frame)
            logging.info(f"Imagem da placa salva em: {os.path.abspath(plate_image_path)}")
            processing_status["plate_image_url"] = '/static/plate_image.jpg'
        except Exception as e:
            logging.error(f"Erro ao salvar a imagem da placa: {e}")
            processing_status["status"] = "error"
            processing_status["message"] = "Erro ao salvar a imagem da placa."
            return

        plate_text = perform_ocr(plate_image_path)

        if plate_text:
            logging.info(f"Placa reconhecida: {plate_text}")
            processing_status["vehicle_plate"] = plate_text
            db = get_database()
            vehicle = db.vehicles.find_one({"license_plate": plate_text})

            if vehicle:
                processing_status["status"] = "vehicle_registered"
                processing_status["message"] = "Veículo registrado. Capturando imagem do motorista..."
                threading.Thread(target=process_driver_image, args=(plate_text,)).start()
            else:
                logging.info(f"Veículo não registrado: {plate_text}")
                processing_status["status"] = "vehicle_not_registered"
                processing_status["message"] = f"Veículo {plate_text} não registrado. Acesso negado."
                enviar_comando_arduino('VEICULO_NAO_REGISTRADO')
                time.sleep(5)
                reset_processing_status()
        else:
            logging.info("Nenhuma placa detectada.")
            processing_status["status"] = "no_plate_detected"
            processing_status["message"] = "Nenhuma placa detectada. Tente novamente."
            time.sleep(5)
            reset_processing_status()

def perform_ocr(image_path):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    try:
        img = Image.open(image_path)
        plate_text = pytesseract.image_to_string(img, lang='por')
        plate_text = ''.join(filter(str.isalnum, plate_text))
        return plate_text.upper()
    except Exception as e:
        logging.error(f"Erro durante o OCR: {e}")
        return None

def valid_plate_format(plate_text):
    pattern_old = r'^[A-Z]{3}[0-9]{4}$'
    pattern_mercosul = r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$'
    return re.match(pattern_old, plate_text) or re.match(pattern_mercosul, plate_text)

def process_driver_image(vehicle_plate):
    global processing_status, show_video_feed
    processing_status["status"] = "capturing_driver"
    show_video_feed = True
    time.sleep(10)
    show_video_feed = False

    with camera_lock:
        ret, captured_frame = camera.read()
        if not ret:
            logging.error("Erro ao capturar a imagem do motorista.")
            processing_status["status"] = "error"
            processing_status["message"] = "Erro ao capturar a imagem do motorista."
            return

    image_path = "static/driver_image.jpg"
    try:
        cv2.imwrite(image_path, captured_frame)
        logging.info(f"Imagem do motorista salva em: {os.path.abspath(image_path)}")
        processing_status["image_url"] = '/static/driver_image.jpg'
    except Exception as e:
        logging.error(f"Erro ao salvar a imagem do motorista: {e}")
        processing_status["status"] = "error"
        processing_status["message"] = "Erro ao salvar a imagem do motorista."
        return

    processing_status["status"] = "driver_image_captured"
    processing_status["message"] = "Imagem do motorista capturada. Processando reconhecimento..."
    processing_status["vehicle_plate"] = vehicle_plate

    time.sleep(2)

    identificado, best_image_path, similaridade, origem = ia.process_image(captured_frame, model, vehicle_plate)

    if identificado:
        processing_status["status"] = "approved"
        processing_status["message"] = f"Acesso Permitido (Imagem reconhecida da pasta {origem})."
        enviar_comando_arduino('LIBERAR')
    else:
        # Não reconhecido em lugar nenhum, mas salva em captured_images e libera o acesso
        processing_status["status"] = "approved"
        processing_status["message"] = "Motorista não cadastrado previamente. Acesso liberado e imagem salva."
        enviar_comando_arduino('LIBERAR')

    logging.info(f"Resultado: {processing_status['message']} para a placa {vehicle_plate}")

    # Mantém o resultado por 5 segundos
    time.sleep(5)
    reset_processing_status()

def reset_processing_status():
    processing_status["status"] = "idle"
    processing_status["message"] = "Aguardando detecção da placa do veículo."
    processing_status["image_url"] = ""
    processing_status["plate_image_url"] = ""
    processing_status["vehicle_plate"] = ""

@app.route('/')
def index():
    return render_template('status.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        license_plate = request.form['license_plate'].upper()
        user_name = request.form['user_name']
        user_image = request.files['user_image']

        if user_image and allowed_file(user_image.filename):
            filename = secure_filename(user_image.filename)
            image_directory = 'registered_faces'
            if not os.path.exists(image_directory):
                os.makedirs(image_directory)

            image_path = os.path.join(image_directory, f"{license_plate}.jpg")
            user_image.save(image_path)

            db = get_database()
            existing_vehicle = db.vehicles.find_one({"license_plate": license_plate})
            if existing_vehicle:
                message = "Este veículo já está registrado."
                return render_template('register.html', message=message)
            else:
                db.vehicles.insert_one({
                    "license_plate": license_plate,
                    "user_name": user_name
                })
                message = "Veículo registrado com sucesso!"

            try:
                with open(image_path, "rb") as image_file:
                    image_data = image_file.read()
                    db.registered_users.insert_one({
                        "license_plate": license_plate,
                        "user_name": user_name,
                        "image": image_data,
                        "timestamp": datetime.datetime.now()
                    })
                logging.info("Dados do usuário salvos no banco de dados.")
            except Exception as e:
                logging.error(f"Erro ao salvar os dados no banco de dados: {e}")
                message = "Erro ao salvar os dados no banco de dados."
                return render_template('register.html', message=message)

            return render_template('register.html', message=message)
        else:
            message = "Arquivo de imagem inválido."
            return render_template('register.html', message=message)
    else:
        return render_template('register.html')

@app.route('/check_status')
def check_status():
    return jsonify(processing_status)

if __name__ == '__main__':
    try:
        db = get_database()
        collections = db.list_collection_names()
        logging.info(f"Conexão com o banco de dados estabelecida. Coleções existentes: {collections}")
    except Exception as e:
        logging.error(f"Erro ao conectar ao banco de dados: {e}")
        exit(1)

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

    try:
        app.run(debug=True, use_reloader=False)
    finally:
        camera.release()
        arduino.close()
