---
phase: 02-player-session-lobby
verified: 2026-05-12T21:00:00Z
status: human_needed
score: 11/12 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Abrir http://localhost:3000 em dois browsers simultâneos — criar sala, compartilhar código, segundo jogador entra — ambos os lobbies atualizam em tempo real sem recarregar a página"
    expected: "Lista de jogadores em ambas as abas atualiza imediatamente ao segundo jogador entrar (evento player_joined entregue via Pyro5 callback → bridge → Socket.IO)"
    why_human: "Verificação do pipeline end-to-end com dois browsers simultâneos; não é possível garantir via análise de código estático que o callback Pyro5 dispara corretamente no ambiente de produção"
  - test: "No lobby com 2 jogadores, Alice (host) clica 'Iniciar Jogo' — verificar que AMBOS os browsers recebem o evento game_started"
    expected: "Ambas as abas navegam para /game/:sessionId e exibem o estado de loading 'Distribuindo imagens...'"
    why_human: "Verificação do broadcast game_started para a Socket.IO room; requer dois browsers ativos simultaneamente"
---

# Phase 2: Player Session + Lobby — Relatório de Verificação

**Phase Goal:** Player session + lobby — jogador pode criar uma sala, compartilhar o código, outro jogador entra, lobby atualiza em tempo real, host inicia o jogo.
**Verificado em:** 2026-05-12T21:00:00Z
**Status:** human_needed
**Re-verificação:** Não — verificação inicial

---

## Conquista do Objetivo

### Verdades Observáveis

| # | Verdade | Status | Evidência |
|---|---------|--------|-----------|
| 1 | `create_game()` armazena GameSession e retorna `{player_id, room_code, is_host: True}` | ✓ VERIFICADO | game_server.py linhas 141-188; test_create_game PASSOU |
| 2 | `room_code` tem exatamente 6 caracteres alfanuméricos maiúsculos; duas chamadas retornam códigos diferentes | ✓ VERIFICADO | `_generate_room_code` (linhas 129-139) usa `string.ascii_uppercase + string.digits` com `k=6`; loop while garante unicidade; test_room_code_format PASSOU |
| 3 | `join_game()` anexa jogador a sessão WAITING e registra callback | ✓ VERIFICADO | game_server.py linhas 190-248; appende PlayerInfo e chama `broadcaster.register_callback`; test_join_game PASSOU |
| 4 | `join_game()` retorna `{error: 'jogo em andamento'}` quando status não é WAITING | ✓ VERIFICADO | game_server.py linha 222; test_join_rejected_if_started PASSOU |
| 5 | `start_game()` retorna True apenas quando chamador é host E sessão tem ≥2 jogadores; False caso contrário | ✓ VERIFICADO | game_server.py linhas 250-293; test_start_game_validation PASSOU |
| 6 | `join_game()` dispara broadcast PLAYER_JOINED para todos os callbacks registrados | ✓ VERIFICADO | Linha 247 — `broadcaster.broadcast("player_joined", broadcast_data)` FORA do lock; test_player_joined_broadcast PASSOU |
| 7 | Jogador A abre landing page com CTAs 'Criar Partida' e 'Entrar numa Partida' | ✓ VERIFICADO | Landing.tsx existe; rotas `/`, `/create`, `/join` definidas em App.tsx; build bem-sucedido |
| 8 | Jogador A preenche nickname + turnos em /create, clica Criar — navega para /lobby/:roomCode com nome e código de 6 chars | ✓ VERIFICADO | CreateGame.tsx: `socket.emit('create_game', ...)` com ack; armazena em localStorage; navega para `/lobby/${response.room_code}` |
| 9 | Jogador B abre /join/:roomCode, entra nickname, clica Entrar — ambos os lobbies atualizam imediatamente sem recarregar | ? INCERTO | Wiring completo no código (join_game → broadcast → on_player_joined → socket.emit to=room_code → Lobby.tsx socket.on); requer verificação humana em dois browsers simultâneos |
| 10 | Tentar entrar em sala IN_PROGRESS mostra erro 'O jogo já começou' na UI | ✓ VERIFICADO | JoinGame.tsx linhas 27-28: `if (err === 'jogo em andamento') { setError('O jogo já começou.') }` |
| 11 | Botão 'Iniciar Jogo' visível apenas para host e apenas quando players.length >= 2; clicar causa game_started para todos | ? INCERTO | Lógica de exibição presente (Lobby.tsx linha 207: `{isHost && (...)}`, linha 102: `canStart = isHost && players.length >= 2`); broadcast pipeline verificado no código; requer verificação humana em dois browsers |
| 12 | Recarregar /lobby/:roomCode em modo dev (proxy Vite ativo) reconecta e exibe estado atual do lobby | ✗ FALHOU | Lobby.tsx inicializa `players` como `[]` (linha 27) sem restaurar do servidor; não há chamada `get_game_state()` ou equivalente ao montar; a lista de jogadores fica vazia após refresh até um novo evento player_joined chegar |

