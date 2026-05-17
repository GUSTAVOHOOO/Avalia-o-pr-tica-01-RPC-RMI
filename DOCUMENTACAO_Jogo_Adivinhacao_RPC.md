# Documentacao Tecnica - Jogo Multijogador de Adivinhacao via RPC/RMI

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
| **Linguagem** | Python (backend) + TypeScript/React (frontend) |
| **Comunicacao** | Pyro5 RPC + Flask-SocketIO Bridge |

### 1.1 Conceito do Jogo

Cada jogador recebe uma imagem de um objeto no inicio de cada turno. A cada rodada, os jogadores enviam dicas curtas (uma palavra) sobre o objeto que receberam. Os outros jogadores podem tentar adivinhar ou esperar. O jogo inclui sistema de troca de dicas privada entre dois jogadores, mecanica de espionagem (com risco de penalidade), chat em tempo real, arbitragem automatica de respostas via WordNet e sistema de pontuacao complexo.

---

## 2. ANALISE DE REQUISITOS

### 2.1 Requisitos Funcionais Implementados

| ID | Requisito | Status |
|----|-----------|--------|
| RF-01 | Cada jogador recebe uma imagem de um objeto no inicio da rodada | ✅ Implementado |
| RF-02 | Sistema de turnos com limite maximo configuravel (1, 3, 5, 7, 10) | ✅ Implementado |
| RF-03 | A cada turno, cada jogador envia uma dica curta (uma palavra) para todos | ✅ Implementado |
| RF-04 | Jogadores podem tentar adivinhar o objeto ou esperar o proximo turno | ✅ Implementado |
| RF-05 | Troca de dicas privada entre dois jogadores (aceitacao mutua) | ✅ Implementado |
| RF-06 | Dicas trocadas privadamente nao precisam ser verdadeiras | ✅ Implementado |
| RF-07 | Notificacao publica quando dois jogadores trocam dicas (sem revelar conteudo) | ✅ Implementado |
| RF-08 | Mecanica de espionagem: espiar troca de dicas com chance de ser descoberto | ✅ Implementado |
| RF-09 | Penalidade de pontos se o espiao for descoberto | ✅ Implementado |
| RF-10 | Mecanismo de arbitragem para validar palpites (WordNet + sinonimos) | ✅ Implementado |
| RF-11 | Opcao de finalizar jogo ou continuar com novos objetos ao fim dos turnos | ✅ Implementado (votacao) |
| RF-12 | Sistema de pontuacao automatico | ✅ Implementado |
| RF-13 | Chat em tempo real separado das funcionalidades do jogo | ✅ Implementado |
| RF-14 | Separacao clara: chat nao e usado para dicas, trocas, espionagem ou palpites | ✅ Implementado |
| RF-15 | Comunicacao exclusivamente via RPC (Pyro5) | ✅ Implementado |
| RF-16 | Suporte a reconexao de jogadores | ✅ Implementado |
| RF-17 | Relatorio tecnico com introducao ao framework RPC escolhido | ✅ Este documento |

### 2.2 Regras de Pontuacao Implementadas

| ID | Regra de Pontuacao | Implementacao |
|----|---------------------|---------------|
| RF-20 | Quem adivinhar corretamente ganha pontos; primeiro a acertar recebe mais pontos | ✅ Posicao 1: +20pts, Posicao 2: +15pts, Posicao N: max(20 - (N-1)*5, 5) |
| RF-21 | Bonus de pontuacao se apenas um jogador adivinhar corretamente | ✅ +10pts bonus |
| RF-22 | Pontos para o dono do objeto baseado em quantos acertaram | ✅ 1 acerto: +15pts, 2 acertos: +10pts, todos acertam: -10pts, ninguem: 0pts |
| RF-23 | Contabilizacao automatica de pontos pela aplicacao | ✅ Calculado na fase SCORING_PHASE |

### 2.3 Requisitos Nao-Funcionais Atendidos

| ID | Requisito | Status |
|----|-----------|--------|
| RNF-01 | Arquitetura baseada em eventos (callbacks/push) | ✅ Pyro5 callbacks + Socket.IO |
| RNF-02 | Baixa latencia na comunicacao | ✅ WebSocket para browser, RPC para backend |
| RNF-03 | Thread-safe: suporte a multiplos jogadores concorrentes | ✅ threading.RLock em todo servidor |
| RNF-04 | Tolerancia a falhas de conexao (reconexao) | ✅ Grace period de 5s + reconexao explicita |
| RNF-05 | Facilidade de instalacao e configuracao | ✅ Docker + requirements.txt |
| RNF-06 | Codigo modular e extensivel | ✅ Separação em modulos independentes |

---

## 3. TECNOLOGIA RPC ESCOLHIDA: Pyro5

### 3.1 Por que Pyro5?

| Criterio | Pyro5 | Justificativa |
|----------|-------|---------------|
| Simplicidade | ⭐⭐⭐⭐⭐ | API Pythonica, decoradores intuitivos |
| Callbacks | ⭐⭐⭐⭐⭐ | `@Pyro5.api.callback` nativo para push de eventos |
| Name Server | ⭐⭐⭐⭐⭐ | Descoberta de servicos integrada |
| Thread-safety | ⭐⭐⭐⭐ | Daemon built-in thread-safe |
| Serializacao | ⭐⭐⭐⭐ | Serializacao automatica de objetos Python |
| Performance | ⭐⭐⭐ | Suficiente para jogo turn-based |

### 3.2 Caracteristicas Utilizadas

- **`@Pyro5.api.expose`**: Expoe metodos do servidor como chamadas RPC
- **`@Pyro5.api.oneway`**: Chamadas fire-and-forget (broadcasts) sem bloqueio
- **`@Pyro5.api.callback`**: Permite servidor chamar metodos no cliente (push de eventos)
- **Name Server**: Descoberta dinamica de servicos via `PYRONAME:game.server`
- **Proxy por thread**: Cada thread Flask cria seu proprio Proxy Pyro5 (thread-safety)

### 3.3 Estrutura de Comunicacao

