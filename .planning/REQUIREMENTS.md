# Requirements — Jogo de Adivinhação Multijogador RPC/Pyro5

## v1 Requirements

### RPC Infrastructure (INFRA)

- [x] **INFRA-01**: Sistema executa um Pyro5 daemon com GameServer exposto via `@Pyro5.api.expose`, acessível via Name Server
- [x] **INFRA-02**: Clientes registram callback URI no servidor via `register_callback(player_id, callback_uri)` para receber eventos push
- [x] **INFRA-03**: EventBroadcaster envia eventos para todos os callbacks registrados usando métodos `@oneway` (não bloqueia o thread do servidor)
- [x] **INFRA-04**: Bridge Flask-SocketIO (async_mode='threading') converte chamadas WebSocket do browser em chamadas Pyro5 RPC e repassa callbacks Pyro5 como eventos Socket.IO
- [x] **INFRA-05**: Bridge usa proxy Pyro5 por thread (não compartilhado) para evitar deadlock de concorrência
- [x] **INFRA-06**: Pyro5 Name Server disponível para descoberta de serviços (sem URIs hardcoded no cliente)
- [ ] **INFRA-07**: Jogador desconectado é identificado por falha de callback e removido da lista de callbacks ativos
- [ ] **INFRA-08**: Cliente web armazena UUID de sessão em localStorage; ao recarregar a página chama `get_game_state()` para restaurar estado

### Gerenciamento de Sessão (SESSION)

- [x] **SESSION-01**: Jogador pode criar partida informando apelido e número máximo de turnos (3, 5, 7 ou 10)
- [x] **SESSION-02**: Partida gera código de sessão de 6 caracteres compartilhável via link
- [x] **SESSION-03**: Jogador pode entrar em partida existente via código ou link de convite, informando apelido
- [x] **SESSION-04**: Sistema rejeita entrada de novos jogadores após início da partida com mensagem "jogo em andamento"
- [x] **SESSION-05**: Lobby exibe lista de jogadores conectados em tempo real via evento `PLAYER_JOINED`
- [x] **SESSION-06**: Host (primeiro jogador) pode iniciar o jogo quando ≥2 jogadores estão no lobby
- [ ] **SESSION-07**: Se host desconecta no lobby, próximo jogador na ordem de entrada assume como host

### Máquina de Estados de Turno (TURN)

- [ ] **TURN-01**: Servidor controla máquina de estados: WAITING → DISTRIBUTING → ROUND_START → HINT_PHASE → GUESS_PHASE → EXCHANGE_PHASE → SPY_PHASE → SCORING_PHASE → TURN_END
- [x] **TURN-02**: Cada fase tem timer configurável (30–60s) gerenciado por `threading.Timer` no servidor; ao expirar, fase avança automaticamente
- [x] **TURN-03**: Transição de fase envia evento broadcast `PHASE_CHANGED` para todos os clientes
- [x] **TURN-04**: Timer de fase usa generation counter para evitar race condition de timers obsoletos disparando após avanço manual

### Mecânica de Dicas (HINT)

- [x] **HINT-01**: Durante HINT_PHASE cada jogador envia exatamente uma palavra via `submit_hint(player_id, hint_word)`
- [x] **HINT-02**: Servidor broadcast `HINT_RECEIVED` para todos os clientes ao receber dica de qualquer jogador
- [x] **HINT-03**: Jogador que não enviar dica antes do timer recebe string vazia automaticamente (sem penalidade)
- [x] **HINT-04**: Fase avança para GUESS_PHASE automaticamente quando todos os jogadores enviaram dica ou timer expirou

### Mecânica de Palpites e Arbitragem (GUESS)

- [x] **GUESS-01**: Durante GUESS_PHASE jogador pode enviar palpite sobre objeto de outro jogador via `submit_guess(player_id, target_player, guess)`
- [x] **GUESS-02**: Jogador pode passar a vez via `skip_guess(player_id)`
- [ ] **GUESS-03**: Arbitragem verifica palpite por: (a) igualdade exata, (b) similaridade Wu-Palmer via NLTK `wn` + own-pt com threshold configurável, (c) fallback exact-match se WordNet retornar None
- [x] **GUESS-04**: Resultado da arbitragem é broadcast para todos via `GUESS_RESULT` com `is_correct: bool`
- [x] **GUESS-05**: Cada jogador pode tentar adivinhar apenas um objeto por turno