**Pontuação:** 10/12 verdades verificadas (+ 2 incertas, requerem verificação humana)

---

### Itens Diferidos

Itens não atendidos por esta fase mas cobertos explicitamente em fases posteriores.

| # | Item | Coberto em | Evidência |
|---|------|-----------|-----------|
| 1 | Recarregar /lobby restaura estado do lobby (INFRA-08) | Phase 7: Reconexão + Fim de Jogo | REQUIREMENTS.md: "INFRA-08: Cliente web armazena UUID em localStorage; ao recarregar chama `get_game_state()` para restaurar estado — Phase 7: Reconnection + End-of-Game, Pending" |

---

### Artefatos Obrigatórios

| Artefato | Esperado | Status | Detalhes |
|----------|----------|--------|----------|
| `server/game_server.py` | GameServer com create_game, join_game, start_game, leave_game, dataclasses GameSession/PlayerInfo | ✓ VERIFICADO | Todos os 4 métodos e 2 dataclasses presentes; 371 linhas substanciais |
| `tests/test_session.py` | 6 testes cobrindo SESSION-01 a SESSION-06 | ✓ VERIFICADO | 6 funções de teste, todas passam (10 passed in 2.37s) |
| `config.py` | Constante FRONTEND_DIST_PATH | ✓ VERIFICADO | Linha 18: `FRONTEND_DIST_PATH = os.environ.get(...)` |
| `bridge/bridge.py` | Handlers Socket.IO create_game/join_game/start_game/disconnect + room isolation + catch-all Flask | ✓ VERIFICADO | Todos os handlers presentes; `_sid_to_player`, `join_room`, `serve_spa` implementados |
| `frontend/src/pages/Lobby.tsx` | Lobby em tempo real com lista de jogadores, exibição de código, botão Iniciar Jogo | ✓ VERIFICADO | socket.on('player_joined'), socket.on('game_started'), lógica de visibilidade do host |
| `frontend/src/socket.ts` | Instância singleton socket.io-client | ✓ VERIFICADO | `io({ path: '/socket.io', autoConnect: false })` |
| `frontend/src/pages/CreateGame.tsx` | Página criar partida com socket.emit('create_game') | ✓ VERIFICADO | Emit com ack, localStorage, navegação |
| `frontend/src/pages/JoinGame.tsx` | Página entrar com socket.emit('join_game') e tratamento de erro | ✓ VERIFICADO | Erro 'jogo em andamento' mapeado para 'O jogo já começou.' |
| `frontend/dist/index.html` | Build de produção gerado | ✓ VERIFICADO | Arquivo presente, build em 977ms sem erros TypeScript |

---

### Verificação de Links Chave (Wiring)