```
Navegador (React)          Bridge (Flask-SocketIO)          GameServer (Pyro5)
      |                            |                                 |
      |---- WebSocket -----------> |                                 |
      |    (Socket.IO)             |                                 |
      |                            |---- Pyro5 RPC Call -----------> |
      |                            |    (Proxy per-thread)           |
      |                            |                                 |
      |<--- WebSocket Push --------|                                 |
      |    (socketio.emit)         |<--- Pyro5 Callback ------------|
      |                            |    (@callback @oneway)          |
```

---

## 4. ARQUITETURA DO SISTEMA

### 4.1 Visao Geral: Arquitetura em 3 Camadas

```
+-----------------------------------------------------------------------+
|                         CAMADA 1: CLIENTE                             |
|                    (React + TypeScript + Tailwind)                    |
|                                                                       |
|  - LandingScreen    - CreateGameScreen   - JoinGameScreen            |
|  - LobbyScreen      - GameScreen         - PostGameScreen            |
|  - ChatPanel        - PhaseModal         - ScoreDeltaToast           |
+-----------------------------------------------------------------------+
                              | WebSocket (Socket.IO)
                              v
+-----------------------------------------------------------------------+
|                      CAMADA 2: BRIDGE (Proxy)                         |
|                  (Flask-SocketIO + Pyro5 Client)                      |
|                                                                       |
|  - BridgeCallbackReceiver: recebe callbacks Pyro5 do servidor         |
|  - Socket.IO handlers: traduz eventos WebSocket para chamadas RPC     |
|  - Per-thread Proxy: cada thread Flask tem seu proprio Proxy Pyro5    |
|  - Grace-period disconnect: 5s antes de remover jogador desconectado  |
+-----------------------------------------------------------------------+
                              | Pyro5 RPC (TCP)
                              v
+-----------------------------------------------------------------------+
|                     CAMADA 3: SERVIDOR (GameServer)                   |
|                    (Pyro5 Daemon + Logica do Jogo)                    |
|                                                                       |
|  - GameServer: API RPC exposta via @expose                           |
|  - TurnMachine: maquina de estados das fases do jogo                 |
|  - TurnState: estado mutavel por turno                               |
|  - EventBroadcaster: fan-out de eventos para todos os callbacks      |
|  - Arbitration: validacao de palpites via NLTK WordNet               |
+-----------------------------------------------------------------------+
```

### 4.2 Componentes do Servidor

| Componente | Arquivo | Responsabilidade |
|------------|---------|------------------|
| **GameServer** | `server/game_server.py` | API RPC exposta, gerenciamento de sessoes, logica de jogo |
| **TurnMachine** | `server/turn_machine.py` | Maquina de estados das fases, timers auto-advance |
| **TurnState** | `server/turn_state.py` | Estado mutavel por turno (dicas, palpites, trocas) |
| **EventBroadcaster** | `server/event_broadcaster.py` | Fan-out de eventos via callbacks Pyro5 |
| **Arbitration** | `server/arbitration.py` | Validacao de palpites via WordNet (exact/synonym/fallback) |
| **Config** | `config.py` | Constantes centralizadas (timers, thresholds, portas) |

### 4.3 Componentes do Bridge

| Componente | Arquivo | Responsabilidade |
|------------|---------|------------------|
| **BridgeCallbackReceiver** | `bridge/bridge.py` | Recebe callbacks Pyro5 e emite eventos Socket.IO |
| **Socket.IO Handlers** | `bridge/bridge.py` | Traduz eventos WebSocket em chamadas RPC |
| **SPA Static Server** | `bridge/bridge.py` | Serve o frontend React compilado |
| **Image Server** | `bridge/bridge.py` | Serve imagens dos objetos via `/static/images/` |

### 4.4 Componentes do Frontend

| Componente | Arquivo | Responsabilidade |
|------------|---------|------------------|
| **Landing** | `frontend/src/pages/Landing.tsx` | Tela inicial com opcoes criar/entrar |
| **CreateGame** | `frontend/src/pages/CreateGame.tsx` | Formulario de criacao de sala |
| **JoinGame** | `frontend/src/pages/JoinGame.tsx` | Formulario de entrada por codigo |
| **Lobby** | `frontend/src/pages/Lobby.tsx` | Sala de espera com lista de jogadores |
| **GameScreen** | `frontend/src/pages/GameScreen.tsx` | Tela principal do jogo com todas as fases |
| **PostGame** | `frontend/src/pages/PostGame.tsx` | Tela de fim de jogo com votacao |
| **ChatPanel** | `frontend/src/components/ChatPanel.tsx` | Painel de chat em tempo real |
| **PhaseModal** | `frontend/src/components/PhaseModal.tsx` | Modal indicando mudanca de fase |
| **CountdownDisplay** | `frontend/src/components/CountdownDisplay.tsx` | Contador regressivo da fase |

---

## 5. MAQUINA DE ESTADOS DO JOGO

### 5.1 Estados da Sessao

```
[WAITING] --host inicia--> [IN_PROGRESS]
[IN_PROGRESS] --ultimo turno--> [VOTACAO]
[VOTACAO] --maioria sim--> [IN_PROGRESS] (novo jogo)
[VOTACAO] --maioria nao--> [ENDED] (sala removida)
```

### 5.2 Fases do Turno

```
TURNO N:
1. ROUND_START (5 segundos)
   - Notificacao de inicio de novo turno
   - Atribuicao de imagens aos jogadores

2. HINT_PHASE (60 segundos)
   - Cada jogador envia uma dica publica (uma palavra)
   - Quando todos enviam, timer encurta para 5 segundos

3. GUESS_PHASE (60 segundos)
   - Jogadores podem enviar palpites sobre objetos de outros
   - Ou passar a vez (skip)
   - Arbitragem automatica via WordNet

4. EXCHANGE_PHASE (45 segundos)
   - Jogador solicita troca privada com outro
   - Aceite ou recusa
   - Se aceita, ambos enviam palavra privada
   - Notificacao publica da troca (sem conteudo)
   - Jogadores podem pular esta fase

5. SPY_PHASE (30 segundos) [*condicional]
   - Apenas se houver trocas completadas no turno
   - Jogadores podem tentar espiar trocas
   - Probabilidade de descoberta: 30%
   - Se descoberto: -10 pontos + notificacao publica

6. SCORING_PHASE (15 segundos)
   - Calculo automatico de pontos
   - Broadcast do placar atualizado

7. TURN_END (5 segundos)
   - Transicao entre turnos
   - Se ultimo turno: vai para votacao
```

