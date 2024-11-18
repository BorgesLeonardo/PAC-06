// Define os pinos de Trig, Echo, LEDs vermelho e verde
const int trigPin = 25;
const int echoPin = 26;
const int redLedPin = 17;   // Pino do LED vermelho
const int greenLedPin = 16; // Pino do LED verde

// Variáveis para armazenar o tempo e a distância
long duration;
int distance;
int distanceThreshold = 20; // Distância em cm para acionar a captura

bool arduinoIdentificado = false;  // Flag para indicar se o Arduino já foi identificado pelo Python
bool isProcessing = false; // Flag para indicar se está processando
bool personPresent = false; // Flag para indicar se a pessoa está próxima
bool accessGranted = false; // Flag para indicar se o acesso foi liberado

void setup() {
  Serial.begin(9600);
  delay(2000); // Aguarda 2 segundos para estabilizar a comunicação serial
  Serial.println("ARDUINO_READY");  // Envia mensagem de identificação

  // Configura os pinos
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(redLedPin, OUTPUT);
  pinMode(greenLedPin, OUTPUT);

  // Garante que os LEDs estejam no estado inicial
  digitalWrite(redLedPin, HIGH);  // LED vermelho aceso inicialmente
  digitalWrite(greenLedPin, LOW); // LED verde apagado inicialmente
}

void loop() {
  if (!arduinoIdentificado) {
    // Aguarda o Python enviar "PYTHON_READY"
    if (Serial.available()) {
      String comando = Serial.readStringUntil('\n');
      comando.trim();
      if (comando == "PYTHON_READY") {
        arduinoIdentificado = true;
        Serial.println("ARDUINO_CONFIRMED"); // Opcional: confirma a identificação
        Serial.println("Arduino identificado pelo Python.");
      }
    }
    return;  // Aguarda até ser identificado
  }

  // Limpa o pino Trigger
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  // Emite um pulso de 10 microsegundos no Trigger
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Lê o tempo de retorno no Echo
  duration = pulseIn(echoPin, HIGH);

  // Calcula a distância em cm
  distance = duration * 0.034 / 2;

  // Envia a distância para o Python
  if (!isProcessing) {
    Serial.print("DISTANCE:");
    Serial.println(distance);
  }

  // Verifica se a pessoa está presente ou não
  if (distance < distanceThreshold) {
    personPresent = true;
  } else {
    if (personPresent) {
      // Pessoa se afastou
      personPresent = false;
      if (accessGranted) {
        // Se o acesso foi liberado e a pessoa se afastou, retorna ao estado inicial
        digitalWrite(greenLedPin, LOW); // Apaga o LED verde
        digitalWrite(redLedPin, HIGH);  // Acende o LED vermelho
        accessGranted = false;
      }
    }
  }

  // Verifica se recebeu algum comando do Python
  if (Serial.available()) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    Serial.print("Comando recebido: ");
    Serial.println(comando); // Adicionado para debug

    if (comando == "LIBERAR") {
      digitalWrite(greenLedPin, HIGH); // Acende o LED verde
      digitalWrite(redLedPin, LOW);    // Apaga o LED vermelho
      isProcessing = false;
      accessGranted = true; // Marca que o acesso foi liberado
    } else if (comando == "RECUSAR") {
      digitalWrite(greenLedPin, LOW);  // Apaga o LED verde
      digitalWrite(redLedPin, HIGH);   // Acende o LED vermelho
      isProcessing = false;
      accessGranted = false; // Certifique-se de que o acesso não está liberado
    } else if (comando == "PROCESSANDO") {
      isProcessing = true;
      blinkRedLed(); // Inicia o piscar do LED vermelho
    }
  }

  delay(200); // Aguarda um pouco antes de realizar a próxima ação
}

void blinkRedLed() {
  unsigned long currentMillis = millis();
  unsigned long previousMillis = 0;
  const long interval = 500; // Intervalo de 500ms para piscar

  while (isProcessing) {
    if (Serial.available()) {
      String comando = Serial.readStringUntil('\n');
      comando.trim();
      Serial.print("Comando recebido durante o processamento: ");
      Serial.println(comando); // Adicionado para debug

      if (comando == "LIBERAR") {
        digitalWrite(greenLedPin, HIGH); // Acende o LED verde
        digitalWrite(redLedPin, LOW);    // Apaga o LED vermelho
        isProcessing = false;
        accessGranted = true;
        return;
      } else if (comando == "RECUSAR") {
        digitalWrite(greenLedPin, LOW);  // Apaga o LED verde
        digitalWrite(redLedPin, HIGH);   // Acende o LED vermelho
        isProcessing = false;
        accessGranted = false;
        return;
      }
    }

    currentMillis = millis();

    if (currentMillis - previousMillis >= interval) {
      previousMillis = currentMillis;
      int state = digitalRead(redLedPin);
      digitalWrite(redLedPin, !state); // Inverte o estado do LED vermelho
    }
  }

  digitalWrite(redLedPin, LOW); // Garante que o LED vermelho esteja apagado
}