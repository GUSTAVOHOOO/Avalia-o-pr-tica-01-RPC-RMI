# PRD - Jogo Multijogador de Adivinhação via RPC/RMI
## Sistemas Distribuidos e Tecnologias (CC5SDT) - UTFPR

---

## 1. RESUMO DO PROJETO

| Campo | Descricao |
|-------|-----------|
| **Disciplina** | Sistemas Distribuidos e Tecnologias (CC5SDT) |
| **Instituicao** | UTFPR - Campus Santa Helena |
| **Professor** | Rafael Keller Tesser |
| **Semestre** | 2026-1 |
| **Peso** | 0,3 (3 pontos na nota final) |
| **Tema** | Jogo multijogador de adivinhacao usando RPC/RMI |
| **Equipe** | 2 integrantes |
| **Linguagem** | Livre escolha (recomendado: Python ou Java) |
| **Comunicacao** | Exclusivamente via RPC ou RMI |

### 1.1 Conceito do Jogo

Cada jogador recebe uma imagem de um objeto. A cada turno, os jogadores enviam dicas curtas (uma palavra) sobre seus objetos. Os outros jogadores podem tentar adivinhar ou esperar. Existe um sistema de troca de dicas privada entre dois jogadores, espionagem (com risco de penalidade), chat em tempo real, arbitragem de respostas e sistema de pontuacao complexo.

---

## 2. ANALISE DE REQUISITOS

### 2.1 Requisitos Funcionais (RF)

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-01 | Cada jogador recebe uma imagem de um objeto no inicio da rodada | Alta |
| RF-02 | Sistema de turnos com limite maximo configuravel | Alta |
| RF-03 | A cada turno, cada jogador envia uma dica curta (uma palavra) para todos | Alta |
| RF-04 | Jogadores podem tentar adivinhar o objeto ou esperar o proximo turno | Alta |
| RF-05 | Troca de dicas privada entre dois jogadores (uma palavra cada, aceitacao mutua) | Alta |
| RF-06 | Dicas trocadas privadamente nao precisam ser verdadeiras | Alta |
| RF-07 | Notificacao publica quando dois jogadores trocam dicas (sem revelar conteudo) | Alta |
| RF-08 | Mecanica de espionagem: espiar troca de dicas com chance de ser descoberto | Alta |
| RF-09 | Penalidade de pontos se o espiao for descoberto | Alta |
| RF-10 | Mecanismo de arbitragem para validar palpites (multiplas palavras para mesmo objeto) | Alta |
| RF-11 | Opcao de finalizar jogo ou continuar com novos objetos ao fim dos turnos | Media |
| RF-12 | Sistema de pontuacao automatico (ver RF-20 a RF-23) | Alta |
| RF-13 | Chat em tempo real separado das funcionalidades do jogo | Alta |
| RF-14 | Separacao clara: chat nao e usado para dicas, trocas, espionagem ou palpites | Alta |
| RF-15 | Comunicacao exclusivamente via RPC ou RMI (proibido sockets diretos) | Alta |
| RF-16 | Suporte a conexao direta entre clientes ou via servidor intermediario | Media |
| RF-17 | Relatorio tecnico com introdulcao ao framework RPC escolhido e justificativa | Alta |
| RF-18 | Relatorio com descricao do desenvolvimento, capturas de tela e trechos de codigo | Alta |
| RF-19 | Instrucoes de instalacao e uso no relatorio | Alta |

### 2.2 Requisitos de Pontuacao (RF-20 a RF-23)

| ID | Regra de Pontuacao |
|----|---------------------|
| RF-20 | Quem adivinhar corretamente ganha pontos; primeiro a acertar recebe mais pontos |
| RF-21 | Bonus de pontuacao se apenas um jogador adivinhar corretamente |
| RF-22 | Pontos para o dono do objeto baseado em quantos acertaram: maior pontuacao se apenas um acertou, menor se varios acertaram, zero se ninguem acertou, **perde pontos se todos acertaram** |
| RF-23 | Contabilizacao automatica de pontos pela aplicacao |

### 2.3 Requisitos Nao-Funcionais (RNF)

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RNF-01 | Arquitetura baseada em eventos (melhor avaliada que polling) | Alta |
| RNF-02 | Baixa latencia na comunicacao entre jogadores | Media |
| RNF-03 | Thread-safe: suporte a multiplos jogadores concorrentes | Alta |
| RNF-04 | Tolerancia a falhas de conexao (reconexao) | Media |
| RNF-05 | Facilidade de instalacao e configuracao | Media |
| RNF-06 | Codigo modular e extensivel | Media |

---

## 3. ESTUDO COMPARATIVO: TECNOLOGIAS RPC/RMI

### 3.1 Opcoes Avaliadas

| Tecnologia | Linguagem | Tipo | Modelo | Performance | Curva de Aprendizado | Melhor Para |
|------------|-----------|------|--------|-------------|----------------------|-------------|
| **Pyro5** | Python | RPC (objetos remotos) | Sincrono + Callbacks | Media | Baixa | Prototipagem rapida, Python puro |
| **RPyC** | Python | RPC simetrico | Transparente | Media | Baixa | Computacao distribuida Python |
| **Python XML-RPC** | Python | RPC XML-based | Sincrono | Baixa | Muito baixa | Simplicidade maxima |
| **gRPC** | Multi (Python/Java/Go/C++) | RPC moderno | Unary + Streaming (4 modos) | **Alta** | Media | Alta performance, streaming real-time |
| **Java RMI** | Java | RMI nativo | Sincrono + Callbacks | Media | Media | Ecossistema Java puro |
| **Pyro4 (legacy)** | Python | RPC | Sincrono | Media | Baixa | Substituído pelo Pyro5 |

### 3.2 Analise Detalhada