### 5.3 Fluxo de Votacao Pos-Jogo

```
1. GAME_ENDED broadcast apos ultimo turno
2. VOTE_STARTED: 30 segundos para votar
3. Jogadores votam "Jogar Novamente" (sim/nao)
4. Se todos votarem antes: resolucao antecipada
5. Se timer expirar: conta votos presentes
6. Maioria (>50%) sim: GAME_RESTARTING, novo jogo
7. Caso contrario: GAME_ENDED final, sala deletada
```

---

## 6. ESTRUTURA DE DADOS

### 6.1 Entidades Principais

```python
# Jogador
@dataclass
class PlayerInfo:
    player_id: str          # UUID unico
    player_name: str        # Nome exibido (max 20 chars)
    callback_uri: str       # URI Pyro5 para callback
    is_host: bool           # True se criou a sala

# Sessao de Jogo
@dataclass
class GameSession:
    room_code: str          # Codigo de 6 chars (ex: "A3B9K2")
    host_id: str            # player_id do host
    max_turns: int          # 1, 3, 5, 7 ou 10
    status: str             # "WAITING" | "IN_PROGRESS" | "ENDED"
    players: List[PlayerInfo]
    turn_machine: TurnMachine
    accumulated_scores: dict      # player_id -> pontos totais
    current_image_assignments: dict  # player_id -> nome do objeto
    turn_score_history: list      # historico de pontos por turno
    vote_record: VoteRecord       # estado da votacao pos-jogo

# Estado do Turno
@dataclass
class TurnState:
    turn_number: int
    player_ids: list
    hints_submitted: dict          # player_id -> palavra-dica
    guesses_made: dict             # player_id -> target_player_id | None
    correct_guesses: list          # ordem de acertos
    image_assignments: dict        # player_id -> nome do objeto
    exchanges: dict                # exchange_id -> ExchangeRecord
    completed_exchanges: list      # exchanges concluidas (alvos de espiao)
    exchange_participants: set     # jogadores que ja usaram slot de troca
    exchange_skips: set            # jogadores que pularam troca
    spy_attempts: set              # jogadores que ja usaram espionagem

# Troca Privada
@dataclass
class ExchangeRecord:
    requester_id: str
    target_id: str
    status: str              # "pending" | "accepted" | "rejected" | "completed"
    requester_hint: Optional[str]
    target_hint: Optional[str]

# Registro de Voto
@dataclass
class VoteRecord:
    votes: dict              # player_id -> bool (sim/nao)
    generation: int          # contador anti-stale (igual TurnMachine)
    timer: threading.Timer   # timer de 30 segundos
    start_time: float
    duration_seconds: int = 30
```

### 6.2 Banco de Imagens (manifest.json)

```json
{
  "apple.jpg": "maca",
  "bicycle.jpg": "bicicleta",
  "chair.jpg": "cadeira",
  "clock.jpg": "relogio",
  "guitar.jpg": "violao",
  "hat.jpg": "chapeu",
  "laptop.jpg": "laptop",
  "umbrella.jpg": "guarda-chuva",
  "book.jpg": "livro",
  "cup.jpg": "xicara",
  "shoe.jpg": "sapato",
  "tree.jpg": "arvore"
}
```

**Validacao**: Ao iniciar, o servidor verifica se cada palavra possui sinonimos no WordNet portugues (omw-1.4). Palavras sem cobertura sao excluidas automaticamente com warning no log.

---

## 7. IMPLEMENTACAO DAS MECANICAS

### 7.1 Distribuicao de Imagens

```
ALGORITMO:
1. Servidor possui um manifest.json com imagens nomeadas
2. Cada imagem tem um nome correto associado (ex: "bola.jpg" -> "bola")
3. No inicio de cada rodada, servidor embaralha imagens disponiveis
4. Atribui uma imagem unica para cada jogador
5. Marca imagens como "usadas" neste jogo (evita repeticao dentro do mesmo jogo)
6. Se acabarem imagens: reseta o pool
7. Envia via callback privado: object_assigned(image_url, object_name)
8. Jogador visualiza a imagem no navegador via /static/images/{filename}
```

### 7.2 Sistema de Turnos e Timers

```python
# DURACOES CONFIGURAVEIS (config.py)
PHASE_DURATIONS = {
    "ROUND_START":    5,   # segundos
    "HINT_PHASE":    60,   # segundos
    "GUESS_PHASE":   60,   # segundos
    "EXCHANGE_PHASE": 45,  # segundos
    "SPY_PHASE":     30,   # segundos
    "SCORING_PHASE": 15,   # segundos
    "TURN_END":       5,   # segundos
}

# Quando todos completam a acao da fase:
PHASE_COMPLETION_GRACE_SECONDS = 5  # encurta para 5s ao inves de avancar instantaneamente
```

**Mecanismo anti-stale (TURN-04)**: Cada fase incrementa um contador `generation`. Se um timer antigo disparar apos o avanco manual, ele e descartado automaticamente.

### 7.3 Troca Privada de Dicas

```
FLUXO DA TROCA:

Jogador A (Browser)    Bridge    GameServer    Jogador B (Browser)
    |                    |            |              |
    |-- request_exchange -----------> |              |
    |                    |            |              |
    |                    |            |-- exchange_requested -->|
    |                    |            |              |
    |                    |<-- accept/reject ----------| (respond_exchange)
    |                    |            |              |
    |<-- exchange_accepted/rejected --| (via callback)         |
    |                    |            |              |
    |-- submit_exchange_hint -------> |              |
    |                    |            |              |
    |                    |            |<-- submit_exchange_hint-|
    |                    |            |              |
    |<-- exchange_hints --------------| (hint privada de B)    |
    |                    |            |              |
    |                    |            |-- exchange_hints ----->| (hint privada de A)
    |                    |            |              |
    |                    |            |-- exchange_completed ->| (broadcast publico)
    |<-- exchange_completed ----------| (broadcast publico)    |

REGRAS:
- Troca e opcional (max 1 vez por objeto por jogador)
- Dica pode ser verdadeira ou falsa (estrategia do jogador)
- Todos sao notificados que A e B trocaram dicas (mas NAO o conteudo)
- Troca so e valida durante a EXCHANGE_PHASE
- Slots reservados no momento do request (evita duplos pedidos)
- Se rejeitada: slots liberados, ambos podem tentar com outros
```

