import cv2
import numpy as np
import os
import time
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import Model
from sklearn.metrics.pairwise import cosine_similarity
import logging

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carregar os classificadores de rosto e olhos Haar Cascade do OpenCV
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

def initialize_model():
    # Carregar o modelo VGG16 pré-treinado sem a camada de classificação final
    base_model = VGG16(weights='imagenet')
    model = Model(inputs=base_model.input, outputs=base_model.get_layer('fc1').output)
    logging.info("Modelo IA inicializado.")
    return model

# Função para detectar o rosto e os olhos e capturar a imagem apenas se o rosto estiver claro e sem desfoque
def capture_image_when_face_and_eyes_detected(cap):
    if not cap.isOpened():
        logging.error("Erro ao acessar a câmera.")
        return None

    logging.info("Iniciando captura de imagem...")

    face_detected = False
    clean_frame = None  # Variável para armazenar a imagem limpa
    start_time = time.time()
    timeout = 10  # Tempo máximo de espera em segundos

    while not face_detected:
        ret, frame = cap.read()
        if not ret:
            logging.error("Erro ao capturar o quadro da câmera.")
            break

        # Converter para escala de cinza para melhorar a detecção de rosto e olhos
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))

        # Verificar cada rosto e procurar olhos
        for (x, y, w, h) in faces:
            face_region_gray = gray_frame[y:y+h//2, x:x+w]
            eyes = eye_cascade.detectMultiScale(face_region_gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30), maxSize=(80, 80))

            # Se dois olhos forem detectados e estiverem alinhados
            if len(eyes) >= 2:
                face_detected = True
                clean_frame = frame.copy()
                break

        if time.time() - start_time > timeout:
            logging.warning("Tempo de espera excedido para detecção de rosto.")
            break

    return clean_frame if face_detected else None

def process_image(captured_frame, model):
    # Definir diretórios de comparação
    image_directory = 'captured_images'
    unrecognized_directory = 'unrecognized_images'
    temp_directory = 'temp_images'

    for directory in [image_directory, unrecognized_directory, temp_directory]:
        if not os.path.exists(directory):
            os.makedirs(directory)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    temp_image_path = os.path.join(temp_directory, f"temp_{timestamp}.jpg")
    cv2.imwrite(temp_image_path, captured_frame)

    # Carregar e extrair características da imagem capturada
    captured_img = load_and_preprocess_image(temp_image_path)
    captured_features = extract_features(model, captured_img)

    best_image_path = None
    highest_similarity = -1
    similarity_threshold_high = 0.75  # Limite de similaridade para aprovação

    # Verificar se existem imagens cadastradas
    image_files = [os.path.join(image_directory, f) for f in os.listdir(image_directory) if f.endswith(('jpg', 'jpeg', 'png'))]
    if not image_files:
        new_image_path = os.path.join(image_directory, f"user_{timestamp}.jpg")
        os.rename(temp_image_path, new_image_path)
        logging.info(f"Nenhuma imagem cadastrada. A imagem foi adicionada como {new_image_path}.")
        return False, None, None

    # Comparar com cada imagem cadastrada
    for img_path in image_files:
        img = load_and_preprocess_image(img_path)
        img_features = extract_features(model, img)
        similarity = cosine_similarity([captured_features], [img_features])[0][0]

        if similarity > highest_similarity:
            highest_similarity = similarity
            best_image_path = img_path

    # Verificar se a maior similaridade está acima do limite
    if highest_similarity >= similarity_threshold_high:
        os.remove(temp_image_path)
        logging.info(f"Pessoa reconhecida com similaridade {highest_similarity:.2f}.")
        return True, best_image_path, highest_similarity
    else:
        unrecognized_path = os.path.join(unrecognized_directory, f"unrecognized_{timestamp}.jpg")
        os.rename(temp_image_path, unrecognized_path)
        logging.info(f"Pessoa não reconhecida. Similaridade {highest_similarity:.2f}. Imagem salva em {unrecognized_path}.")
        return False, None, highest_similarity

def load_and_preprocess_image(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    return preprocess_input(img_array)

def extract_features(model, img_array):
    return model.predict(img_array).flatten()