#### 3.2.1 Pyro5 (Python Remote Objects 5)
- **Site oficial**: https://pyro5.readthedocs.io/
- **Instalacao**: `pip install Pyro5`
- **Conceito**: Permite expor objetos Python como servicos remotos via proxy
- **Pontos fortes**:
  - API Pythonica e intuitiva
  - Name Server integrado para descoberta de servicos
  - Suporte a callbacks (objetos no cliente podem ser chamados pelo servidor)
  - Decoradores `@Pyro5.api.expose` para expor metodos
  - Suporte a chamadas `@Pyro5.api.oneway` (assincronas)
  - Serializacao automatica de objetos Python
  - Thread-safe com daemon built-in
- **Limitacoes**:
  - Apenas Python (nao e cross-language)
  - Performance inferior ao gRPC
  - Nao tem streaming nativo bidirecional como gRPC
- **Uso para o jogo**: EXCELENTE - callbacks permitem push de eventos, name server facilita descoberta

**Exemplo de servidor Pyro5:**
```python
import Pyro5.api

@Pyro5.api.expose
class GameService(object):
    def send_hint(self, player_id, hint):
        # Logica de envio de dica
        return True

daemon = Pyro5.api.Daemon()
uri = daemon.register(GameService)
print("URI:", uri)
daemon.requestLoop()
```

**Exemplo de callback Pyro5 (push/event-driven):**
```python
class GameCallback(object):
    @Pyro5.api.expose
    @Pyro5.api.callback
    def on_game_event(self, event_type, data):
        print(f"Evento recebido: {event_type}")
```

#### 3.2.2 RPyC (Remote Python Call)
- **Site oficial**: https://rpyc.readthedocs.io/
- **Instalacao**: `pip install rpyc`
- **Conceito**: RPC simetrico e transparente - objetos remotos parecem locais
- **Pontos fortes**:
  - Transparencia total: acesso a objetos remotos como se fossem locais
  - Conexoes simetricas (cliente e servidor sao intercambiaveis)
  - Suporte a synchronous e asynchronous invocation
  - ThreadPool server built-in
- **Limitacoes**:
  - Apenas Python
  - Modelo "classic" e inseguro (permite execucao arbitraria)
  - Menos documentacao que Pyro5
- **Uso para o jogo**: BOM - mas Pyro5 e mais adequado para este caso com callbacks

#### 3.2.3 gRPC (Google RPC)
- **Site oficial**: https://grpc.io/
- **Instalacao**: `pip install grpcio grpcio-tools`
- **Conceito**: RPC moderno baseado em HTTP/2 e Protocol Buffers
- **Pontos fortes**:
  - **4 tipos de comunicacao**: Unary, Server Streaming, Client Streaming, Bidirectional Streaming
  - Bidirectional streaming e IDEAL para jogos real-time e chat
  - Alta performance (HTTP/2, protobuf binario)
  - Cross-language (gera stubs para varias linguagens)
  - Fortemente tipado (.proto definitions)
  - Usado em producao por Google, Netflix, etc.
- **Limitacoes**:
  - Curva de aprendizado maior (necessita .proto files)
  - Mais verboso que Pyro5
  - Requer geracao de codigo a partir de .proto
- **Uso para o jogo**: EXCELENTE - streaming bidirecional e perfeito para eventos em tempo real

**Tipos de streaming gRPC:**
```protobuf
// Unary - simples request/response
rpc SendMessage(Message) returns (Response);

// Server streaming - servidor envia multiplas respostas
rpc GetHistory(Request) returns (stream Message);

// Client streaming - cliente envia multiplas mensagens
rpc SendHints(stream Hint) returns (Response);

// Bidirectional streaming - ambos enviam streams independentes
rpc GameStream(stream ClientEvent) returns (stream ServerEvent);
```

#### 3.2.4 Java RMI (Remote Method Invocation)
- **Documentacao**: https://docs.oracle.com/javase/tutorial/rmi/
- **Conceito**: RMI nativo do Java - permite chamar metodos em objetos remotos
- **Pontos fortes**:
  - Integrado nativamente no Java (sem dependencias externas)
  - Suporte a callbacks via interfaces remotas
  - Garbage collection distribuido
  - Familiar para desenvolvedores Java
- **Limitacoes**:
  - Apenas Java
  - Problemas com firewalls (usa portas dinamicas)
  - Requer registry (rmiregistry)
  - Mais complexo para configurar
  - Nao suporta streaming como gRPC
- **Uso para o jogo**: BOM - se a equipe preferir Java, e uma opcao viavel

### 3.3 Recomendacao Final

| Cenario | Recomendacao | Justificativa |
|---------|--------------|---------------|
| **Python, simplicidade** | **Pyro5** | Callbacks nativos permitem event-driven, API simples, name server integrado |
| **Python, performance** | **gRPC** | Streaming bidirecional ideal para jogos real-time, mais robusto |
| **Java** | **Java RMI** | Nativo do Java, callbacks suportados, menos dependencias |

> **RECOMENDACAO PRINCIPAL**: Pyro5 (Python) para equipes que priorizam simplicidade e rapidez de desenvolvimento, ou gRPC (Python/Java) para equipes que querem arquitetura mais robusta e performatica. Para este trabalho academico, **Pyro5 oferece o melhor custo-beneficio**.

---

## 4. ARQUITETURA DO SISTEMA

### 4.1 Modelo Arquitetural: Cliente-Servidor via RPC