### 7.4 Mecanica de Espionagem

```
ALGORITMO DE ESPIONAGEM:

INPUT: spy_player_id, exchange_id
OUTPUT: {ok: bool, discovered: bool}

1. Verificar se esta na SPY_PHASE
2. Verificar se spy_player nao ja usou espionagem neste turno
3. Verificar se exchange_id esta em completed_exchanges
4. Verificar se spy_player nao e participante da troca
5. Calcular probabilidade de descoberta: P_DISCOVER = 0.30 (30%)
6. Gerar numero aleatorio R em [0, 1]
7. Se R < 0.30:
     - discovered = True
     - penalty = -10 pontos (subtraido de accumulated_scores)
     - Broadcast publico "spy_discovered" com nome do espiao
     - Spy NAO recebe as dicas
   Senao:
     - discovered = False
     - Spy recebe ambas as dicas privadas via "spy_success"
     - Sem broadcast publico

REGRAS:
- Um jogador so pode espiar uma vez por turno
- So pode espiar trocas que nao participa
- So pode espiar trocas COMPLETADAS
- SPY_PHASE e pulada automaticamente se nao houver trocas
```

### 7.5 Arbitragem de Palpites (WordNet)

```python
# TRES NIVEIS DE DECISAO:

# 1. Match exato (case-insensitive)
if guess.lower() == target.lower():
    return True, target, 'exact'

# 2. Sinonimos via WordNet (Portugues - omw-1.4)
guess_synsets = wn.synsets(guess, lang='por')
target_synsets = wn.synsets(target, lang='por')
if guess_synsets and target_synsets:
    sim = max_wup_similarity(guess_synsets, target_synsets)
    # Wu-Palmer similarity >= 0.7 aceita sinonimos proximos
    is_correct = sim >= 0.7
    return is_correct, target if is_correct else None, 'synonym'

# 3. Fallback (quando WordNet nao tem synsets para alguma palavra)
# Repete match exato como fallback
return guess.lower() == target.lower(), target if match else None, 'fallback'
```

**Exemplos de sinonimos aceitos (threshold 0.7)**:
- "bicicleta" ~ "bike" = ~0.9 ✅
- "maca" ~ "fruta" = ~0.82 ✅
- "cadeira" ~ "banquinho" = depende, pode ser aceito se >0.7

### 7.6 Sistema de Pontuacao

```
PONTOS POR ADIVINHAR:
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

PENALIDADE DE ESPIONAGEM:
- Espiar e ser descoberto: -10 pontos

EXEMPLO:
Rodada com 4 jogadores (A, B, C, D):
- Objeto de A: B acertou 1o, C errou, D errou
  - B: 20pts
  - A: +15pts (1 acertou)
- Objeto de B: todos erraram
  - B: 0pts
- Objeto de C: todos acertaram
  - A: 5pts, B: 5pts, D: 5pts
  - C: -10pts (penalidade)
```

### 7.7 Chat em Tempo Real

```
ARQUITETURA:
- Chat usa o mesmo mecanismo de WebSocket do jogo
- Mensagens sao enviadas via send_chat() no servidor
- Broadcast para todos os jogadores da sala via broadcaster
- Bridge retransmite como evento Socket.IO "chat_message"
- Maximo 200 caracteres por mensagem
- Timestamp incluido em cada mensagem
- Chat e isolado: nao afeta logica do jogo
```

### 7.8 Reconexao (Grace Period)

```
FLUXO DE RECONEXAO:

1. Jogador perde conexao (fecha aba, refresh, rede instavel)
2. Bridge detecta disconnect via Socket.IO
3. Inicia timer de 5 segundos (grace period)
4. Se jogador reconectar dentro de 5s:
   - Timer cancelado
   - Novo SID mapeado ao mesmo player_id
   - Callback Pyro5 re-registrado
   - Estado atual recuperado via get_player_view()
5. Se timer expirar:
   - Jogador removido da sessao via leave_game()
   - Broadcast "player_left" para outros jogadores
   - Se host sair em WAITING: proximo jogador promovido a host
```

---

## 8. INTERFACE RPC (GameServer)

### 8.1 Metodos Expostos

```python
@Pyro5.api.expose
class GameServer:
    # === HEALTH CHECK ===
    def ping(self) -> str                    # Retorna "pong"

    # === GERENCIAMENTO DE SESSAO ===
    def create_game(player_name, callback_uri, max_turns) -> dict
    def join_game(player_name, callback_uri, room_code) -> dict
    def get_session(room_code) -> dict       # Lista de jogadores e estado
    def get_player_view(room_code, player_id) -> dict  # Vista privada do jogador
    def start_game(player_id) -> bool        # Host inicia o jogo (requer >=2)
    def leave_game(player_id) -> bool        # Sair da sessao
    def reconnect_player(player_id, room_code, callback_uri) -> dict

    # === FASE DE DICAS ===
    def submit_hint(player_id, hint_word) -> dict

    # === FASE DE PALPITES ===
    def submit_guess(player_id, target_player_id, guess_word) -> dict
    def skip_guess(player_id) -> dict

    # === TROCA PRIVADA ===
    def request_exchange(player_id, target_player_id) -> dict
    def skip_exchange(player_id) -> dict
    def respond_exchange(player_id, exchange_id, accept) -> dict
    def submit_exchange_hint(player_id, exchange_id, hint_word) -> dict

    # === ESPIONAGEM ===
    def attempt_spy(player_id, exchange_id) -> dict

    # === CHAT ===
    def send_chat(player_id, message) -> dict

    # === VOTACAO POS-JOGO ===
    def submit_vote(player_id, continue_game) -> dict

    # === OPERADOR/TESTE ===
    def advance_phase(player_id) -> bool     # Pular fase atual manualmente
```

### 8.2 Eventos de Callback (Push)