### Troca Privada de Dicas (EXCHANGE)

- [x] **EXCHANGE-01**: Durante EXCHANGE_PHASE jogador pode solicitar troca privada com outro jogador via `request_exchange(player_id, target_player)`, retorna exchange_id
- [x] **EXCHANGE-02**: Jogador receptor recebe notificação privada de pedido e pode aceitar/recusar via `respond_exchange(player_id, exchange_id, accept)`
- [x] **EXCHANGE-03**: Se aceito, ambos enviam uma palavra privada via `submit_exchange_hint(player_id, exchange_id, hint_word)` — pode ser verdadeira ou falsa
- [x] **EXCHANGE-04**: Servidor broadcast público `EXCHANGE_COMPLETED` para todos sem revelar conteúdo das dicas
- [x] **EXCHANGE-05**: Dicas privadas são entregues apenas aos dois participantes via evento privado
- [x] **EXCHANGE-06**: Cada jogador pode participar de no máximo uma troca por turno

### Mecânica de Espionagem (SPY)

- [x] **SPY-01**: Durante SPY_PHASE (simultâneo ao EXCHANGE) jogador pode tentar espiar troca ativa via `attempt_spy(player_id, exchange_id)`
- [x] **SPY-02**: Probabilidade de descoberta é 30% (configurável); se descoberto: espião perde 10pts e broadcast público `SPY_DISCOVERED` com nome do espião
- [x] **SPY-03**: Se não descoberto: espião recebe as duas dicas privadas em silêncio, nenhuma notificação pública
- [x] **SPY-04**: Jogador só pode espiar trocas das quais não é participante
- [x] **SPY-05**: Cada jogador pode espiar no máximo uma troca por turno

### Sistema de Pontuação (SCORE)

- [x] **SCORE-01**: Primeiro a acertar palpite recebe +20pts; segundo +15pts; terceiro +10pts; demais max(20-(N-1)\*5, 5)
- [x] **SCORE-02**: Se apenas um jogador acertou, recebe +10pts bônus
- [x] **SCORE-03**: Dono do objeto: +15pts se 1 acertou; +10 se 2; +5 se 3; max(15-(N-1)\*5, 0) para N acertaram; 0pts se ninguém acertou; -10pts se todos acertaram
- [x] **SCORE-04**: Pontuação calculada automaticamente ao fim de SCORING_PHASE e broadcast via `SCORE_UPDATED` com breakdown por jogador
- [x] **SCORE-05**: Placar acumulado disponível via `get_scores(player_id)` a qualquer momento

### Distribuição de Imagens (IMAGE)

- [x] **IMAGE-01**: Servidor possui banco de imagens em pasta local com mapeamento nome_arquivo → nome_objeto
- [x] **IMAGE-02**: No início de cada rodada servidor distribui uma imagem única por jogador via evento `OBJECT_ASSIGNED` contendo URL estática Flask (não bytes via Pyro5)
- [x] **IMAGE-03**: Imagens servidas como arquivos estáticos pela camada Flask, nunca via serialização Pyro5

### Chat em Tempo Real (CHAT)

- [ ] **CHAT-01**: Jogador pode enviar mensagem de chat via `send_chat(player_id, message)` a qualquer momento da partida
- [ ] **CHAT-02**: Mensagens de chat são broadcast para todos via `on_chat_message` callback
- [ ] **CHAT-03**: Chat é visualmente e funcionalmente separado das ações de jogo (inputs distintos, painéis distintos)
- [ ] **CHAT-04**: Interface não permite confundir campo de chat com campo de dica ou palpite

### Pós-Jogo (POSTGAME)

- [ ] **POSTGAME-01**: Após último turno exibe tela de resultados com pódio (top 3) e tabela de pontos por turno
- [ ] **POSTGAME-02**: Sistema inicia votação "continuar com novos objetos?" com timer de 30s
- [ ] **POSTGAME-03**: Se maioria vota continuar: servidor distribui novas imagens e jogo reinicia no turno 1
- [ ] **POSTGAME-04**: Se maioria vota encerrar (ou timer expira sem maioria para continuar): partida encerrada

