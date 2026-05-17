---
title: "Jogo de Adivinhação Multijogador via RPC/Pyro5"
subtitle: "CC5SDT — Sistemas Distribuídos e Tecnologias — UTFPR Campus Santa Helena — 2026-1"
author: "Gabriel Spacko"
date: \today
lang: pt-BR
---

# 1. Introdução ao Pyro5 e Comunicação RPC

A Chamada de Procedimento Remoto (RPC — *Remote Procedure Call*) é um paradigma de comunicação em sistemas distribuídos no qual um processo pode invocar sub-rotinas em outro processo, possivelmente em outra máquina, como se fossem funções locais. O mecanismo abstrai os detalhes de serialização de dados, transporte de rede e sincronização, permitindo ao desenvolvedor concentrar-se na lógica da aplicação.

Para este trabalho foram avaliadas quatro tecnologias de comunicação remota. A tabela abaixo compara as características relevantes para o contexto acadêmico e para os requisitos do projeto:

| Tecnologia | Linguagens | Modelo | Esquema | Desvantagens |
|------------|-----------|--------|---------|--------------|
| **Java RMI** | Java (JVM) | Síncrono, OO | Interface Java | Acoplamento à JVM; verbose; sem suporte a Python |
| **gRPC** | Multi-linguagem | Síncrono/streaming | Protocol Buffers | Requer arquivo `.proto`; overkill para projeto de 2 pessoas; compilação de schema |
| **RPyC** | Python | Síncrono | Dinâmico | Python-only; sem padrão de registro de callback push nativo |
| **Pyro5** | Python | Síncrono + `@oneway` | Serpent (dinâmico) | Python-only; sem suporte nativo a linguagens heterogêneas |

A escolha recaiu sobre **Pyro5** por três critérios principais:

1. **Requisito curricular**: a disciplina CC5SDT exige comunicação RPC Python-nativo, e Pyro5 é a biblioteca de referência adotada.
2. **Padrão de callback push sem polling**: Pyro5 suporta o padrão de registro de URI de callback, possibilitando que o servidor notifique todos os clientes conectados de forma assíncrona via `@oneway`, eliminando a necessidade de *polling* periódico dos clientes.
3. **Baixa curva de aprendizado**: a equipe de dois integrantes pode implementar servidor, cliente e sistema de nomes com uma única biblioteca e sem etapa de compilação de schema, reduzindo o tempo de configuração da infraestrutura.

---

# 2. Arquitetura do Sistema

O sistema é composto por três processos independentes que se comunicam via Pyro5 e Socket.IO:

![Diagrama de componentes: 3 processos do sistema](diagrams/arquitetura.png)

**Name Server (Pyro5 NS):** Serviço de descoberta de nomes fornecido pelo próprio Pyro5. O GameServer se registra no Name Server ao iniciar, e o Bridge realiza a descoberta usando `locate_ns()` para obter o proxy do servidor de jogo.

**GameServer (Pyro5 Daemon):** Processo central da aplicação. Gerencia o estado da partida, os turnos, as mecânicas de dica/palpite/troca/espionagem e o sistema de pontuação. Expõe métodos via `@expose` para chamada remota pelo Bridge. Utiliza `@oneway` para notificações push, evitando deadlock de callback.

**Bridge (Flask-SocketIO):** Processo intermediário que traduz eventos WebSocket/Socket.IO do navegador em chamadas RPC ao GameServer, e recebe callbacks `@oneway` do GameServer para repassar via `socketio.emit()` a todos os jogadores no *room* correto. Utiliza `async_mode='threading'` conforme recomendação oficial da biblioteca (gevent e eventlet foram descartados, sendo eventlet oficialmente depreciado).

## 2.1 Registro de Callback

O padrão de callback é o núcleo da arquitetura distribuída. Ao conectar-se ao jogo, o Bridge registra um objeto `BridgeCallbackReceiver` no Pyro5 daemon local e envia sua URI ao GameServer:

![Diagrama de sequência: registro de callback](diagrams/seq-callback.png)

O `BridgeCallbackReceiver` armazena a URI (não o objeto Proxy diretamente), criando um novo Proxy a cada chamada de broadcast. Isso é necessário porque proxies Pyro5 não são thread-safe — cada thread do Flask-SocketIO precisa de seu próprio Proxy independente.

O método `@oneway` garante que o GameServer não bloqueie aguardando retorno dos callbacks. Se um callback falhar (ex.: jogador desconectado), o GameServer continua operando normalmente.

## 2.2 Entrega de Evento de Jogo

O fluxo completo de um evento de dica exemplifica o ciclo request-broadcast-delivery do sistema:

![Diagrama de sequência: entrega de evento de jogo](diagrams/seq-game-event.png)

O navegador emite `submit_hint` via Socket.IO ao Bridge. O Bridge chama `proxy.submit_hint(player_id, hint_word)` via RPC Pyro5 no GameServer. O GameServer valida a dica, armazena no estado da partida e itera sobre todos os callbacks registrados, chamando `on_hint_received(data)` como `@oneway` para cada um. Cada Bridge recebe o callback e emite `hint_received` via `socketio.emit()` apenas para o *room* correto.