| Evento | Quem Recebe | Quando |
|--------|-------------|--------|
| `player_joined` | Todos na sala | Novo jogador entra |
| `game_started` | Todos na sala | Host inicia o jogo |
| `phase_changed` | Todos na sala | Mudanca de fase do turno |
| `phase_timer_shortened` | Todos na sala | Todos completaram acao antecipadamente |
| `object_assigned` | Jogador especifico | Nova imagem atribuida |
| `hint_received` | Todos na sala | Um jogador enviou dica |
| `guess_result` | Todos na sala | Um palpite foi avaliado |
| `exchange_requested` | Jogador alvo | Solicitacao de troca recebida |
| `exchange_accepted` | Solicitante | Troca aceita |
| `exchange_rejected` | Solicitante | Troca rejeitada |
| `exchange_completed` | Todos na sala | Troca concluida (sem conteudo) |
| `exchange_hints` | Participantes | Dica privada recebida |
| `spy_discovered` | Todos na sala | Espiao foi descoberto |
| `spy_success` | Espiao | Espionagem bem-sucedida |
| `score_updated` | Todos na sala | Pontuacao atualizada |
| `chat_message` | Todos na sala | Nova mensagem de chat |
| `player_left` | Todos na sala | Jogador saiu da sessao |
| `host_changed` | Todos na sala | Host saiu, novo host designado |
| `game_ended` | Todos na sala | Fim do jogo (placar final) |
| `vote_started` | Todos na sala | Votacao pos-jogo iniciou |
| `vote_update` | Todos na sala | Alguem votou |
| `game_restarting` | Todos na sala | Maioria votou para reiniciar |

---

## 9. SEGURANCA E VALIDACOES

### 9.1 Validacoes de Entrada

```
- player_name: nao-vazio, string, max 20 caracteres
- callback_uri: nao-vazio, string
- room_code: nao-vazio, string (6 caracteres gerados pelo servidor)
- max_turns: deve ser um de {1, 3, 5, 7, 10}
- hint_word: stripped, max 50 caracteres
- guess_word: stripped, max 50 caracteres
- message (chat): stripped, max 200 caracteres
```

### 9.2 Protecoes Contra Erros

- **Callback failures permanentes**: ConnectionRefusedError/OSError remove callback imediatamente
- **Callback failures transientes**: 3 falhas consecutivas removem callback
- **Stale timers**: Generation counter previne timers antigos de avancar fases
- **Deadlock prevention**: Broadcasts SEMPRE fora do RLock
- **Path traversal**: `send_from_directory` nativo do Flask protege contra `../`
- **Vote stuffing**: Jogador so pode votar uma vez (duplicate flag)
- **Double-exchange**: Slots reservados no request para evitar requests duplos
- **Double-guess**: Dicionario guesses_made previne multiplos palpites

---

## 10. ESTRUTURA DE PASTAS DO PROJETO

```
jogo-adivinhacao-rpc/
|
|-- README.md                          # Documentacao basica do projeto
|-- requirements.txt                   # Dependencias Python
|-- config.py                          # Constantes e configuracoes centralizadas
|-- docker-compose.yml                 # Orquestracao Docker (NS + GameServer + Bridge + Frontend)
|-- Dockerfile                         # Imagem para containerizacao
|-- start-demo.sh                      # Script de inicializacao rapida (TODO EM UM!)
|-- pytest.ini                         # Configuracao dos testes
|-- validate_manifest.py               # Script de validacao do manifest.json
|
|-- .planning/                         # Documentacao de planejamento (roadmap, requisitos)
|   |-- PROJECT.md
|   |-- ROADMAP.md
|   |-- REQUIREMENTS.md
|   |-- research/
|   |   |-- ARCHITECTURE.md
|   |   |-- FEATURES.md
|   |   |-- PITFALLS.md
|   |   |-- STACK.md
|   |   |-- SUMMARY.md
|
|-- server/                            # SERVIDOR RPC (Pyro5)
|   |-- __init__.py
|   |-- game_server.py                 # GameServer - API RPC exposta (~1400 linhas)
|   |-- turn_machine.py                # Maquina de estados das fases (~330 linhas)
|   |-- turn_state.py                  # Estado mutavel por turno (~70 linhas)
|   |-- event_broadcaster.py           # Fan-out de callbacks Pyro5 (~115 linhas)
|   |-- arbitration.py                 # Validacao de palpites via WordNet (~90 linhas)
|   |-- images/                        # Banco de imagens dos objetos
|   |   |-- manifest.json              # Mapeamento arquivo -> palavra
|   |   |-- apple.jpg, bicycle.jpg, ... # 12 imagens
|
|-- bridge/                            # BRIDGE WebSocket-RPC
|   |-- __init__.py
|   |-- bridge.py                      # Flask-SocketIO + Pyro5 client (~815 linhas)
|
|-- frontend/                          # CLIENTE (React + TypeScript)
|   |-- src/
|   |   |-- main.tsx                   # Entry point React
|   |   |-- App.tsx                    # Router e gerenciamento de estado
|   |   |-- socket.ts                  # Cliente Socket.IO
|   |   |-- pages/
|   |   |   |-- Landing.tsx            # Tela inicial
|   |   |   |-- CreateGame.tsx         # Criar sala
|   |   |   |-- JoinGame.tsx           # Entrar em sala
|   |   |   |-- JoinByCode.tsx         # Entrar por codigo
|   |   |   |-- Lobby.tsx              # Sala de espera
|   |   |   |-- GameScreen.tsx         # Tela principal do jogo
|   |   |   |-- PostGame.tsx           # Tela de votacao pos-jogo
|   |   |-- components/
|   |   |   |-- ChatPanel.tsx          # Painel de chat
|   |   |   |-- CountdownDisplay.tsx   # Contador regressivo
|   |   |   |-- PhaseBadge.tsx         # Badge da fase atual
|   |   |   |-- PhaseModal.tsx         # Modal de transicao de fase
|   |   |   |-- PlayerListItem.tsx     # Item da lista de jogadores
|   |   |   |-- ReconnectionBanner.tsx # Banner de reconexao
|   |   |   |-- ScoreDeltaToast.tsx    # Notificacao de pontos
|   |   |-- index.css                  # Estilos globais (Tailwind)
|   |-- package.json
|   |-- tsconfig.json
|   |-- tailwind.config.ts
|   |-- vite.config.ts
|
|-- tests/                             # TESTES AUTOMATIZADOS
|   |-- __init__.py
|   |-- test_unit.py                   # Testes unitarios basicos
|   |-- test_turn_machine.py           # Testes da maquina de turnos
|   |-- test_turn_state.py             # Testes do estado do turno
|   |-- test_exchange.py               # Testes de troca privada
|   |-- test_scoring.py                # Testes de pontuacao
|   |-- test_arbitration.py            # Testes de arbitragem WordNet
|   |-- test_chat.py                   # Testes de chat
|   |-- test_event_broadcaster.py      # Testes do broadcast
|   |-- test_session.py                # Testes de sessao
|   |-- test_reconnect.py              # Testes de reconexao
|   |-- test_postgame.py               # Testes de votacao pos-jogo
```