```
+------------------+     RPC Calls      +--------------------+
|   CLIENTE 1      |<----------------->|                    |
|  (Pyro5 Proxy)   |                   |    SERVIDOR        |
+------------------+                   |   (Pyro5 Daemon)   |
                                      |                    |
+------------------+     RPC Calls    |  - Game Manager    |
|   CLIENTE 2      |<----------------->|  - Turn Manager    |
|  (Pyro5 Proxy)   |                   |  - Score Manager   |
+------------------+                   |  - Chat Manager    |
                                      |  - Spy Manager     |
+------------------+     RPC Calls    |  - Event Broadcaster|
|   CLIENTE 3      |<----------------->|                    |
|  (Pyro5 Proxy)   |                   |                    |
+------------------+                   +--------------------+
       ^
       | Callbacks (push de eventos)
       v
  [Event Handler Local]
```

### 4.2 Componentes do Sistema

#### 4.2.1 Servidor

| Componente | Responsabilidade |
|------------|------------------|
| **GameManager** | Gerencia sessoes de jogo, jogadores, estados |
| **TurnManager** | Controla fluxo de turnos, temporizadores, transicoes |
| **HintManager** | Processa envio de dicas publicas e privadas |
| **GuessManager** | Recebe e valida palpites dos jogadores |
| **ArbitrationManager** | Decide se um palpite esta correto (sinonimos, variacoes) |
| **ScoreManager** | Calcula e mantem pontuacao de todos os jogadores |
| **SpyManager** | Controla mecanica de espionagem e probabilidade de descoberta |
| **ChatManager** | Gerencia mensagens de chat em tempo real |
| **EventBroadcaster** | Envia eventos para todos os clientes via callbacks |
| **PyroDaemon** | Servidor RPC que expoe os servicos |

#### 4.2.2 Cliente

| Componente | Responsabilidade |
|------------|------------------|
| **GameClient** | Proxy Pyro5 para o servidor, faz chamadas RPC |
| **EventCallback** | Objeto exposto via Pyro5 que recebe eventos do servidor |
| **GameUI** | Interface do usuario (CLI ou GUI) |
| **LocalState** | Estado local do jogo (cache) |

### 4.3 Fluxo de Comunicacao Event-Driven (Push)

```
1. Cliente registra callback no servidor (register_callback)
2. Servidor armazena referencia ao callback de cada cliente
3. Quando um evento ocorre, servidor chama callback de TODOS os clientes
4. Clientes recebem o evento e atualizam a UI

Exemplo de eventos:
- PLAYER_JOINED: novo jogador entrou
- TURN_STARTED: novo turno comecou
- HINT_RECEIVED: dica publica recebida
- PRIVATE_EXCHANGE: dois jogadores trocaram dicas
- GUESS_MADE: alguem fez um palpite
- SPY_ATTEMPT: alguem tentou espiar
- SCORE_UPDATED: pontuacao atualizada
- CHAT_MESSAGE: nova mensagem no chat
- GAME_OVER: jogo terminou
```

---

## 5. ESTRUTURA DE DADOS

### 5.1 Entidades Principais

```python
# Jogador
class Player:
    id: str                    # ID unico
    name: str                  # Nome do jogador
    callback_uri: str          # URI Pyro5 para callback
    score: int                 # Pontuacao atual
    object_image: str          # Path da imagem do objeto
    object_name: str           # Nome correto do objeto (secreto)
    status: PlayerStatus       # WAITING, PLAYING, DISCONNECTED

# Dica
class Hint:
    id: str
    from_player: str           # Quem enviou
    to_player: Optional[str]   # null = publica, senao = privada
    word: str                  # A palavra-dica
    turn: int                  # Em qual turno foi enviada
    is_truthful: bool          # Se a dica e verdadeira (para privadas)

# Palpite
class Guess:
    id: str
    player_id: str             # Quem palpitou
    target_player: str         # De qual objeto esta tentando adivinhar
    word: str                  # O palpite
    turn: int                  # Em qual turno
    is_correct: Optional[bool] # Resultado da arbitragem

# Troca Privada
class PrivateExchange:
    id: str
    player_a: str
    player_b: str
    hint_a: str                # Dica de A para B
    hint_b: str                # Dica de B para A
    accepted: bool
    turn: int

# Tentativa de Espiar
class SpyAttempt:
    id: str
    spy_player: str            # Quem esta espiando
    target_exchange: str       # Qual troca quer espiar
    was_discovered: bool       # Se foi descoberto
    penalty: int               # Pontos perdidos

# Estado do Jogo
class GameState:
    game_id: str
    players: List[Player]
    current_turn: int
    max_turns: int
    status: GameStatus         # WAITING, IN_PROGRESS, FINISHED
    phase: TurnPhase           # HINT_PHASE, GUESS_PHASE, EXCHANGE_PHASE
    history: List[GameEvent]

# Evento de Jogo
class GameEvent:
    type: EventType
    timestamp: datetime
    data: dict                 # Dados especificos do evento

# Mensagem de Chat
class ChatMessage:
    id: str
    from_player: str
    content: str
    timestamp: datetime
```

### 5.2 Maquina de Estados do Jogo

```
[WAITING_FOR_PLAYERS] --todos conectados--> [DISTRIBUTING_OBJECTS]
[DISTRIBUTING_OBJECTS] --objetos atribuidos--> [ROUND_START]
[ROUND_START] --novo turno--> [HINT_PHASE]
[HINT_PHASE] --todos enviaram dicas--> [GUESS_PHASE]
[GUESS_PHASE] --tempo esgotado ou todos palpitaram--> [EXCHANGE_PHASE]
[EXCHANGE_PHASE] --trocas concluidas--> [SPY_PHASE]
[SPY_PHASE] --espionagem concluida--> [SCORING_PHASE]
[SCORING_PHASE] --pontos calculados--> [TURN_END]
[TURN_END] --ainda ha turnos--> [ROUND_START]
[TURN_END] --ultimo turno--> [GAME_END]
[GAME_END] --jogadores querem continuar--> [DISTRIBUTING_OBJECTS]
[GAME_END] --jogadores querem parar--> [FINAL]
```