### Interface Web (UI)

- [ ] **UI-01**: Landing page com CTA "Criar Partida" e CTA "Entrar em Partida" (campo de código)
- [ ] **UI-02**: Tela criar partida: input apelido + seleção número de turnos + botão criar
- [ ] **UI-03**: Lobby: lista de jogadores em tempo real, link de convite copiável, botão "Iniciar Jogo" (só host, ativo com ≥2 jogadores)
- [ ] **UI-04**: Tela principal de jogo: painel imagem secreta, dicas públicas por adversário (chips), zona de ação que muda por fase, placar/eventos/chat em tabs
- [ ] **UI-05**: Timer visual com mudança de cor: verde → amarelo (<10s) → vermelho (<5s)
- [ ] **UI-06**: Modais/overlays por fase: HINT (campo palavra única), GUESS (seleção alvo + palpite), EXCHANGE (solicitante e receptor), SPY (lista trocas + confirmação de risco), resultado de espionagem
- [ ] **UI-07**: Painel de scoring inline ao fim de cada turno com delta de pontos animado
- [ ] **UI-08**: Tela de resultados finais com pódio, tabela turno×jogador e votação com barra de progresso ao vivo
- [ ] **UI-09**: Banner de reconexão não-bloqueante com estado visual (âmbar: reconectando, vermelho: offline)
- [ ] **UI-10**: Separação visual radical entre chat e ações de jogo (cores, zonas, labels explícitos)

### Relatório Técnico (REPORT)

- [ ] **REPORT-01**: Relatório inclui introdução ao Pyro5 com comparativo de tecnologias RPC e justificativa da escolha
- [ ] **REPORT-02**: Relatório descreve a arquitetura do sistema com diagrama de componentes e diagramas de sequência de comunicação RPC
- [ ] **REPORT-03**: Relatório inclui capturas de tela da aplicação funcionando e trechos de código relevantes
- [ ] **REPORT-04**: Relatório inclui instruções completas de instalação e execução

---

## v2 Requirements (deferred)

- Configuração de probabilidade de espionagem pelo host (fixo em 30% no MVP)
- Bônus de espionagem bem-sucedida (+5pts) — marcado como opcional no PRD
- Modo espectador
- Histórico de partida persistente (WEB-019)
- Timer configurável por fase pelo host
- Tela 404 genérica (WEB-018)
- Autenticação / contas entre sessões
- Múltiplos idiomas

---

## Out of Scope