---

## 11. DEPENDENCIAS E INSTALACAO

### 11.1 Requisitos do Sistema

- Python 3.10+
- Node.js 18+ (para build do frontend)
- Rede local (localhost) para comunicacao Pyro5 + WebSocket
- Docker (opcional, para execucao containerizada)

### 11.2 Dependencias Python (requirements.txt)

```
Pyro5==5.16              # Framework RPC
Flask==3.1.3             # Web framework do bridge
flask-socketio==5.6.1    # WebSocket para browser
simple-websocket==1.1.0  # Dependencia do flask-socketio
nltk==3.9.4              # WordNet para arbitragem de sinonimos
pytest                   # Framework de testes
```

### 11.3 Dependencias Node.js (frontend/package.json)

```json
{
  "dependencies": {
    "react": "^18.x",
    "react-dom": "^18.x",
    "react-router-dom": "^6.x",
    "socket.io-client": "^4.x",
    "tailwindcss": "^3.x"
  }
}
```

### 11.4 Instalacao Local

```bash
# 1. Backend Python
cd jogo-adivinhacao-rpc
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt

# 2. Download WordNet (primeira execucao)
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"

# 3. Frontend
npm install --prefix frontend
npm run build --prefix frontend

# 4. Iniciar servicos (3 terminais separados)
# Terminal 1: Name Server
python -m Pyro5.nameserver

# Terminal 2: GameServer
python server/game_server.py

# Terminal 3: Bridge
python bridge/bridge.py

# 5. Acessar no navegador
# http://localhost:5000
```

### 11.5 Instalacao com Docker (Recomendado!)

```bash
# Clone o projeto e entre no diretório
cd Avalia-o-pr-tica-01-RPC-RMI

# Execute o script de inicializacao demo (TUDO AUTOMATICO!)
./start-demo.sh
```

**O que o `start-demo.sh` faz automaticamente:**

```bash
#!/usr/bin/env bash
# 1. Verifica se docker-compose esta disponivel
# 2. Constrói e sobe todos os serviços Docker
docker compose up -d --build

# 3. Espera o Bridge ficar "healthy" (até 120 segundos)
#    - Name Server (Pyro5)
#    - Game Server (Pyro5 RPC)
#    - Bridge (Flask-SocketIO)
#    - Frontend (React estático)

# 4. Inicia tunnel ngrok na porta 5000
#    - Exponibiliza o jogo publicamente pela internet
#    - Útil para demos com jogadores em máquinas diferentes

# 5. Exibe a URL pública para compartilhar
#    Public URL: https://xxxxx.ngrok.io
```

**Apos executar, basta:**

1. Acessar a URL pública mostrada no terminal
2. Compartilhar a URL com outros jogadores
3. Cada jogador entra com um nome e o código da sala
4. O host inicia o jogo quando todos entrarem

**Parar os serviços:**
```bash
docker compose down
```

### 11.6 Instalacao Manual (sem Docker)

```bash
# 1. Backend Python
cd Avalia-o-pr-tica-01-RPC-RMI
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt

# 2. Download WordNet (primeira execucao)
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"

# 3. Frontend
npm install --prefix frontend
npm run build --prefix frontend

# 4. Iniciar servicos (3 terminais separados)

# Terminal 1: Name Server
python -m Pyro5.nameserver

# Terminal 2: GameServer
python server/game_server.py

# Terminal 3: Bridge
python bridge/bridge.py

# 5. Acessar no navegador
# http://localhost:5000
```

---

## 11B. ARQUITETURA DOCKER (Docker Compose)

### 11B.1 Servicos e Comunicacao

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Docker Network (jogo-adivinhacao)                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    PYRO5     ┌─────────────┐    PYRO5     ┌──────┐ │
│  │ nameserver  │◄────────────►│ gameserver  │◄────────────►│bridge│ │
│  │  (Pyro5)    │   port 9090  │  (Pyro5)    │   port 9091  │      │ │
│  │             │              │             │              │Flask │ │
│  └─────────────┘              └─────────────┘              │ :5000│ │
│                                                             └──────┘ │
│                                                                    │
│                                              ┌──────────────────────────────────────────┐
│                                              │              ngrok tunnel                 │
│                                              │   (expõe porta 5000 para internet)       │
│                                              └──────────────────────────────────────────┘
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ HTTP/WebSocket
                                       ▼
                              ┌──────────────────┐
                              │   Navegadores   │
                              │   dos Jogadores  │
                              └──────────────────┘
```

### 11B.2 Services do Docker Compose

| Servico | Imagem | Portas | Descricao |
|---------|--------|--------|-----------|
| **nameserver** | Pyro5 built-in | 9090 | Name Server para descoberta de servicos |
| **gameserver** | Dockerfile local | 9091 | Servidor Pyro5 com toda a logica do jogo |
| **bridge** | Dockerfile local | 5000:5000 | Flask-SocketIO + Pyro5 client |
| **frontend** | Dockerfile local | 8080:80 | React build (servido estaticamente pelo bridge) |

### 11B.3 Vantagens da Arquitetura Docker

- **Isolamento**: Cada servico roda em container separado
- **Rede interna**: Containers se comunicam por nomes Docker (nameserver, gameserver, bridge)
- **Portas fixas**: Sem conflitos com portas locais do host
- **ngrok**: Túnel automatico para expor o jogo publicamente para demonstração
- **Health checks**: Bridge verifica se GameServer esta pronto antes de aceitar conexoes

### 11B.4 Variaveis de Ambiente Docker

```yaml
# docker-compose.yml (valores padrao)
environment:
  - PYRO_NS_HOST=nameserver        # Nome do servico Docker, nao IP
  - DAEMON_BIND_HOST=gameserver    # Bind host para Pyro5
  - FLASK_BIND_HOST=0.0.0.0        # Aceita conexoes de qualquer interface
  - GAME_SERVER_PORT=9091           # Porta Pyro5 do gameserver
  - BRIDGE_PORT=5000               # Porta HTTP/WebSocket do bridge