### 5.3 Maquina de Estados do Turno

```
TURNO N:
1. HINT_PHASE (30-60 segundos)
   - Cada jogador envia uma dica publica (uma palavra)
   
2. GUESS_PHASE (30-60 segundos)
   - Jogadores podem enviar palpites ou passar
   - Cada jogador palpita para UM objeto de outro jogador
   
3. EXCHANGE_PHASE (opcional, uma vez por objeto)
   - Jogador A solicita troca privada com Jogador B
   - B aceita ou recusa
   - Se aceita, ambos enviam uma palavra privada
   - Todos sao notificados que houve troca (sem conteudo)
   
4. SPY_PHASE (simultaneo ao EXCHANGE_PHASE)
   - Jogadores podem tentar espiar trocas em andamento
   - Probabilidade de descoberta: configuravel (ex: 30%)
   - Se descoberto: perde pontos + todos sabem
   
5. SCORING_PHASE (automatico)
   - Arbitragem valida palpites
   - Pontos calculados e atribuidos
   - Placar atualizado e broadcast
```

---

## 6. DEFINICAO DAS CHAMADAS RPC

### 6.1 Interface do Servidor (Servicos Expostos)

```python
@Pyro5.api.expose
class GameServer(object):
    # === GERENCIAMENTO DE JOGO ===
    
    def join_game(self, player_name: str, callback_uri: str) -> str:
        """Entra no jogo. Retorna player_id."""
        
    def leave_game(self, player_id: str) -> bool:
        """Sai do jogo."""
        
    def start_game(self, player_id: str, max_turns: int) -> bool:
        """Inicia o jogo (apenas se houver jogadores suficientes)."""
        
    def register_callback(self, player_id: str, callback_uri: str) -> bool:
        """Registra callback do cliente para receber eventos."""
        
    # === FASE DE DICAS ===
    
    def submit_hint(self, player_id: str, hint_word: str) -> bool:
        """Envia dica publica (uma palavra) para todos."""
        
    # === FASE DE PALPITES ===
    
    def submit_guess(self, player_id: str, target_player: str, guess: str) -> dict:
        """Envia palpite sobre o objeto de outro jogador.
        Retorna: {success: bool, message: str, is_correct: bool?}"""
        
    def skip_guess(self, player_id: str) -> bool:
        """Pula a vez de palpitar."""
        
    # === TROCA PRIVADA DE DICAS ===
    
    def request_exchange(self, player_id: str, target_player: str) -> str:
        """Solicita troca de dicas privada com outro jogador.
        Retorna exchange_id."""
        
    def respond_exchange(self, player_id: str, exchange_id: str, accept: bool) -> bool:
        """Aceita ou recusa uma solicitacao de troca."""
        
    def submit_exchange_hint(self, player_id: str, exchange_id: str, hint_word: str) -> bool:
        """Envia dica privada para a troca (pode ser falsa!)."""
        
    # === ESPIONAGEM ===
    
    def attempt_spy(self, player_id: str, exchange_id: str) -> dict:
        """Tenta espiar uma troca privada.
        Retorna: {success: bool, discovered: bool, hint_a: str?, hint_b: str?, penalty: int}"""
        
    # === CHAT ===
    
    def send_chat(self, player_id: str, message: str) -> bool:
        """Envia mensagem no chat geral."""
        
    # === CONSULTAS ===
    
    def get_game_state(self, player_id: str) -> dict:
        """Retorna estado atual do jogo."""
        
    def get_scores(self, player_id: str) -> List[dict]:
        """Retorna placar atual."""
        
    def get_history(self, player_id: str) -> List[dict]:
        """Retorna historico de eventos do jogo."""
        
    def vote_continue(self, player_id: str, continue_game: bool) -> bool:
        """Vota para continuar ou nao apos fim dos turnos."""
```

### 6.2 Interface do Callback (Cliente)

```python
@Pyro5.api.expose
class GameCallback(object):
    """Cliente implementa esta interface para receber eventos."""
    
    @Pyro5.api.callback
    def on_player_joined(self, player: dict):
        """Novo jogador entrou no jogo."""
        
    @Pyro5.api.callback
    def on_game_started(self, game_state: dict):
        """Jogo iniciou."""
        
    @Pyro5.api.callback
    def on_turn_started(self, turn_number: int, phase: str):
        """Novo turno comecou."""
        
    @Pyro5.api.callback
    def on_phase_changed(self, phase: str):
        """Fase do turno mudou."""
        
    @Pyro5.api.callback
    def on_hint_received(self, from_player: str, hint_word: str, turn: int):
        """Dica publica recebida."""
        
    @Pyro5.api.callback
    def on_guess_made(self, player: str, target: str, guess: str):
        """Alguem fez um palpite."""
        
    @Pyro5.api.callback
    def on_guess_result(self, player: str, target: str, guess: str, is_correct: bool):
        """Resultado de um palpite (apos arbitragem)."""
        
    @Pyro5.api.callback
    def on_exchange_requested(self, exchange_id: str, from_player: str, to_player: str):
        """Solicitacao de troca recebida."""
        
    @Pyro5.api.callback
    def on_exchange_completed(self, exchange_id: str, player_a: str, player_b: str):
        """Troca privada foi concluida (notificacao publica)."""
        
    @Pyro5.api.callback
    def on_private_hint_received(self, exchange_id: str, from_player: str, hint_word: str):
        """Dica privada da troca recebida."""
        
    @Pyro5.api.callback
    def on_spy_attempt(self, spy_player: str, exchange_id: str, was_discovered: bool):
        """Alguem tentou espiar (resultado publico)."""
        
    @Pyro5.api.callback
    def on_score_updated(self, scores: List[dict]):
        """Pontuacao foi atualizada."""
        
    @Pyro5.api.callback
    def on_chat_message(self, from_player: str, message: str, timestamp: str):
        """Nova mensagem de chat."""
        
    @Pyro5.api.callback
    def on_game_over(self, final_scores: List[dict]):
        """Jogo terminou."""
        
    @Pyro5.api.callback
    def on_vote_request(self):
        """Solicitacao de voto para continuar ou nao."""
        
    @Pyro5.api.callback
    def on_error(self, error_code: str, message: str):
        """Erro ocorrido."""
```