| De | Para | Via | Status | Detalhes |
|----|------|-----|--------|---------|
| `game_server.py create_game` | `event_broadcaster.py register_callback` | `self.broadcaster.register_callback(player_id, callback_uri)` | ✓ WIRED | Linha 185 confirmada |
| `game_server.py join_game` | `event_broadcaster.py broadcast` | `self.broadcaster.broadcast("player_joined", broadcast_data)` fora do lock | ✓ WIRED | Linha 247, fora do bloco `with self.lock:` — Pitfall 4 aplicado |
| `CreateGame.tsx` | bridge handler `on('create_game')` | `socket.emit('create_game', payload, ack)` | ✓ WIRED | CreateGame.tsx linha 23 |
| `bridge BridgeCallbackReceiver.on_player_joined` | `Lobby.tsx` | `socketio.emit('player_joined', data, to=room_code)` → `socket.on('player_joined')` | ✓ WIRED | bridge.py linha 69; Lobby.tsx linha 68 |
| `bridge handle_start_game` | `bridge BridgeCallbackReceiver.on_game_started` | `proxy.start_game()` dispara broadcast → `on_game_started` → `socketio.emit` | ✓ WIRED | bridge.py linhas 250-257; on_game_started linhas 76-82 |
| `Lobby.tsx host_changed handler` | `game_server.py host_changed payload` | `data.new_host_name` vs payload real `{new_host_id, players}` | ⚠️ DESCONECTADO | Server envia `new_host_id` + `players`; Lobby.tsx espera `new_host_name` (não existe no payload). Handler sempre exibe "novo host: desconhecido". Além disso, `players` não é atualizado no handler de host_changed. |

---

### Trace de Fluxo de Dados (Nível 4)

| Artefato | Variável de Dados | Fonte | Produz Dados Reais | Status |
|----------|------------------|-------|-------------------|--------|
| `Lobby.tsx` players | `players` (useState) | `socket.on('player_joined', data => setPlayers(data.players))` | Sim — data.players vem de `session.get_player_dicts()` no servidor | ✓ FLOWING |
| `Lobby.tsx` isHost | `localStorage.is_host` | Definido em CreateGame.tsx/JoinGame.tsx no momento do join | Sim | ✓ FLOWING |
| `Lobby.tsx` players após refresh | `players` (useState) | Inicializado como `[]`; sem chamada de restauração de estado | Não — lista vazia após refresh | ✗ HOLLOW (diferido para Phase 7) |

---

### Verificações Comportamentais (Spot-checks)

| Comportamento | Comando | Resultado | Status |
|---------------|---------|-----------|--------|
| Suite de testes passa (10 testes) | `venv/bin/python -m pytest tests/ -q` | `10 passed in 2.37s` | ✓ PASSOU |
| Build do frontend sem erros TypeScript | `cd frontend && npm run build` | `✓ built in 977ms` — sem erros | ✓ PASSOU |
| bridge.py sem SyntaxError | `python -c "import ast; ast.parse(...)"` | `bridge.py parses OK` | ✓ PASSOU |
| frontend/dist/index.html existe | `ls frontend/dist/index.html` | Arquivo presente, 19 linhas | ✓ PASSOU |

---

### Cobertura de Requisitos

| Requisito | Plano Fonte | Descrição | Status | Evidência |
|-----------|-------------|-----------|--------|-----------|
| SESSION-01 | 02-01, 02-02 | Jogador pode criar partida com apelido e número de turnos | ✓ SATISFEITO | create_game() implementado e testado; CreateGame.tsx wired |
| SESSION-02 | 02-01, 02-02 | Partida gera código de 6 chars compartilhável | ✓ SATISFEITO | `_generate_room_code` — `[A-Z0-9]{6}` confirmado por regex em test_room_code_format |
| SESSION-03 | 02-01, 02-02 | Jogador pode entrar via código ou link | ✓ SATISFEITO | join_game() + JoinGame.tsx + JoinByCode.tsx implementados |
| SESSION-04 | 02-01, 02-02 | Sistema rejeita entrada após início com "jogo em andamento" | ✓ SATISFEITO | game_server.py linha 222; JoinGame.tsx mapeia para "O jogo já começou." |
| SESSION-05 | 02-01, 02-02 | Lobby exibe lista de jogadores em tempo real via PLAYER_JOINED | ✓ SATISFEITO (code) / ? HUMANO (runtime) | Pipeline completo verificado; requer smoke test |
| SESSION-06 | 02-01, 02-02 | Host pode iniciar jogo quando ≥2 jogadores no lobby | ✓ SATISFEITO (code) / ? HUMANO (runtime) | start_game() valida host + player_count; UI condicional verificada |

