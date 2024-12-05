import cv2
import numpy as np
import os
import time
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import Model
from sklearn.metrics.pairwise import cosine_similarity
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

def initialize_model():
    base_model = VGG16(weights='imagenet')
    model = Model(inputs=base_model.input, outputs=base_model.get_layer('fc1').output)
    logging.info("Modelo IA inicializado.")
    return model

def load_and_preprocess_image(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    return preprocess_input(img_array)

def extract_features(model, img_array):
    return model.predict(img_array).flatten()

def process_image(captured_frame, model, vehicle_plate):
    registered_directory = 'registered_faces'
    captured_directory = 'captured_images'
    temp_directory = 'temp_images'
    unrecognized_directory = 'unrecognized_images'

    # Criar diretórios se não existirem
    for directory in [registered_directory, captured_directory, temp_directory, unrecognized_directory]:
        if not os.path.exists(directory):
            os.makedirs(directory)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    temp_image_path = os.path.join(temp_directory, f"temp_{timestamp}.jpg")
    cv2.imwrite(temp_image_path, captured_frame)

    captured_img = load_and_preprocess_image(temp_image_path)
    captured_features = extract_features(model, captured_img)

    similarity_threshold_high = 0.75

    # Tentar em registered_faces
    image_path_reg = os.path.join(registered_directory, f"{vehicle_plate}.jpg")
    if os.path.exists(image_path_reg):
        img_reg = load_and_preprocess_image(image_path_reg)
        img_reg_features = extract_features(model, img_reg)
        similarity_reg = cosine_similarity([captured_features], [img_reg_features])[0][0]

        if similarity_reg >= similarity_threshold_high:
            os.remove(temp_image_path)
            logging.info(f"Pessoa reconhecida (registered_faces) com similaridade {similarity_reg:.2f}.")
            return True, image_path_reg, similarity_reg, 'registered_faces'
        else:
            logging.info(f"Nível de similaridade em registered_faces insuficiente: {similarity_reg:.2f}")

    # Tentar em captured_images
    best_similarity_captured = 0
    best_image_captured = None
    if os.path.exists(captured_directory):
        for fname in os.listdir(captured_directory):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                # Verifica se a imagem começa com a placa
                if fname.startswith(vehicle_plate):
                    captured_path = os.path.join(captured_directory, fname)
                    img_captured = load_and_preprocess_image(captured_path)
                    img_captured_features = extract_features(model, img_captured)
                    similarity_captured = cosine_similarity([captured_features], [img_captured_features])[0][0]

                    if similarity_captured > best_similarity_captured:
                        best_similarity_captured = similarity_captured
                        best_image_captured = captured_path

        if best_image_captured and best_similarity_captured >= similarity_threshold_high:
            os.remove(temp_image_path)
            logging.info(f"Pessoa reconhecida (captured_images) com similaridade {best_similarity_captured:.2f}.")
            return True, best_image_captured, best_similarity_captured, 'captured_images'
        else:
            if best_image_captured:
                logging.info(f"Nível de similaridade em captured_images insuficiente: {best_similarity_captured:.2f}")

    # Não encontrou similaridade em nenhum dos dois
    new_image_path = os.path.join(captured_directory, f"{vehicle_plate}_{timestamp}.jpg")
    os.rename(temp_image_path, new_image_path)
    logging.info(f"Pessoa não reconhecida. Imagem salva em {new_image_path} e acesso liberado.")
    return False, None, None, None