---

## 7. IMPLEMENTACAO DAS MECANICAS

### 7.1 Distribuicao de Imagens

```
ALGORITMO:
1. Servidor possui um banco de imagens (pasta com imagens nomeadas)
2. Cada imagem tem um nome correto associado (ex: "bola.jpg" -> "bola")
3. No inicio de cada rodada, servidor embaralha a lista de imagens
4. Atribui uma imagem unica para cada jogador
5. Envia via callback: on_object_assigned(image_path)
6. Jogador carrega e visualiza a imagem localmente

FORMATO DA RESPOSTA DO CALLBACK:
{
    "image_url": "PYRO:file_service@host:port/image/bola.jpg",
    "object_name_hash": "hash_para_validacao"  # servidor guarda o hash
}
```

### 7.2 Sistema de Turnos

```python
class TurnManager:
    TURN_MAX_SECONDS = 60  # Tempo por fase
    
    def start_turn(self):
        self.current_turn += 1
        self.phase = TurnPhase.HINT
        self.hints_submitted = {}   # player_id -> hint
        self.guesses_submitted = {} # player_id -> guess
        self.timer = Timer(self.TURN_MAX_SECONDS, self.end_phase)
        self.broadcast_event("TURN_STARTED", {"turn": self.current_turn})
    
    def end_phase(self):
        if self.phase == TurnPhase.HINT:
            # Auto-envia dica vazia para quem nao enviou
            self.phase = TurnPhase.GUESS
            self.broadcast_event("PHASE_CHANGED", {"phase": "GUESS"})
            self.timer = Timer(self.TURN_MAX_SECONDS, self.end_phase)
            
        elif self.phase == TurnPhase.GUESS:
            self.phase = TurnPhase.EXCHANGE
            self.broadcast_event("PHASE_CHANGED", {"phase": "EXCHANGE"})
            self.timer = Timer(self.TURN_MAX_SECONDS, self.end_phase)
            
        elif self.phase == TurnPhase.EXCHANGE:
            self.phase = TurnPhase.SPY
            self.broadcast_event("PHASE_CHANGED", {"phase": "SPY"})
            self.timer = Timer(self.TURN_MAX_SECONDS, self.end_phase)
            
        elif self.phase == TurnPhase.SPY:
            self.phase = TurnPhase.SCORING
            self.calculate_scores()
            self.end_turn()
```

### 7.3 Troca Privada de Dicas

```
FLUXO DA TROCA:

Jogador A                           Servidor                          Jogador B
   |                                   |                                  |
   |-- request_exchange(B) ----------> |                                  |
   |                                   |-- on_exchange_requested(A) ----->|
   |                                   |                                  |
   |                                   |<-- respond_exchange(id, true) ---|
   |                                   |                                  |
   |-- submit_exchange_hint(id, "X")-> |                                  |
   |                                   |-- on_private_hint_received(A,"X")->|
   |                                   |                                  |
   |                                   |<-- submit_exchange_hint(id, "Y")-|
   |<-- on_private_hint_received(B,"Y")|                                  |
   |                                   |                                  |
   |                                   |-- on_exchange_completed(A,B) --->|
   |<-- on_exchange_completed(A,B) ----|                                  |

REGRAS:
- Troca e opcional (max 1 vez por objeto por jogador)
- Dica pode ser verdadeira ou falsa (estratégia do jogador)
- Todos sao notificados que A e B trocaram dicas (mas NAO o conteudo)
- Troca so e valida durante a EXCHANGE_PHASE
```

### 7.4 Mecanica de Espionagem

```
ALGORITMO DE ESPIONAGEM:

INPUT: spy_player_id, exchange_id
OUTPUT: {success, discovered, penalty, hints?}

1. Verificar se a troca existe e esta ativa
2. Verificar se spy_player nao e participante da troca
3. Calcular probabilidade de descoberta: P_DISCOVER = 0.30 (30%)
4. Gerar numero aleatorio R em [0, 1]
5. Se R < P_DISCOVER:
     - discovered = true
     - penalty = -10 pontos
     - spy_player perde pontos
     - TODOS recebem on_spy_attempt com was_discovered=true
     - spy_player NAO recebe as dicas
   Senao:
     - discovered = false
     - penalty = 0
     - spy_player recebe as dicas privadas
     - Nenhuma notificacao publica

CONFIGURACOES:
- P_DISCOVER: 0.30 (30%) - ajustavel
- PENALTY_DISCOVERED: -10 pontos
- BONUS_SPY_SUCCESS: +5 pontos (opcional)
- Um jogador so pode espiar uma vez por turno
- So pode espiar trocas em que nao participa
```

### 7.5 Arbitragem de Palpites

```
PROBLEMA: Um objeto pode ser descrito por multiplas palavras
          (ex: "bola" pode ser adivinhada como "esfera", "globo", "pelota")

SOLUCAO 1: Jogador dono do objeto valida (simplificado)
- Quando um palpite e feito, o servidor pergunta ao dono do objeto
- Dono responde se esta correto ou nao
- Vantagem: O dono conhece as variacoes aceitaveis
- Desvantagem: Dono pode mentir (mas isso e anti-etica de jogo)

SOLUCAO 2: Validacao por sinonimos (mais automatizado)
- Usar API de sinonimos (ex: WordNet, Dicio API)
- Palpite e considerado correto se:
  a) E exatamente igual ao nome do objeto, OU
  b) E sinonimo do nome do objeto (usando API), OU
  c) E similar suficiente (Levenshtein distance < threshold)
- Servidor decide automaticamente
- Mais justo e rapido

IMPLEMENTACAO RECOMENDADA (Solucao 2):
```python
import nltk
from nltk.corpus import wordnet
from difflib import SequenceMatcher