---

# 3. Demonstração da Aplicação

A interface foi desenvolvida com React (TypeScript) + Tailwind CSS, comunicando-se com o Bridge via Socket.IO. As capturas de tela abaixo ilustram o fluxo completo de uma partida com dois jogadores.

## 3.1 Tela Inicial (Landing)

A tela inicial apresenta as opções de criação e entrada em partida. O jogador informa seu apelido e pode criar uma nova sala ou entrar em uma sala existente via código de 6 dígitos.

![Tela inicial — Landing page](screenshots/landing.png)

## 3.2 Lobby — Aguardando Jogadores

Após criar ou entrar em uma sala, o jogador aguarda no Lobby. A lista de jogadores atualiza em tempo real via Socket.IO. O host (criador da sala) vê o botão "Iniciar Partida" habilitado ao atingir o mínimo de 2 jogadores.

![Lobby — aguardando jogadores](screenshots/lobby.png)

## 3.3 Tela de Jogo — Fase de Dicas

Durante a partida, cada jogador recebe uma imagem secreta de um objeto. A tela principal exibe o timer de fase (com indicação visual de urgência: verde → âmbar → vermelho), as dicas públicas enviadas por outros jogadores, e o painel de ação da fase corrente em um modal dedicado.

![Tela de jogo durante a fase de dicas](screenshots/game.png)

## 3.4 Resultados Finais (PostGame)

Ao final de todos os turnos, a tela de resultados exibe o pódio com os três melhores jogadores e uma tabela completa com a pontuação por turno de cada jogador. Os participantes podem votar para jogar novamente.

![Resultados finais — PostGame](screenshots/postgame.png)

## 3.5 Trechos de Código Relevantes

O padrão de callback é implementado no Bridge com armazenamento de URI e criação de Proxy por thread:

```python
import threading
import Pyro5.api

# Estado compartilhado: mapa player_id → URI do callback
_callback_uris: dict[str, str] = {}
_local = threading.local()

class BridgeCallbackReceiver:
    """Daemon Pyro5 local no processo Bridge.
    Recebe @oneway do GameServer e repassa via socketio.emit().
    """
    @Pyro5.api.expose
    @Pyro5.api.oneway
    def on_phase_changed(self, data: dict) -> None:
        room_code = data.get("room_code")
        socketio.emit("phase_changed", data, to=room_code)

    @Pyro5.api.expose
    @Pyro5.api.oneway
    def on_hint_received(self, data: dict) -> None:
        room_code = data.get("room_code")
        socketio.emit("hint_received", data, to=room_code)


def get_game_proxy():
    """Retorna Proxy Pyro5 per-thread para o GameServer.
    Proxies não são thread-safe — cada thread Flask-SocketIO precisa do seu.
    """
    if not hasattr(_local, "proxy"):
        ns = Pyro5.api.locate_ns(host="127.0.0.1")
        uri = ns.lookup("game.server")
        _local.proxy = Pyro5.api.Proxy(uri)
    return _local.proxy
```

O método de broadcast no GameServer utiliza `@oneway` para evitar deadlock:

```python
import Pyro5.api

@Pyro5.api.expose
@Pyro5.api.oneway
def broadcast_phase_changed(self, room_code: str, data: dict) -> None:
    """Notifica todos os callbacks registrados no room via @oneway.
    Falhas individuais de callback não interrompem o broadcast.
    """
    for player_id, uri in self._callbacks.get(room_code, {}).items():
        try:
            proxy = Pyro5.api.Proxy(uri)
            proxy.on_phase_changed(data)
        except Exception:
            pass  # Jogador desconectado — ignora silenciosamente
```

---

# 4. Instalação e Execução

## 4.1 Pré-requisitos

- Python 3.11 ou superior
- Node.js 18 ou superior e npm
- Google Chrome (para compilação dos diagramas no relatório)

## 4.2 Instalação do Ambiente Python

```bash
# Clonar o repositório
git clone <url-do-repositorio>
cd sd-rpc-av-1

# Criar e ativar ambiente virtual com Python 3.11+
python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Baixar corpora NLTK para arbitragem de sinônimos
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
```

## 4.3 Iniciar o Sistema (4 Terminais)

O sistema requer quatro processos rodando simultaneamente:

**Terminal 1 — Name Server Pyro5:**
```bash
pyro5-ns --host 127.0.0.1
```

**Terminal 2 — Servidor de Jogo:**
```bash
source venv/bin/activate
python server/game_server.py
```

**Terminal 3 — Bridge (Flask-SocketIO):**
```bash
source venv/bin/activate
python bridge/bridge.py
```

**Terminal 4 — Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## 4.4 Acessar o Jogo

Abra o navegador e acesse: **http://localhost:5173**

Insira um apelido, crie uma sala e compartilhe o código de 6 dígitos com os outros jogadores (2 a 4 participantes).

## 4.5 Compilar o Relatório (Opcional)

Para gerar o relatório em PDF:

```bash
cd docs
npm install
make pdf
# Abre docs/relatorio.pdf
```
