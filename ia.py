import cv2
import numpy as np
import os
import time
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import Model
from sklearn.metrics.pairwise import cosine_similarity

# Carregar os classificadores de rosto e olhos Haar Cascade do OpenCV
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# Função para calcular a nitidez da imagem usando a variação Laplaciana
def calculate_blurriness(image):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray_image, cv2.CV_64F).var()
    return laplacian_var

# Função para redimensionar a imagem mantendo a proporção
def resize_image_with_aspect_ratio(image, width=None, height=None):
    (h, w) = image.shape[:2]
    
    if width is None and height is None:
        return image
    
    if width is None:
        aspect_ratio = height / float(h)
        new_width = int(w * aspect_ratio)
        return cv2.resize(image, (new_width, height), interpolation=cv2.INTER_AREA)
    
    if height is None:
        aspect_ratio = width / float(w)
        new_height = int(h * aspect_ratio)
        return cv2.resize(image, (width, new_height), interpolation=cv2.INTER_AREA)

# Função para detectar o rosto, olhos e capturar a imagem somente se o rosto estiver claro e a imagem não estiver tremida
# Função para detectar o rosto, olhos e capturar a imagem somente se o rosto estiver claro e a imagem não estiver tremida
def capture_image_when_face_and_eyes_detected(camera_index=0):
    cap = cv2.VideoCapture(camera_index)  # Acessa a webcam

    if not cap.isOpened():
        print(f"Erro ao acessar a câmera com índice {camera_index}.")
        return None

    print("Acesso à câmera bem-sucedido. Iniciando captura de imagem...")

    # Aumentar a resolução da captura
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    face_detected = False
    clean_frame = None  # Variável para armazenar a imagem limpa
    while not face_detected:
        ret, frame = cap.read()  # Captura o quadro da webcam
        if not ret:
            print("Erro ao capturar o quadro da câmera.")
            break

        # Armazena uma cópia limpa do frame antes de qualquer anotação
        clean_frame = frame.copy()

        # Converter para escala de cinza para melhorar a detecção de rosto e olhos
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detectar rostos no frame
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))

        # Desenhar retângulos ao redor dos rostos detectados
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # Região do rosto onde procuraremos os olhos (somente na metade superior)
            face_region_gray = gray_frame[y:y+h//2, x:x+w]
            face_region_color = frame[y:y+h//2, x:x+w]

            # Detectar olhos dentro da região do rosto
            eyes = eye_cascade.detectMultiScale(face_region_gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30), maxSize=(80, 80))

            # Verificar se os dois olhos foram detectados
            if len(eyes) != 2:
                cv2.putText(frame, "Olhos não detectados", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                continue

            # Verificar se os olhos estão aproximadamente na mesma linha horizontal
            eye1_y = eyes[0][1]
            eye2_y = eyes[1][1]
            if abs(eye1_y - eye2_y) > 15:  # Diferença muito grande entre os olhos
                cv2.putText(frame, "Olhos desalinhados", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                continue

            # Desenhar retângulos ao redor dos olhos
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(face_region_color, (ex, ey), (ex+ew, ey+eh), (255, 0, 0), 2)

            # Verificar a proporção do rosto em relação ao tamanho da imagem
            if w / frame.shape[1] < 0.2 or h / frame.shape[0] < 0.2:
                cv2.putText(frame, "Rosto muito pequeno", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                continue

            # Verificar a nitidez da imagem
            blurriness = calculate_blurriness(frame)
            cv2.putText(frame, f"Nitidez: {blurriness:.2f}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            if blurriness < 100:
                cv2.putText(frame, "Imagem desfocada", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                continue

            # Se o rosto for grande o suficiente, os olhos estiverem detectados e a imagem estiver clara
            cv2.putText(frame, "Capturando imagem", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            face_detected = True
            break

        # Mostrar o frame com as informações e retângulos durante a captura
        cv2.imshow('Detecção de Rosto e Olhos', frame)

        # Se o usuário pressionar a tecla 'q', o loop será interrompido
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    # Retornar a imagem limpa capturada
    return clean_frame if face_detected else None

# Função para salvar a imagem capturada no disco
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
def display_image_with_similarity(img_path, similarity):
    img = cv2.imread(img_path)
    cv2.putText(img, f"Similaridade: {similarity:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.imshow(f'Comparando com: {os.path.basename(img_path)}', img)
    # Mantém a janela aberta até o usuário fechar
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# Carregar o modelo VGG16 pré-treinado sem a camada de classificação final
base_model = VGG16(weights='imagenet')
model = Model(inputs=base_model.input, outputs=base_model.get_layer('fc1').output)

# Diretório onde as imagens estão armazenadas
image_directory = 'captured_images'
unrecognized_directory = 'unrecognized_images'

# Função para processar a imagem capturada
def process_image_comparison():
    # Captura uma nova imagem da webcam quando um rosto e olhos forem detectados
    captured_frame = capture_image_when_face_and_eyes_detected()

    if captured_frame is None:
        print("Nenhuma imagem foi capturada.")
        return False

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
    similarity_threshold_high = 0.75  # Limite de 80% de similaridade
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
        display_image_with_similarity(best_image_path, highest_similarity)
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