class ArbitrationManager:
    SIMILARITY_THRESHOLD = 0.8  # 80% similaridade
    
    def is_correct_guess(self, object_name: str, guess: str) -> bool:
        # Normalizacao
        obj = object_name.lower().strip()
        g = guess.lower().strip()
        
        # 1. Igualdade exata
        if obj == g:
            return True
        
        # 2. Sinonimos via WordNet
        obj_synsets = wordnet.synsets(obj, lang='por')  # Portugues
        guess_synsets = wordnet.synsets(g, lang='por')
        for os in obj_synsets:
            for gs in guess_synsets:
                if os == gs or os.wup_similarity(gs) > 0.9:
                    return True
        
        # 3. Similaridade de string
        similarity = SequenceMatcher(None, obj, g).ratio()
        return similarity >= self.SIMILARITY_THRESHOLD
```

### 7.6 Sistema de Pontuacao

```
PONTOS POR ADIVINHAR:
- Se o jogador acertou o objeto:
  - Posicao 1 (primeiro a acertar): +20 pontos
  - Posicao 2: +15 pontos
  - Posicao 3: +10 pontos
  - Posicao N: max(20 - (N-1)*5, 5)  # Minimo 5 pontos
  
- Se APENAS UM jogador acertou: +10 pontos bonus

PONTOS PARA O DONO DO OBJETO:
- Se 1 jogador acertou: +15 pontos
- Se 2 jogadores acertaram: +10 pontos
- Se 3 jogadores acertaram: +5 pontos
- Se N jogadores acertaram: max(15 - (N-1)*5, 0)
- Se NINGUEM acertou: 0 pontos
- Se TODOS os outros acertaram: -10 pontos (penalidade)

PONTOS DE ESPIONAGEM:
- Espiar e ser descoberto: -10 pontos
- Espiar com sucesso (nao descoberto): +5 pontos (opcional)

EXEMPLO DE CALCULO:
Rodada com 4 jogadores (A, B, C, D):
- Objeto de A: palpites = [B acertou 1o, C acertou 2o, D errou]
  - B: 20 pts (1o) + 10 bonus (unico nao, tem C) = 20 pts
  - C: 15 pts (2o) 
  - A: +10 pts (2 acertaram)
  - D: 0 pts
  
- Objeto de B: palpites = [ninguem acertou]
  - A, C, D: 0 pts
  - B: 0 pts (ninguem acertou)
  
- Objeto de C: palpites = [A acertou 1o, B acertou 2o, D acertou 3o]
  - A: 20 pts, B: 15 pts, D: 10 pts
  - C: 0 pts (todos acertaram = -10, mas minimo e 0)
  
- Objeto de D: palpites = [todos acertaram]
  - A, B, C: 5 pts cada (posicoes 1,2,3 com 4+ jogadores)
  - D: -10 pts (todos acertaram)
```

### 7.7 Chat em Tempo Real

```
ARQUITETURA DO CHAT:

O chat usa o mesmo mecanismo de callbacks Pyro5:

Cliente A                          Servidor                         Cliente B
   |                                 |                                 |
   |-- send_chat("oi galera!") --->  |                                 |
   |                                 |                                 |
   |                                 |-- on_chat_message(A, "oi...") ->|
   |<-- on_chat_message(A,"oi...") --|                                 |
   |                                 |-- on_chat_message(A,"oi...") ->|
   |                                 |                                 |

CARACTERISTICAS:
- Chat separado das funcionalidades do jogo
- Mensagens de chat NAO sao dicas, palpites ou trocas
- Interface separada na UI (painel de chat ao lado)
- Historico de mensagens mantido pelo servidor
- Sistema de notificacao visual quando nova mensagem chega

TIPOS DE MENSAGENS DE CHAT:
- PUBLIC: mensagem visivel para todos
- SYSTEM: mensagem do sistema (jogador entrou, turno mudou, etc.)
```

---

## 8. MODELO DE EVENTOS E BROADCAST

### 8.1 EventBroadcaster (Servidor)

```python
class EventBroadcaster:
    """Responsavel por enviar eventos para todos os clientes via callbacks."""
    
    def __init__(self):
        self.callbacks = {}  # player_id -> Pyro5 Proxy do callback
        self.lock = threading.Lock()
    
    def register_callback(self, player_id: str, callback_uri: str):
        with self.lock:
            self.callbacks[player_id] = Pyro5.api.Proxy(callback_uri)
    
    def broadcast(self, event_type: str, data: dict, exclude: List[str] = None):
        """Envia evento para TODOS os clientes conectados."""
        exclude = exclude or []
        failed_players = []
        
        with self.lock:
            for player_id, callback in self.callbacks.items():
                if player_id in exclude:
                    continue
                try:
                    # Chamada assincrona (oneway) para nao bloquear
                    callback._pyroOneway.add("on_" + event_type.lower())
                    getattr(callback, "on_" + event_type.lower())(data)
                except Exception as e:
                    failed_players.append(player_id)
                    print(f"Falha ao enviar para {player_id}: {e}")
        
        # Remove callbacks que falharam (desconectados)
        for pid in failed_players:
            self.callbacks.pop(pid, None)
    
    def send_to_player(self, player_id: str, event_type: str, data: dict):
        """Envia evento para um jogador especifico."""
        if player_id in self.callbacks:
            callback = self.callbacks[player_id]
            getattr(callback, "on_" + event_type.lower())(data)