```

### 11B.5 Exemplo de Uso Demo Completo

```bash
# 1. Baixar/clonar o projeto
git clone <repo>
cd Avalia-o-pr-tica-01-RPC-RMI

# 2. Executar script demo (TODO AUTOMÁTICO!)
./start-demo.sh

# 3. Saída esperada:
# [demo] Building and starting services...
# [demo] Waiting for bridge to be healthy...
# [demo] Bridge is healthy.
# [demo] Starting ngrok tunnel on port 5000...
#
# ==================================================
#   Public URL: https://abcd1234.ngrok.io
# ==================================================
#
# [demo] Press Ctrl+C to stop ngrok (Docker services keep running).

# 4. Jogadores acessam a URL pública
# 5. Criam salas, entram, jogam!

# 6. Para parar:
# docker compose down
```

---

## 12. INICIALIZACAO RAPIDA (start-demo.sh)

### 12.1 O que e?

`start-demo.sh` e um script de conveniencia que automatiza TODO o processo de inicializacao para demonstracoes do jogo. Com apenas um comando, todos os servicos sobem automaticamente.

### 12.2 O que ele faz passo a passo:

```bash
#!/usr/bin/env bash

# Passo 1: Verifica versao do docker-compose
COMPOSE_CMD="docker compose"  # ou "docker-compose" em versoes antigas

# Passo 2: Constroi e sobe todos os servicos em background
$COMPOSE_CMD up -d --build

# Passo 3: Aguarda bridge ficar healthy (ate 120 segundos)
# - Verifica healthcheck do container bridge
# - Se unhealthy: mostra logs e aborta
# - Se timeout: mostra logs e aborta

# Passo 4: Inicia ngrok para expor porta 5000 publicamente
# - Útil para jogadores em máquinas diferentes
# - Mostra URL pública ao final

# Passo 5: Exibe URL e instruções
# - Public URL: https://xxxx.ngrok.io
# - Instruções para parar serviços
```

### 12.3 Requisitos

- Docker + Docker Compose instalados
- ngrok com autenticação (para uso real)
- Permissão de execução no script: `chmod +x start-demo.sh`

### 12.4 Para que serve o ngrok?

O ngrok cria um túnel seguro da sua máquina local para a internet. Isso e **essencial para demos** porque:

1. **Jogadores em máquinas diferentes** podem acessar o mesmo jogo
2. **Não precisa configurar roteador** ou firewall
3. **URL pública temporária** para compartilhar rapidamente
4. **Funciona mesmo em redes restritivas** que bloqueiam portas

### 12.5/health endpoint do Bridge

O `healthcheck` no docker-compose.yml verifica se o Bridge esta pronto:

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import Pyro5.api; ns=Pyro5.api.locate_ns(); p=Pyro5.api.Proxy(f'PYRONAME:game.server@{ns._pyroUri.host}'); p.ping()"]
  interval: 10s
  timeout: 5s
  retries: 5
```

Isso garante que o Bridge só fica "healthy" quando:
- Nome Server esta rodando
- Game Server esta registrado
- Game Server responde ao ping

---

## 14. TESTES AUTOMATIZADOS

### 14.1 Suite de Testes

```bash
# Executar todos os testes
pytest

# Com verbose
pytest -v

# Teste especifico
pytest tests/test_scoring.py -v
```

### 14.2 Cobertura de Testes

| Modulo Testado | Arquivo de Teste | O que e testado |
|----------------|------------------|-----------------|
| TurnMachine | `test_turn_machine.py` | Transicao de fases, timers, stale guard |
| TurnState | `test_turn_state.py` | Hint/guess/exchange/spy completion logic |
| Exchange | `test_exchange.py` | Fluxo completo de troca privada |
| Scoring | `test_scoring.py` | Calculo de pontos para cenarios diversos |
| Arbitration | `test_arbitration.py` | WordNet exact/synonym/fallback matching |
| Chat | `test_chat.py` | Envio e recebimento de mensagens |
| EventBroadcaster | `test_event_broadcaster.py` | Fan-out e remocao de callbacks falhos |
| Session | `test_session.py` | Create/join/leave/get_session |
| Reconnect | `test_reconnect.py` | Reconexao e grace period |
| PostGame | `test_postgame.py` | Votacao e resolucao |

### 14.3 Exemplo de Teste

```python
# tests/test_scoring.py
def test_only_one_correct_gets_bonus():
    state = create_test_turn_state(3)
    state.guesses_made = {"p1": "p3", "p2": "p3", "p3": None}
    state.correct_guesses = ["p1"]  # p1 acertou sozinho
    deltas = _calculate_score_deltas(state)
    assert deltas["p1"] == 30  # 20 + 10 bonus
    assert deltas["p3"] == 15  # dono: 1 acerto
```

---

## 15. FLUXO DE UTILIZACAO

### 15.1 Criar uma Partida

```
1. Jogador A acessa http://localhost:5000
2. Clica "Criar Partida"
3. Digita nome e escolhe numero de turnos (1/3/5/7/10)
4. Recebe codigo da sala (ex: "A3B9K2")
5. Aguarda na tela de Lobby
```

### 15.2 Entrar em uma Partida

```
1. Jogador B acessa o site
2. Clica "Entrar em Partida"
3. Digita nome e codigo da sala
4. Entra no Lobby
5. Ve lista de jogadores presentes
```

### 15.3 Durante o Jogo