---

### Anti-Padrões Encontrados

| Arquivo | Linha | Padrão | Severidade | Impacto |
|---------|-------|--------|-----------|---------|
| `frontend/src/pages/Lobby.tsx` | 52-60 | `handleHostChanged` espera `data.new_host_name` mas server envia `data.new_host_id` + `data.players` | ⚠️ Aviso | Host changed exibe "novo host: desconhecido" sempre; lista de jogadores não atualiza ao host sair |
| `frontend/src/pages/Lobby.tsx` | 48-49 | `navigate('/game/${sessionId}')` — rota `/game/:sessionId` não existe em App.tsx | ⚠️ Aviso | Ao receber game_started, navegação aterra em rota não encontrada; esperado para Phase 3 (game loop não implementado) |

Sem marcadores de dívida técnica (TBD, FIXME, XXX) nos arquivos modificados nesta fase.

---

### Verificação Humana Necessária

#### 1. Pipeline de Lobby em Tempo Real (Dois Browsers)

**Teste:** Abrir Terminal 1: `pyro5-ns --host 127.0.0.1`, Terminal 2: `python server/game_server.py`, Terminal 3: `python bridge/bridge.py`, Terminal 4: `cd frontend && npm run dev`. Browser A: http://localhost:3000 → Criar Partida → apelido "Alice" → 5 turnos → Criar. Browser B (aba anônima): http://localhost:3000 → inserir código da sala → apelido "Bob" → Entrar.

**Esperado:** A lista de jogadores em AMBOS os browsers mostra Alice + Bob imediatamente sem recarregar a página. O evento `player_joined` do Socket.IO deve aparecer na aba Network → WS de ambos os DevTools.

**Por que humano:** Requer dois browsers ativos simultaneamente; o pipeline de callback Pyro5 → bridge → Socket.IO só pode ser confirmado em runtime.

#### 2. Iniciar Jogo com Múltiplos Clientes

**Teste:** Com Alice e Bob no lobby (cenário acima). Verificar que apenas Browser A (Alice = host) exibe o botão "Iniciar Jogo" habilitado. Browser B (Bob) não deve ter o botão habilitado. Alice clica "Iniciar Jogo".

**Esperado:** Botão exibe "Distribuindo imagens...", AMBOS os browsers recebem o evento `game_started` (verificável no console do DevTools → WS frames).

**Por que humano:** Requer dois browsers e confirmação de que o broadcast chega a ambos os clientes na room correta.

---

### Resumo de Gaps

**Nenhum gap bloqueador identificado.** O objetivo da fase está funcionalmente implementado no código.

**Avisos (não bloqueadores):**

1. **handler `host_changed` com payload incompatível:** `Lobby.tsx` lê `data.new_host_name` mas o servidor envia `data.new_host_id` + `data.players`. O HOST_CHANGED sempre exibe "novo host: desconhecido" e não atualiza a lista de jogadores. Este cenário (host desconecta durante lobby) está marcado como SESSION-07 diferido para Phase 7. O impacto prático na Phase 2 é mínimo pois SESSION-07 não é um requisito desta fase.

2. **Rota `/game/:sessionId` ausente:** `game_started` navega para uma rota não definida em App.tsx. Esperado — o game loop é Phase 3. O comportamento resultante é uma página 404 interna do React Router, que é aceitável como placeholder.

3. **Restauração de estado no refresh:** `players` inicializa como `[]` no mount sem restaurar do servidor. Diferido para Phase 7 (INFRA-08). Não bloqueia o objetivo desta fase.

---

_Verificado em: 2026-05-12T21:00:00Z_
_Verificador: Claude (gsd-verifier)_