```

### 8.2 Thread Safety no Servidor

```python
import threading

class GameServer(object):
    def __init__(self):
        self.players = {}
        self.game_state = GameState()
        self.lock = threading.RLock()  # Reentrant Lock
        self.broadcaster = EventBroadcaster()
    
    def submit_hint(self, player_id: str, hint_word: str) -> bool:
        with self.lock:  # Garante acesso thread-safe
            # Verifica se e a fase correta
            if self.game_state.phase != TurnPhase.HINT:
                return False
            
            # Registra a dica
            self.game_state.hints[player_id] = hint_word
            
            # Broadcast para todos
            self.broadcaster.broadcast("HINT_RECEIVED", {
                "from_player": player_id,
                "hint": hint_word,
                "turn": self.game_state.current_turn
            })
            
            # Verifica se todos enviaram dica
            if len(self.game_state.hints) == len(self.players):
                self.turn_manager.end_phase()
            
            return True
```

---

## 9. INTERFACE DO USUARIO (CLI)

### 9.1 Layout da Tela

```
+===========================================================================+
|                    JOGO DE ADIVINHACAO MULTIJOGADOR                       |
+===========================================================================+
|  TURNO: 3/10    FASE: ADIVINHAR    TEMPO: 00:23                         |
+----------------------------------------+----------------------------------+
|              SEU OBJETO                |           DICAS RECEBIDAS        |
|                                        |                                  |
|    [Imagem do objeto]                  |  Jogador1: "redonda"             |
|                                        |  Jogador2: "salta"               |
|    Voce sabe o que e, nao conta!       |  Jogador3: "esporte"             |
|                                        |                                  |
+----------------------------------------+----------------------------------+
|  SEUS PALPITES:                        |           PLACAR                 |
|  > Tentar adivinhar objeto de: [J1]    |  Jogador1:  45 pts               |
|    Palpite: [________] [ENVIAR]        |  Jogador2:  30 pts  <-- voce     |
|  > [PASSAR A VEZ]                      |  Jogador3:  55 pts               |
|                                        |  Jogador4:  20 pts               |
+----------------------------------------+----------------------------------+
|  ACAO ESPECIAL:                        |           CHAT GERAL             |
|  [Trocar dica com J1] [Trocar c/ J3]   |  Jogador1: alguem tem ideia?     |
|  [Espiar J1<->J3] (risco: 30%)        |  Jogador4: acho que sei!         |
|                                        |  > [digite sua mensagem] [OK]    |
+----------------------------------------+----------------------------------+
|  LOG DE EVENTOS:                                                        |
|  [14:32:05] Jogador3 acertou o objeto de Jogador1! (+20 pts)           |
|  [14:32:01] Jogador2 e Jogador4 trocaram dicas privadas                 |
|  [14:31:58] Jogador1 tentou espiar e FOI DESCOBERTO! (-10 pts)         |
+===========================================================================+
```

### 9.2 Fluxo de Interacao

```
1. Jogador inicia cliente
2. Digita nome e URI do servidor (ou auto-discover via Name Server)
3. Aguarda outros jogadores conectarem
4. Quando minimo de jogadores atingido, lider inicia o jogo
5. Recebe imagem do objeto via callback
6. FASE DE DICAS: digita uma palavra e envia
7. FASE DE PALPITES: escolhe jogador e digita palpite, ou passa
8. FASE DE TROCA: escolhe jogador para trocar dicas (uma vez)
9. FASE DE ESPIAR: escolhe troca para espiar (com risco)
10. Fase de pontuacao: ve resultado automaticamente
11. Repete do passo 6 ate ultimo turno
12. Vota para continuar ou parar
```

---

## 10. ESTRUTURA DE PASTAS DO PROJETO

```
jogo-adivinhacao-rpc/
|
|-- README.md                          # Documentacao do projeto
|-- requirements.txt                   # Dependencias Python
|-- relatorio.pdf                      # Relatorio do trabalho
|
|-- server/
|   |-- __init__.py
|   |-- main.py                        # Ponto de entrada do servidor
|   |-- game_server.py                 # Classe GameServer (Pyro5 expose)
|   |-- game_manager.py                # Logica do jogo
|   |-- turn_manager.py                # Gerenciamento de turnos
|   |-- hint_manager.py                # Processamento de dicas
|   |-- guess_manager.py               # Processamento de palpites
|   |-- arbitration_manager.py         # Arbitragem de respostas
|   |-- score_manager.py               # Calculo de pontuacao
|   |-- spy_manager.py                 # Mecanica de espionagem
|   |-- chat_manager.py                # Chat em tempo real
|   |-- event_broadcaster.py           # Broadcast de eventos
|   |-- models.py                      # Classes de dados (Player, Hint, etc.)
|   |-- constants.py                   # Constantes do jogo
|   |-- images/                        # Pasta com imagens dos objetos
|       |-- bola.jpg
|       |-- cadeira.jpg
|       |-- carro.jpg
|       |-- ...
|
|-- client/
|   |-- __init__.py
|   |-- main.py                        # Ponto de entrada do cliente
|   |-- game_client.py                 # Proxy Pyro5 para o servidor
|   |-- callback_handler.py            # Implementacao do GameCallback
|   |-- ui.py                          # Interface de linha de comando
|   |-- local_state.py                 # Estado local do cliente
|
|-- proto/                             # (se usar gRPC)
|   |-- game.proto                     # Definicao Protocol Buffers
|
|-- tests/
|   |-- test_game_server.py
|   |-- test_turn_manager.py
|   |-- test_scoring.py
|   |-- test_arbitration.py
```

---

## 11. DEPENDENCIAS E INSTALACAO

### 11.1 Requisitos do Sistema

- Python 3.8+
- Rede local ou internet para comunicacao RPC
- Terminal com suporte a Unicode (para CLI)

### 11.2 Dependencias (requirements.txt)

```
# Framework RPC (escolher um):
Pyro5>=5.14          # Para Pyro5
# grpcio>=1.50       # Para gRPC
# grpcio-tools>=1.50 # Para gRPC (geracao de stubs)
# rpyc>=5.3          # Para RPyC