- Java RMI, gRPC, RPyC — Pyro5 confirmado como único framework RPC
- Sockets diretos (TCP/UDP) entre quaisquer componentes — violação do requisito acadêmico
- Upload de imagens pelo usuário — imagens fornecidas pelo servidor
- Banco de dados / persistência entre sessões
- Modo pausa de jogo
- Moderação de chat

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| INFRA-01 | Phase 1: RPC Infrastructure + Callback Pipeline | Complete |
| INFRA-02 | Phase 1: RPC Infrastructure + Callback Pipeline | Complete |
| INFRA-03 | Phase 1: RPC Infrastructure + Callback Pipeline | Complete |
| INFRA-04 | Phase 1: RPC Infrastructure + Callback Pipeline | Complete |
| INFRA-05 | Phase 1: RPC Infrastructure + Callback Pipeline | Complete |
| INFRA-06 | Phase 1: RPC Infrastructure + Callback Pipeline | Complete |
| INFRA-07 | Phase 7: Reconnection + End-of-Game | Pending |
| INFRA-08 | Phase 7: Reconnection + End-of-Game | Pending |
| SESSION-01 | Phase 2: Player Session + Lobby | Complete |
| SESSION-02 | Phase 2: Player Session + Lobby | Complete |
| SESSION-03 | Phase 2: Player Session + Lobby | Complete |
| SESSION-04 | Phase 2: Player Session + Lobby | Complete |
| SESSION-05 | Phase 2: Player Session + Lobby | Complete |
| SESSION-06 | Phase 2: Player Session + Lobby | Complete |
| SESSION-07 | Phase 7: Reconnection + End-of-Game | Pending |
| TURN-01 | Phase 3: Phase Machine + Timer | Pending |
| TURN-02 | Phase 3: Phase Machine + Timer | Complete |
| TURN-03 | Phase 3: Phase Machine + Timer | Complete |
| TURN-04 | Phase 3: Phase Machine + Timer | Complete |
| HINT-01 | Phase 4: Core Turn Loop | Complete |
| HINT-02 | Phase 4: Core Turn Loop | Complete |
| HINT-03 | Phase 4: Core Turn Loop | Complete |
| HINT-04 | Phase 4: Core Turn Loop | Complete |
| GUESS-01 | Phase 4: Core Turn Loop | Complete |
| GUESS-02 | Phase 4: Core Turn Loop | Complete |
| GUESS-03 | Phase 6: Synonym Arbitration | Pending |
| GUESS-04 | Phase 4: Core Turn Loop | Complete |
| GUESS-05 | Phase 4: Core Turn Loop | Complete |
| EXCHANGE-01 | Phase 5: Exchange + Spy Mechanics | Complete |
| EXCHANGE-02 | Phase 5: Exchange + Spy Mechanics | Complete |
| EXCHANGE-03 | Phase 5: Exchange + Spy Mechanics | Complete |
| EXCHANGE-04 | Phase 5: Exchange + Spy Mechanics | Complete |
| EXCHANGE-05 | Phase 5: Exchange + Spy Mechanics | Complete |
| EXCHANGE-06 | Phase 5: Exchange + Spy Mechanics | Complete |
| SPY-01 | Phase 5: Exchange + Spy Mechanics | Complete |
| SPY-02 | Phase 5: Exchange + Spy Mechanics | Complete |
| SPY-03 | Phase 5: Exchange + Spy Mechanics | Complete |
| SPY-04 | Phase 5: Exchange + Spy Mechanics | Complete |
| SPY-05 | Phase 5: Exchange + Spy Mechanics | Complete |
| SCORE-01 | Phase 4: Core Turn Loop | Complete |
| SCORE-02 | Phase 4: Core Turn Loop | Complete |
| SCORE-03 | Phase 4: Core Turn Loop | Complete |
| SCORE-04 | Phase 4: Core Turn Loop | Complete |
| SCORE-05 | Phase 4: Core Turn Loop | Complete |
| IMAGE-01 | Phase 4: Core Turn Loop | Complete |
| IMAGE-02 | Phase 4: Core Turn Loop | Complete |
| IMAGE-03 | Phase 4: Core Turn Loop | Complete |
| CHAT-01 | Phase 7: Reconnection + End-of-Game | Pending |
| CHAT-02 | Phase 7: Reconnection + End-of-Game | Pending |
| CHAT-03 | Phase 7: Reconnection + End-of-Game | Pending |
| CHAT-04 | Phase 7: Reconnection + End-of-Game | Pending |
| POSTGAME-01 | Phase 7: Reconnection + End-of-Game | Pending |
| POSTGAME-02 | Phase 7: Reconnection + End-of-Game | Pending |
| POSTGAME-03 | Phase 7: Reconnection + End-of-Game | Pending |
| POSTGAME-04 | Phase 7: Reconnection + End-of-Game | Pending |
| UI-01 | Phase 8: UI Polish + Technical Report | Pending |
| UI-02 | Phase 8: UI Polish + Technical Report | Pending |
| UI-03 | Phase 8: UI Polish + Technical Report | Pending |
| UI-04 | Phase 8: UI Polish + Technical Report | Pending |
| UI-05 | Phase 8: UI Polish + Technical Report | Pending |
| UI-06 | Phase 8: UI Polish + Technical Report | Pending |
| UI-07 | Phase 8: UI Polish + Technical Report | Pending |
| UI-08 | Phase 8: UI Polish + Technical Report | Pending |
| UI-09 | Phase 8: UI Polish + Technical Report | Pending |
| UI-10 | Phase 8: UI Polish + Technical Report | Pending |
| REPORT-01 | Phase 8: UI Polish + Technical Report | Pending |
| REPORT-02 | Phase 8: UI Polish + Technical Report | Pending |
| REPORT-03 | Phase 8: UI Polish + Technical Report | Pending |
| REPORT-04 | Phase 8: UI Polish + Technical Report | Pending |
