
# Estacione Seguro

**Estacione Seguro** é um sistema inteligente para melhorar a segurança em estacionamentos, utilizando tecnologias de **Internet das Coisas (IoT)** e **Inteligência Artificial (IA)**. O sistema realiza o monitoramento e identificação de veículos e motoristas, prevenindo furtos ao verificar se o motorista e o carro são os mesmos na entrada e saída.

## Visão Geral do Projeto

O projeto é focado em criar um ambiente de segurança completo para estacionamentos, onde câmeras capturam imagens dos motoristas e placas dos veículos na entrada e saída. Essas informações são processadas por uma IA, que faz o reconhecimento facial e de placas para garantir a autenticidade dos dados.

## Funcionalidades

### Requisitos Funcionais

1. **Identificação de Entrada e Saída**: O sistema detecta a entrada e saída de veículos automaticamente.
2. **Captura de Imagens**: Ao detectar um veículo, o sistema captura a imagem do motorista e da placa.
3. **Armazenamento de Dados**: Informações como imagens, horários e detalhes de veículos e motoristas são armazenados de forma segura no banco de dados.
4. **Comparação de Dados**: O sistema compara os dados de entrada e saída para verificar a correspondência entre o motorista e o veículo.
5. **Notificação de Alerta**: Em caso de discrepância ou suspeita de roubo, o sistema envia alertas ao proprietário e à equipe de segurança.
6. **Cadastro de Motoristas e Veículos**: Caso um veículo não esteja registrado, o sistema solicita o cadastro no momento da entrada.
7. **Verificação de Assinaturas ou Tickets**: O sistema verifica se o veículo tem uma assinatura válida ou um ticket de estacionamento.
8. **Notificações em Tempo Real**: Alertas em tempo real para a equipe de segurança quando forem detectadas anomalias.

### Requisitos Não Funcionais

1. **Alta Resolução**: As câmeras devem capturar imagens de alta qualidade para garantir precisão.
2. **Desempenho da IA**: O reconhecimento facial e de placas deve ocorrer em menos de 2 segundos.
3. **Segurança dos Dados**: Implementação de criptografia para proteger informações sensíveis.
4. **Operação 24/7**: O sistema deve funcionar continuamente, com alta disponibilidade.
5. **Escalabilidade**: Suporte para múltiplos pontos de entrada e saída sem perda de desempenho.

## Arquitetura do Sistema

O sistema é composto pelos seguintes componentes:

- **Câmeras de Segurança**: Capturam as imagens de veículos e motoristas.
- **Servidor de IA**: Responsável por processar as imagens e realizar o reconhecimento facial e de placas.
- **Banco de Dados (MongoDB)**: Armazena de forma segura as informações dos motoristas, veículos e eventos.
- **Placa Arduino**: Controla os sensores de movimento e proximidade para detectar veículos.
- **Sensores de Movimento/Proximidade**: Ativam as câmeras ao detectar a presença de veículos.
- **Sistema de Redes**: Conecta todos os dispositivos IoT ao servidor de IA e ao banco de dados.

## Tecnologias Utilizadas

- **C/C++**: Para comunicação com o Arduino e controle dos sensores.
- **Python**: Para o desenvolvimento da IA e processamento de imagens.
- **MongoDB**: Armazenamento seguro das informações.
- **IA/Deep Learning**: Algoritmos de reconhecimento facial e de placas.
- **Arduino**: Integração de sensores de movimento e câmeras.

## Fluxo de Funcionamento

1. **Entrada**:
   - O sensor detecta a chegada de um veículo e aciona a câmera.
   - A câmera captura a imagem do motorista e da placa do veículo.
   - A imagem é enviada para o servidor, onde é processada e armazenada no banco de dados.

2. **Análise**:
   - O servidor de IA faz o reconhecimento facial e de placas.
   - O sistema verifica se o motorista e o veículo estão cadastrados no banco de dados.
   - Caso não estejam, o cadastro é solicitado.

3. **Saída**:
   - Ao sair, o sistema repete o processo de captura de imagem e compara com os dados de entrada.
   - Se houver inconsistência, o sistema gera um alerta e notifica o proprietário e a equipe de segurança.

## Como Executar o Projeto

1. Clone o repositório:

```bash
git clone https://github.com/seu-usuario/estacione-seguro.git
```

2. Instale as dependências necessárias:

```bash
pip install -r requirements.txt
```

3. Conecte os dispositivos (câmeras, sensores, Arduino) de acordo com o diagrama de hardware.

4. Execute o servidor de IA:

```bash
python main.py
```

5. Acesse a interface web ou mobile para gerenciar o estacionamento.

## Contribuições

Para contribuir com o projeto, faça um fork do repositório, crie uma nova branch, adicione suas alterações e submeta um pull request. 

```bash
git checkout -b minha-feature
```

```bash
git push origin minha-feature
```

## Alunos/Desenvolvedores 
Alexandre Vieira, Edson Polucena, Leonardo Borges, Richard Riedo, Wueliton Santos


## Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
