import cv2
import os
import numpy as np
import time  # Para pegar o horário
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import Model
from sklearn.metrics.pairwise import cosine_similarity

# Função para capturar imagem da webcam e retornar o frame capturado (não salva ainda)
def capture_webcam_image():
    cap = cv2.VideoCapture(0)  # Acessa a webcam
    ret, frame = cap.read()  # Captura o quadro
    if ret:
        cv2.imshow('Webcam', frame)
        cv2.waitKey(5000)  # Aguarda 5 segundos para visualização
    cap.release()
    cv2.destroyAllWindows()
    return frame

# Função para salvar a imagem capturada no disco, somente após o processo de verificação
def save_image(image, folder_name="captured_images"):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    timestamp = time.strftime("%Y%m%d_%H%M%S")  # Formato: AnoMêsDia_HoraMinutoSegundo
    image_name = f"{timestamp}.jpg"
    image_path = os.path.join(folder_name, image_name)

    # Salva a imagem capturada
    cv2.imwrite(image_path, image)
    return image_path

# Função para carregar e pré-processar a imagem
def load_and_preprocess_image(img_path):
    img = image.load_img(img_path, target_size=(224, 224))  # Redimensiona a imagem
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array)
    return img_array

# Função para extrair características usando o VGG16
def extract_features(model, img_array):
    features = model.predict(img_array)
    return features.flatten()

# Comparar duas imagens usando similaridade de cosseno
def compare_images(features1, features2):
    similarity = cosine_similarity([features1], [features2])
    return similarity[0][0]

# Função para exibir a imagem mais semelhante
def display_most_similar_image(img_path):
    img = cv2.imread(img_path)
    cv2.imshow('Imagem mais semelhante', img)
    cv2.waitKey(5000)  # Aguarda 5 segundos para visualização
    cv2.destroyAllWindows()

# Carregar o modelo VGG16 pré-treinado sem a camada de classificação final
base_model = VGG16(weights='imagenet')
model = Model(inputs=base_model.input, outputs=base_model.get_layer('fc1').output)

# Diretório onde as imagens estão armazenadas
image_directory = 'captured_images'
unrecognized_directory = 'unrecognized_images'

# Função para processar a imagem capturada
def process_image_comparison():
    # Captura uma nova imagem da webcam (não salva ainda)
    captured_frame = capture_webcam_image()

    # Lista de todas as imagens no diretório especificado
    image_files = [os.path.join(image_directory, f) for f in os.listdir(image_directory) if f.endswith(('jpg', 'jpeg', 'png'))]

    # Verificar se existem imagens no diretório
    if not image_files:
        print("A pessoa não está cadastrada.")
        # Adicionar a imagem à pasta de capturas já que não há imagens para comparar
        image_path = save_image(captured_frame, folder_name=image_directory)
        print(f"A imagem foi adicionada como {image_path}.")
        return False

    # Salvar a imagem capturada temporariamente para processamento
    temp_image_path = save_image(captured_frame, folder_name="temp_images")
    captured_img = load_and_preprocess_image(temp_image_path)

    # Extrair as características da nova imagem capturada
    captured_features = extract_features(model, captured_img)

    # Variáveis para armazenar a imagem mais semelhante e a maior similaridade
    best_image_path = None
    highest_similarity = -1
    similarity_threshold_high = 0.80  # Limite de 80% de similaridade
    similarity_threshold_low = 0.50  # Limite mínimo de 50% de similaridade

    # Iterar sobre todas as imagens no diretório
    for img_path in image_files:
        img = load_and_preprocess_image(img_path)
        img_features = extract_features(model, img)
        similarity = compare_images(captured_features, img_features)
        print(f'Similaridade com {img_path}: {similarity:.2f}')

        # Atualizar a imagem mais semelhante, se necessário
        if similarity > highest_similarity:
            highest_similarity = similarity
            best_image_path = img_path

    # Verifica se a maior similaridade está acima de 80%
    if highest_similarity >= similarity_threshold_high:
        print(f'A imagem mais semelhante é: {best_image_path} com similaridade {highest_similarity:.2f}')
        display_most_similar_image(best_image_path)
        # Remove a imagem temporária, pois a pessoa foi identificada
        os.remove(temp_image_path)
        return True
    # Verifica se a maior similaridade está entre 50% e 80%
    elif similarity_threshold_low <= highest_similarity < similarity_threshold_high:
        print(f"Similaridade intermediária ({highest_similarity:.2f}). Salvando imagem em 'unrecognized_images'.")
        # Mover imagem temporária para a pasta de não reconhecidas
        os.rename(temp_image_path, os.path.join(unrecognized_directory, os.path.basename(temp_image_path)))
        print(f"A imagem foi movida para a pasta 'unrecognized_images'.")
        return False
    else:
        print("A pessoa não foi identificada e a imagem foi descartada.")
        # Remove a imagem temporária pois a similaridade foi baixa
        os.remove(temp_image_path)
        return False

# Loop para capturar imagens até a pessoa ser identificada
def run_recognition_process():
    identified = False
    while not identified:
        identified = process_image_comparison()
        if not identified:
            print("Tentando novamente...")

# Iniciar o processo de comparação com repetição até identificação
run_recognition_process()