# Utilidades
nltk>=3.8            # Para arbitragem por sinonimos
Pillow>=9.0          # Para manipulacao de imagens

# Testes
pytest>=7.0
```

### 11.3 Instalacao

```bash
# 1. Clonar o projeto
cd jogo-adivinhacao-rpc

# 2. Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Baixar dados do NLTK (para arbitragem)
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"

# 5. Iniciar Name Server (Pyro5) - opcional
python -m Pyro5.nameserver

# 6. Iniciar servidor
python server/main.py

# 7. Em outro terminal, iniciar cliente(s)
python client/main.py
```

---

## 12. ROTEIRO DE IMPLEMENTACAO

### Fase 1: Setup e Infraestrutura (2-3 horas)
- [ ] Configurar ambiente Python e instalar dependencias
- [ ] Implementar estrutura basica de pastas
- [ ] Implementar modelo de dados (models.py)
- [ ] Configurar Pyro5 Daemon e Name Server
- [ ] Testar comunicacao basica cliente-servidor

### Fase 2: Core do Jogo (4-5 horas)
- [ ] Implementar GameServer com metodos RPC
- [ ] Implementar GameCallback no cliente
- [ ] Implementar EventBroadcaster
- [ ] Implementar fluxo de join/leave
- [ ] Implementar distribuicao de imagens
- [ ] Implementar maquina de estados do jogo

### Fase 3: Mecanicas de Turno (3-4 horas)
- [ ] Implementar TurnManager com fases
- [ ] Implementar envio de dicas publicas
- [ ] Implementar palpites e validacao basica
- [ ] Implementar controle de tempo por fase
- [ ] Testar fluxo completo de um turno

### Fase 4: Mecanicas Avancadas (4-5 horas)
- [ ] Implementar troca privada de dicas
- [ ] Implementar mecanica de espionagem
- [ ] Implementar arbitragem (sinonimos/WordNet)
- [ ] Implementar sistema de pontuacao completo
- [ ] Testar todas as mecanicas integradas

### Fase 5: Chat e UI (3-4 horas)
- [ ] Implementar ChatManager
- [ ] Implementar interface de linha de comando
- [ ] Integrar todos os callbacks na UI
- [ ] Adicionar log de eventos
- [ ] Testar experiencia completa

### Fase 6: Testes e Relatorio (3-4 horas)
- [ ] Testar com multiplos jogadores simultaneos
- [ ] Testar concorrencia e thread-safety
- [ ] Testar reconexao de jogadores
- [ ] Escrever relatorio tecnico
- [ ] Preparar demonstracao

**TOTAL ESTIMADO: 19-25 horas de trabalho**

---

## 13. CRITERIOS DE AVALIACAO MAPEADOS

| Criterio do Professor | Como Atendido |
|----------------------|---------------|
| Uso de RPC/RMI | Pyro5 para toda comunicacao |
| Estrategia event-driven | Callbacks Pyro5 (push) em vez de polling |
| Jogo multijogador | Arquitetura cliente-servidor com broadcast |
| Dicas por turno | TurnManager com fase HINT |
| Troca de dicas privada | ExchangeManager com aceitacao |
| Espionagem com risco | SpyManager com probabilidade de descoberta |
| Arbitragem | ArbitrationManager com WordNet |
| Pontuacao automatica | ScoreManager com todas as regras |
| Chat em tempo real | ChatManager separado do jogo |
| Continuar ou parar | Votacao no GAME_END |
| Relatorio tecnico | Inclui introdulcao ao Pyro5, justificativa, descricao do desenvolvimento |
| Demonstracao | Preparar cenario de teste com 2-3 jogadores |

---

## 14. DICAS E BOAS PRATICAS

1. **Use o Name Server do Pyro5** para facilitar a descoberta de servicos - nao precisa hardcodar URIs
2. **Use @Pyro5.api.oneway** para metodos que nao precisam de resposta (como broadcast) - evita bloqueio
3. **Use @Pyro5.api.callback** para tratamento de excecoes em callbacks - facilita debug
4. **Use threading.RLock()** para garantir thread-safety no servidor
5. **Teste com pelo menos 3 instancias** do cliente simultaneas para verificar concorrencia
6. **Mantenha o callback do cliente rodando em thread separada** para receber eventos
7. **Use um dicionario thread-safe** (collections.deque ou queue.Queue) para eventos pendentes no cliente
8. **Log tudo** - use logging.info/debug para facilitar debug remoto
9. **Trate desconexoes** - remova callbacks que falham e trate reconexao
10. **Para o relatorio**, inclua diagramas de sequencia mostrando a comunicacao RPC entre cliente e servidor

---

## 15. REFERENCIAS

1. Pyro5 Documentation - https://pyro5.readthedocs.io/
2. gRPC Documentation - https://grpc.io/docs/languages/python/basics/
3. Java RMI Tutorial - https://docs.oracle.com/javase/tutorial/rmi/
4. RPyC Documentation - https://rpyc.readthedocs.io/
5. "Game Server Synchronization" - Monstar Lab Engineering Blog
6. "Push vs. Polling Models in Real-Time Communication" - Medium
7. "Networking of a Turn-Based Game" - Hacker News Discussion
8. "Consistency Patterns in Distributed Systems" - Design Gurus
9. NLTK WordNet Documentation - https://www.nltk.org/howto/wordnet.html

---

*Documento gerado em: 12 de Maio de 2026*
*Versao: 1.0*