```
1. Host clica "Iniciar Jogo" (requer >=2 jogadores)
2. ROUND_START: espera 5 segundos
3. HINT_PHASE: cada jogador recebe imagem e envia uma dica
4. GUESS_PHASE: jogadores palpitam ou passam
5. EXCHANGE_PHASE: jogadores trocam dicas privadas ou pulam
6. SPY_PHASE: jogadores tentam espiar ou pulam
7. SCORING_PHASE: pontuacao calculada e exibida
8. TURN_END: transicao para proximo turno
9. Repete ate ultimo turno
```

### 15.4 Pos-Jogo

```
1. GAME_ENDED: exibe placar final
2. VOTE_STARTED: 30 segundos para votar
3. Jogadores votam "Jogar Novamente" ou "Sair"
4. Se maioria sim: GAME_RESTARTING, novo jogo comec
5. Se maioria nao: sala e deletada, jogadores voltam ao inicio
```

---

## 16. CONFIGURACOES IMPORTANTES

### 16.1 Timers (`config.py`)

```python
PHASE_DURATIONS = {
    "ROUND_START":    5,   # Transicao entre turnos
    "HINT_PHASE":    60,   # Tempo para enviar dicas
    "GUESS_PHASE":   60,   # Tempo para palpitar
    "EXCHANGE_PHASE": 45,  # Tempo para trocas privadas
    "SPY_PHASE":     30,   # Tempo para espionagem
    "SCORING_PHASE": 15,   # Exibicao do placar
    "TURN_END":       5,   # Transicao
}

PHASE_COMPLETION_GRACE_SECONDS = 5  # Quando todos acabam, espera 5s ao inves de avancar imediatamente
```

### 16.2 Arbitragem (`config.py`)

```python
WU_PALMER_THRESHOLD = 0.7  # Similaridade minima para sinonimos via WordNet
```

### 16.3 Espionagem (hardcoded no codigo)

```python
P_DISCOVER = 0.30          # 30% chance de ser descoberto
PENALTY_DISCOVERED = -10   # Pontos perdidos se descoberto
```

### 16.4 Ambiente Docker

```python
NS_HOST = os.environ.get("PYRO_NS_HOST", "127.0.0.1")
DAEMON_BIND_HOST = os.environ.get("DAEMON_BIND_HOST", "127.0.0.1")
FLASK_BIND_HOST = os.environ.get("FLASK_BIND_HOST", "127.0.0.1")
GAME_SERVER_PORT = 9091
BRIDGE_PORT = 5000
```

---

## 15. CRITERIOS DE AVALIACAO MAPEADOS

| Criterio do Professor | Como Atendido |
|----------------------|---------------|
| Uso de RPC/RMI | Pyro5 para toda comunicacao servidor-bridge |
| Estrategia event-driven | Callbacks Pyro5 (@callback) + Socket.IO push |
| Jogo multijogador | Arquitetura cliente-servidor com salas (room codes) |
| Dicas por turno | TurnMachine com HINT_PHASE e GUESS_PHASE |
| Troca de dicas privada | ExchangeRecord com aceitacao e entrega privada |
| Espionagem com risco | SpyManager com 30% de probabilidade de descoberta |
| Arbitragem | Arbitration via NLTK WordNet + Wu-Palmer similarity |
| Pontuacao automatica | ScoreManager com regras documentadas |
| Chat em tempo real | ChatManager separado via Socket.IO |
| Continuar ou parar | Votacao pos-jogo com timer de 30 segundos |
| Relatorio tecnico | Este documento |
| Demonstracao | Frontend React responsivo com indicadores visuais |

---

## 16. EVOLUCOES EM RELACAO AO PRD ORIGINAL

| Aspecto | PRD Original | Implementacao Atual |
|---------|-------------|---------------------|
| Interface | CLI ou GUI simples | React Web App responsiva |
| Comunicacao Browser | N/A | Flask-SocketIO Bridge |
| Salas | N/A | Sistema de room codes (6 chars) |
| Host | N/A | Sistema de host com permissoes |
| Reconexao | N/A | Grace period de 5s + reconexao explicita |
| Fases | 5 fases | 7 fases (inclui ROUND_START e TURN_END) |
| Timer adaptive | N/A | Encurta para 5s quando todos completam |
| Votacao pos-jogo | Sim/Nao simples | Timer de 30s + resolucao automatica |
| Historico de pontos | N/A | turn_score_history por turno |
| Testes | N/A | 10+ arquivos de teste automatizado |
| Docker | N/A | docker-compose.yml incluido |
| Validacao WordNet | Opcional | Obrigatoria - filtra manifest.json |
| Frontend Stack | N/A | React 18 + TypeScript + Tailwind + Vite |

---

## 17. BOAS PRATICAS E PADROES UTILIZADOS

1. **RLock em todo servidor**: Toda mutacao de estado segura entre threads
2. **Broadcast fora do lock**: Previne deadlock em I/O de rede
3. **Generation counter**: Evita timers stale avancando fases erroneamente
4. **Validacao server-side**: Inputs validados antes de processamento
5. **Separação de concerns**: GameServer, TurnMachine, TurnState como modulos independentes
6. **Testabilidade**: TurnMachine e TurnState puros (sem Pyro5) permitem testes unitarios
7. **Per-thread proxies**: Cada thread Flask tem seu proprio Proxy Pyro5
8. **Graceful degradation**: Callbacks falhos sao removidos automaticamente
9. **Configuracao centralizada**: Todas as constantes em config.py
10. **Type hints**: Python completo com type hints para melhor documentacao

---

## 18. REFERENCIAS

1. Pyro5 Documentation - https://pyro5.readthedocs.io/
2. Flask-SocketIO Documentation - https://flask-socketio.readthedocs.io/
3. NLTK WordNet Documentation - https://www.nltk.org/howto/wordnet.html
4. React Documentation - https://react.dev/
5. Tailwind CSS Documentation - https://tailwindcss.com/
6. "Game Server Synchronization" - Monstar Lab Engineering Blog
7. "Push vs. Polling Models in Real-Time Communication" - Medium
8. "Consistency Patterns in Distributed Systems" - Design Gurus

---

*Documento atualizado em: 17 de Maio de 2026*
*Versao: 2.0*
*Baseado no PRD v1.0 de 12 de Maio de 2026*
