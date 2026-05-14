# Arquitetura de Interface — Jogo de Adivinhação Multijogador
### Source of Truth de UI/UX | Versão 1.0

---

## 1. Visão Geral da Aplicação

**Tipo de produto:** Web app responsivo multijogador em tempo real, com mecânicas de turnos, comunicação privada e pontuação automática.

**Objetivo principal da experiência:** Reunir 2–6 jogadores em uma sessão de adivinhação baseada em dicas, onde cada um defende o segredo da própria imagem enquanto tenta descobrir as dos outros — com traição, espionagem e blefe como mecânicas centrais.

**Papel da interface:** A UI é o árbitro visual do jogo. Ela precisa apresentar simultaneamente o estado público do jogo (dicas, palpites, placar, log de eventos), o estado privado do jogador (imagem secreta, dicas recebidas em troca) e a área de comunicação (chat separado), sem causar confusão entre esses contextos. A separação clara entre ações de jogo e chat é requisito funcional crítico.

**Contexto técnico:** O backend opera via RPC/Pyro5 com event callbacks. A UI recebe eventos push do servidor e deve reagir a eles em tempo real sem recarregar página. O modelo mental do jogador é orientado a fases de turno com timer visível.

---

## 2. Personas e Papéis de Usuário

### Jogador Anônimo (Visitante)
Chega via link direto ou acesso à URL raiz. Não tem conta. Quer entrar numa sessão rapidamente com um apelido.

**Necessidades principais:**
- Entrar no jogo sem fricção (sem cadastro obrigatório)
- Entender as regras antes de começar
- Receber confirmação de que entrou na sessão

### Jogador Conectado (Participante)
Está em uma sessão ativa. Pode ser o criador ou um convidado.

**Necessidades principais:**
- Ver claramente em qual fase do turno está
- Distinguir sua imagem secreta das dicas dos outros
- Realizar ações (dica, palpite, troca, espionagem) dentro do tempo
- Monitorar o placar e o log de eventos
- Usar o chat sem confundir com ações de jogo

### Criador da Partida (Host)
É o primeiro jogador a criar a sessão. Tem controle adicional.

**Necessidades principais:**
- Configurar número máximo de turnos
- Decidir quando iniciar o jogo (após jogadores suficientes)
- Votar para continuar ou encerrar no pós-jogo

### Espectador Potencial *(premissa)*
O PRD não menciona explicitamente. **Premissa adotada:** não há modo espectador no MVP. Apenas jogadores ativos participam.

---

## 3. Mapa Geral de Navegação

```
ÁREA PÚBLICA
├── / ................................ Landing Page
└── /rules .......................... Regras do Jogo

ENTRADA NA SESSÃO
├── /join ........................... Tela de entrada (nome + código)
├── /join/:sessionCode .............. Entrada via link de convite
└── /create ......................... Criar nova partida

LOBBY
└── /lobby/:sessionId ............... Sala de espera pré-jogo

GAMEPLAY (rota protegida — só jogadores da sessão)
└── /game/:sessionId ................ Tela principal de jogo
    ├── [Estado: HINT_PHASE]
    ├── [Estado: GUESS_PHASE]
    ├── [Estado: EXCHANGE_PHASE]
    ├── [Estado: SPY_PHASE]
    └── [Estado: SCORING_PHASE]

PÓS-JOGO
└── /game/:sessionId/results ........ Resultados e votação

ERROS / UTILIDADES
├── /404 ............................ Página não encontrada
├── /error/session-expired .......... Sessão expirada
└── /error/invalid-invite ........... Convite inválido
```

---

## 4. Fluxos Principais de Usuário

---

### Fluxo 1: Criar e iniciar uma partida

1. Jogador acessa `/`
2. Clica em "Criar Partida"
3. É direcionado para `/create`
4. Informa apelido e número máximo de turnos (ex: 5–10)
5. Sistema cria sessão e redireciona para `/lobby/:sessionId`
6. Lobby exibe código/link de convite para compartilhar
7. Outros jogadores entram via link ou código
8. Quando ≥2 jogadores estão prontos, botão "Iniciar Jogo" fica disponível
9. Host clica em "Iniciar Jogo"
10. Servidor distribui imagens e todos são redirecionados para `/game/:sessionId`

---

### Fluxo 2: Entrar numa partida via convite

1. Jogador recebe link (ex: `app.com/join/ABC123`)
2. Acessa o link
3. Sistema verifica se a sessão existe e está aberta
4. Se sim: exibe campo para apelido → jogador digita e confirma
5. Sistema entra na sessão e redireciona para `/lobby/:sessionId`
6. Se sessão inválida/expirada: exibe tela de erro com opção de criar nova partida

---

### Fluxo 3: Turno completo (visão de um jogador)

**HINT_PHASE (30–60s)**
1. Jogador vê sua imagem secreta e o timer
2. Digita uma palavra no campo de dica e envia
3. À medida que outros enviam, as dicas aparecem no painel público
4. Timer encerra a fase automaticamente (dica vazia enviada para quem não interagiu)

**GUESS_PHASE (30–60s)**
1. Jogador vê as dicas públicas de cada adversário
2. Escolhe um jogador para tentar adivinhar (dropdown ou card selecionável)
3. Digita o palpite e confirma, ou clica em "Passar a vez"
4. Sistema processa via arbitragem e exibe resultado imediatamente

**EXCHANGE_PHASE (30–60s)**
1. Jogador pode solicitar troca privada com 1 adversário
2. Se solicitar: seleciona jogador e confirma pedido
3. Adversário recebe notificação e aceita/recusa
4. Se aceito: ambos digitam uma palavra privada
5. Todos os jogadores recebem notificação pública de que a troca ocorreu (sem conteúdo)

**SPY_PHASE (simultâneo à Exchange)**
1. Jogador vê trocas privadas em andamento (sem conteúdo)
2. Pode escolher espiar uma troca (com risco de 30%)
3. Sistema resolve: se descoberto, perde 10pts e alerta público é emitido
4. Se bem-sucedido, recebe as dicas privadas em silêncio

**SCORING_PHASE (automático)**
1. Arbitragem valida todos os palpites
2. Pontos são calculados e distribuídos
3. Placar atualizado com animação de destaque

---

### Fluxo 4: Pós-jogo e votação para continuar

1. Último turno encerra → redirecionamento para `/game/:sessionId/results`
2. Tela exibe ranking final com pontuação e breakdown por rodada
3. Sistema exibe votação: "Continuar com novos objetos?" / "Encerrar"
4. Cada jogador vota (timer de 30s)
5. Se maioria vota continuar → servidor distribui novas imagens → jogo reinicia no turno 1
6. Se maioria vota encerrar → tela de resultados finais com opção de nova partida

---

### Fluxo 5: Reconexão durante partida

1. Jogador perde conexão
2. Sistema exibe banner "Conexão perdida — reconectando..."
3. Se reconectar em < 60s: estado do jogo é restaurado via `get_game_state`
4. Se não reconectar: jogador é marcado como DISCONNECTED, jogo continua sem ele
5. Ao tentar acessar novamente a URL: sistema verifica se sessão ainda está ativa e se jogador pertence a ela

---

## 5. Inventário Completo de Telas

| ID | Tela | Rota sugerida | Objetivo | Descrição sucinta | Usuários | Prioridade |
|---|---|---|---|---|---|---|
| WEB-001 | Landing Page | `/` | Apresentar o jogo e capturar interesse | Hero com conceito, regras resumidas e CTAs principais | Visitante | Alta |
| WEB-002 | Criar Partida | `/create` | Configurar e iniciar uma nova sessão | Form com apelido e número de turnos | Visitante/Host | Alta |
| WEB-003 | Entrar na Partida | `/join` | Ingressar em sessão existente | Campo de apelido + código da sessão | Visitante | Alta |
| WEB-004 | Entrada via Convite | `/join/:code` | Entrada direta por link de convite | Versão simplificada do WEB-003, pré-preenchida | Visitante | Alta |
| WEB-005 | Lobby | `/lobby/:sessionId` | Aguardar jogadores e iniciar | Lista de jogadores, link de convite, botão iniciar | Host/Participante | Alta |
| WEB-006 | Tela Principal de Jogo | `/game/:sessionId` | Interface central durante toda a partida | Layout em painéis: imagem, dicas, ações, placar, chat | Participante | Alta |
| WEB-007 | Modal: Fase de Dica | (overlay em WEB-006) | Enviar dica pública do turno | Campo de texto single-word + submit + timer | Participante | Alta |
| WEB-008 | Modal: Fase de Palpite | (overlay em WEB-006) | Escolher alvo e enviar palpite | Seleção de jogador alvo + campo de palpite | Participante | Alta |
| WEB-009 | Modal: Troca Privada (solicitante) | (overlay em WEB-006) | Solicitar e realizar troca | Seleção de parceiro + digitação de dica privada | Participante | Alta |
| WEB-010 | Modal: Troca Privada (receptor) | (overlay em WEB-006) | Responder pedido de troca | Aceitar/recusar + digitação de dica | Participante | Alta |
| WEB-011 | Modal: Espionagem | (overlay em WEB-006) | Tentar espiar uma troca ativa | Lista de trocas em andamento + botão espiar com aviso de risco | Participante | Alta |
| WEB-012 | Modal: Resultado da Espionagem | (overlay em WEB-006) | Feedback de sucesso ou penalidade | Card revelando se foi descoberto, pontos perdidos ou dica obtida | Participante | Alta |
| WEB-013 | Painel de Scoring (inline) | (seção em WEB-006) | Mostrar resultado do turno | Breakdown de pontos ganhos/perdidos por jogador | Participante | Alta |
| WEB-014 | Tela de Resultados Finais | `/game/:sessionId/results` | Ranking e votação pós-jogo | Pódio, pontuação por turno, votação para continuar | Participante | Alta |
| WEB-015 | Regras do Jogo | `/rules` | Explicar as mecânicas em detalhe | Texto estruturado com exemplos visuais, fases do turno | Visitante/Jogador | Média |
| WEB-016 | Tela de Erro — Sessão Inválida | `/error/invalid-invite` | Informar convite expirado/inválido | Mensagem clara + CTA para criar ou entrar em sessão | Visitante | Média |
| WEB-017 | Tela de Erro — Sessão Expirada | `/error/session-expired` | Informar sessão encerrada | Mensagem + histórico se disponível + CTA nova partida | Participante | Média |
| WEB-018 | Tela 404 | `/404` | Rota não encontrada | Página genérica de erro com navegação | Qualquer | Baixa |
| WEB-019 | Histórico de Partida | `/game/:sessionId/history` | Revisar log completo após fim | Timeline de todos os eventos da partida | Participante | Baixa |

---

## 6. Detalhamento de Cada Tela

---

### WEB-001 — Landing Page

**Objetivo:** Apresentar o conceito do jogo, gerar interesse e direcionar para criação ou ingresso em partida.

**Descrição sucinta:** Página de entrada com hero visual explicando a proposta, resumo das mecânicas principais (dicas, espionagem, blefe) e dois CTAs claros: "Criar Partida" e "Entrar numa Partida".

**Principais elementos de interface:**
- Header fixo com logo e link para regras
- Hero section: título do jogo, tagline, ilustração temática
- Cards explicativos das 3 mecânicas principais (dicas, trocas privadas, espionagem)
- CTA primário: botão "Criar Partida" → `/create`
- CTA secundário: campo de código + botão "Entrar" → `/join/:code`
- Seção "Como funciona" com fases do turno ilustradas
- Footer com link para regras detalhadas

**Ações do usuário:**
- Clicar em "Criar Partida"
- Digitar código de sessão e clicar em "Entrar"
- Clicar em "Ver Regras"

**Estados necessários:**
- Default (landing limpa)
- Input de código com erro de validação ("Código inválido")

**Notas de UX:** Os dois CTAs devem ter hierarquia visual clara — "Criar" como primário, "Entrar" como secundário. O campo de código deve aceitar entrada em letras maiúsculas/minúsculas e normalizar automaticamente.

**Considerações mobile:** Stack vertical dos CTAs. Hero simplificado (sem ilustração grande). Cards de mecânicas em carrossel ou accordion. Botão fixo "Criar Partida" no rodapé mobile.

---

### WEB-002 — Criar Partida

**Objetivo:** Configurar a sessão e tornar o usuário o host.

**Descrição sucinta:** Formulário simples com dois campos: apelido do jogador e número máximo de turnos. Após confirmar, a sessão é criada e o usuário vai para o lobby.

**Principais elementos de interface:**
- Título "Nova Partida"
- Input: Apelido (max 20 chars, sem caracteres especiais)
- Select/slider: Número de turnos (3, 5, 7, 10)
- Checkbox opcional: configuração de probabilidade de espionagem (premissa: exposta apenas se a aplicação suportar customização)
- Botão "Criar" (primary)
- Link "Voltar" / cancelar

**Ações do usuário:**
- Preencher apelido
- Selecionar número de turnos
- Confirmar criação

**Estados necessários:**
- Loading: após submit, spinner no botão e desabilitar campos
- Error state: apelido já em uso na sessão (improvável aqui, mas validar)
- Error state: falha de conexão com servidor

**Notas de UX:** Turno padrão sugerido de 5 é razoável para primeira partida. Exibir preview do tempo estimado de jogo ("~15 min" para 5 turnos) ajuda na decisão.

**Considerações mobile:** Layout de coluna única. Campos full-width. Botão fixo no rodapé.

---

### WEB-003 / WEB-004 — Entrar na Partida

**Objetivo:** Ingressar em sessão existente com um apelido.

**Descrição sucinta:** WEB-003 apresenta campo de código de sessão + apelido. WEB-004 (via link) pré-preenche o código e só pede o apelido.

**Principais elementos de interface:**
- Input: Código da sessão (6 chars, auto-uppercase) — apenas no WEB-003
- Input: Apelido
- Botão "Entrar"
- Preview da sessão após validar código: número de jogadores aguardando

**Ações do usuário:**
- Digitar código e apelido
- Confirmar entrada

**Estados necessários:**
- Validando código (loading inline no campo)
- Código inválido (inline error)
- Sessão cheia (error com CTA para criar nova)
- Sessão já iniciada (error: "O jogo já começou")
- Apelido duplicado na sessão (error inline)

**Notas de UX:** Validação do código deve acontecer ao sair do campo (onBlur), não apenas no submit. Exibir quantos jogadores já estão no lobby ao validar o código cria antecipação.

**Considerações mobile:** Mesmas considerações do WEB-002.

---

### WEB-005 — Lobby

**Objetivo:** Reunir jogadores, exibir link de convite e permitir que o host inicie a partida.

**Descrição sucinta:** Tela de espera com lista ao vivo de jogadores conectados, link/código para compartilhar e botão "Iniciar" (apenas para o host, habilitado quando ≥2 jogadores).

**Principais elementos de interface:**
- Header: nome da sessão + código de convite copiável
- Botão "Copiar Link" com feedback de confirmação
- Lista de jogadores: avatar gerado, apelido, badge "Host" para o criador
- Indicador de mínimo de jogadores ("2/6 jogadores — mínimo atingido")
- Botão "Iniciar Jogo" (só host, desabilitado com < 2 jogadores)
- Badge de status por jogador: "Pronto" / "Aguardando"
- Contador de tempo de espera (opcional, pressão social)
- Botão "Sair" para abandonar o lobby

**Ações do usuário:**
- Copiar link de convite
- Aguardar outros jogadores
- (Host) Iniciar jogo quando pronto

**Estados necessários:**
- Waiting (< 2 jogadores): botão Iniciar desabilitado
- Ready (≥ 2 jogadores): botão Iniciar ativo
- Loading (iniciando): spinner + mensagem "Distribuindo imagens..."
- Player joined: animação de entrada na lista
- Player left: remoção com animação e toast informativo

**Notas de UX:** O código de sessão deve ser grande e legível (facilitando digitação manual em outro dispositivo). A lista de jogadores deve atualizar em tempo real via evento `PLAYER_JOINED`. Exibir claramente quem é o host.

**Considerações mobile:** Lista de jogadores em cards verticais. Link de convite com botão nativo de compartilhamento (Web Share API).

---

### WEB-006 — Tela Principal de Jogo

**Objetivo:** Interface central que contém todos os elementos do jogo durante a partida, reagindo a cada fase do turno.

**Descrição sucinta:** Layout em 4 zonas principais: (1) painel superior com turno, fase e timer; (2) zona esquerda com a imagem secreta do jogador e dicas recebidas; (3) zona central com ações do turno atual; (4) zona direita com placar + log de eventos + chat.

**Principais elementos de interface:**

*Header de Jogo:*
- Badge: "Turno X / Y"
- Badge: Fase atual (DICA / PALPITE / TROCA / ESPIONAGEM / PONTUAÇÃO)
- Timer countdown animado (círculo progressivo ou barra)
- Indicador de conexão

*Painel Minha Imagem:*
- Imagem do objeto secreto do jogador (bem visível)
- Label "Seu objeto — só você vê isso"
- Miniaturas dos outros jogadores (avatares) com suas dicas públicas acumuladas embaixo

*Zona de Ação (muda por fase):*
- HINT_PHASE: input de uma palavra + botão Enviar + feedback "Dica enviada ✓"
- GUESS_PHASE: seletor de jogador alvo + input de palpite + botão Enviar + botão Passar
- EXCHANGE_PHASE: lista de jogadores disponíveis + botão Solicitar Troca + indicador de trocas em andamento + botão Espiar
- SPY_PHASE: integrado ao EXCHANGE
- SCORING_PHASE: card de pontuação do turno (automático, sem ação)

*Painel Direito — 3 tabs:*
- Tab "Placar": ranking atualizado em tempo real
- Tab "Eventos": log cronológico de todos os eventos públicos
- Tab "Chat": histórico de mensagens + input

**Ações do usuário:**
- Enviar dica (HINT_PHASE)
- Enviar palpite ou passar (GUESS_PHASE)
- Solicitar troca / aceitar troca / enviar dica privada (EXCHANGE_PHASE)
- Tentar espionar uma troca (SPY_PHASE)
- Enviar mensagem no chat (qualquer fase)
- Clicar na tab do painel direito

**Estados necessários:**
- Por fase: UI de ação muda completamente com transição suave
- Ação já realizada: campo desabilitado + confirmação visual ("Dica enviada")
- Aguardando outros jogadores: spinner + "Aguardando X jogadores..."
- Reconectando: banner overlay com spinner
- Offline: banner vermelho + freeze da UI
- Timer expirado: transição automática de fase com animação
- Palpite correto: toast verde + incremento no placar
- Palpite errado: toast vermelho
- Espionagem descoberta: alert público dramático no log + animação de penalidade

**Notas de UX:**
- A separação chat/ações de jogo deve ser visual e espacial — nunca sobrepor. O input de chat deve estar em zona claramente distinta dos inputs de dica e palpite.
- Ações irreversíveis (espionar) devem ter confirmação de 1 clique adicional com exibição do risco.
- O timer deve mudar de cor quando < 10s (amarelo) e < 5s (vermelho), com vibração mobile.
- Dicas públicas acumuladas por jogador devem ser exibidas em bolhas, não em lista, para facilitar leitura rápida.
- O log de eventos deve distinguir visualmente: eventos positivos (acerto, troca) vs negativos (penalidade, erro).

**Considerações mobile:**
- Layout em camadas: painel de imagem + ações ocupam a tela toda; placar/log/chat acessíveis via bottom sheet ou tabs na base.
- Bottom navigation mobile: Jogo | Placar | Chat.
- Timer sempre visível no topo, fixo.
- Modais de ação (GUESS, EXCHANGE, SPY) sobem como bottom sheet.

---

### WEB-007 — Modal: Fase de Dica

**Objetivo:** Capturar a dica pública do jogador (uma palavra).

**Descrição sucinta:** Overlay/modal leve que aparece sobre a tela principal durante a HINT_PHASE. Campo single-line com validação de palavra única.

**Principais elementos de interface:**
- Título: "Sua dica para este turno"
- Lembrete da imagem (thumbnail do objeto)
- Input text: uma palavra apenas (validação: sem espaços, sem caracteres especiais)
- Contador de caracteres (sugestão: máx 20 chars)
- Botão "Enviar Dica"
- Timer (replicado do header)

**Ações do usuário:**
- Digitar palavra
- Enviar

**Estados necessários:**
- Validação inline: erro se mais de uma palavra ou caracteres inválidos
- Enviado: modal some + feedback "Dica enviada ✓" na zona de ação
- Timer encerrado sem envio: modal fecha automaticamente + dica vazia registrada

**Notas de UX:** Validação deve bloquear espaços no input em tempo real (não apenas no submit). Exibir exemplos de dicas válidas ("uma palavra") é útil para novatos.

**Considerações mobile:** Bottom sheet em vez de modal centralizado.

---

### WEB-008 — Modal: Fase de Palpite

**Objetivo:** Permitir ao jogador selecionar um alvo e enviar palpite, ou passar.

**Descrição sucinta:** Modal com lista de jogadores disponíveis para adivinhar (excluindo a si mesmo e já adivinhados), campo de texto e ação de envio ou skip.

**Principais elementos de interface:**
- Título: "Fazer palpite"
- Lista/cards de jogadores elegíveis: avatar + apelido + dicas públicas acumuladas
- Ao selecionar jogador: expande para mostrar todas as dicas recebidas dele
- Input: campo de palpite
- Botão "Enviar Palpite" (primary)
- Botão "Passar a vez" (secondary, com confirmação)

**Ações do usuário:**
- Selecionar jogador alvo
- Digitar palpite
- Confirmar ou passar

**Estados necessários:**
- Sem alvo selecionado: botão desabilitado
- Palpite em processamento: loading no botão
- Resultado: modal muda para feedback (correto/incorreto) antes de fechar
- Todos já adivinhados: modal mostra apenas "Passar a vez"

**Notas de UX:** Exibir as dicas públicas do jogador alvo dentro do modal reduz a necessidade de fechar e consultar o painel — crucial para decisão de palpite. O botão "Passar" deve ser menos proeminente para evitar cliques acidentais.

**Considerações mobile:** Cards de jogador em lista vertical rolável.

---

### WEB-009 — Modal: Troca Privada (Solicitante)

**Objetivo:** Solicitar troca privada com um adversário e enviar dica após aceitação.

**Descrição sucinta:** Fluxo em duas etapas: (1) seleção do parceiro e envio de pedido; (2) após aceitação, envio da dica privada (que pode ser verdadeira ou falsa).

**Principais elementos de interface:**
- Etapa 1: Lista de jogadores disponíveis para troca (excluindo já trocados e si mesmo)
- Botão "Solicitar Troca"
- Status: "Aguardando resposta de [Jogador X]..."
- Etapa 2 (após aceite): Input de dica privada + badge "Esta dica é privada — pode ser verdadeira ou falsa" + Botão "Enviar"
- Indicador visual: ícone cadeado para reforçar privacidade

**Ações do usuário:**
- Selecionar parceiro
- Aguardar resposta
- Enviar dica privada

**Estados necessários:**
- Aguardando resposta: spinner + timer reduzido
- Recusado: notificação "Troca recusada por [X]" + opção de solicitar outro
- Expirou sem resposta: notificação + retorno ao estado de ação
- Enviado: confirmação + modal fecha

**Notas de UX:** O aviso de que a dica pode ser falsa deve ser proeminente — é a mecânica de blefe central do jogo. Usar um ícone de "dado" ou "máscara" para reforçar a ambiguidade estratégica.

**Considerações mobile:** Bottom sheet com etapas em scroll.

---

### WEB-010 — Modal: Troca Privada (Receptor)

**Objetivo:** Notificar o jogador de pedido de troca e permitir aceitação/recusa + envio de dica.

**Descrição sucinta:** Notificação urgente que aparece durante a EXCHANGE_PHASE quando outro jogador solicita troca. Timer para resposta.

**Principais elementos de interface:**
- Notificação push (toast ou overlay): "[Jogador X] quer trocar dicas com você!"
- Botões: "Aceitar" / "Recusar"
- Timer de resposta (ex: 20s)
- Após aceitar: mesmo input de dica privada do WEB-009

**Ações do usuário:**
- Aceitar ou recusar
- Se aceitar: enviar dica privada

**Estados necessários:**
- Timer esgotado sem resposta: recusa automática
- Já trocou com este jogador: opção de aceitar desabilitada

**Notas de UX:** A notificação deve interromper levemente a experiência (overlay semi-transparente) mas não bloquear completamente — o jogador pode precisar ver o estado da tela para decidir se aceita ou não.

**Considerações mobile:** Bottom sheet com botões grandes para aceitar/recusar.

---

### WEB-011 — Modal: Espionagem

**Objetivo:** Permitir ao jogador tentar espiar uma troca privada em andamento.

**Descrição sucinta:** Lista de trocas ativas (identificadas pelos participantes, sem conteúdo) com botão de espionagem e exibição clara do risco de penalidade.

**Principais elementos de interface:**
- Título: "Espionar uma troca"
- Lista de trocas em andamento: "[Jogador A] ↔ [Jogador B]"
- Badge de risco: "30% de chance de ser descoberto — penalidade: -10 pts"
- Botão "Espionar" por troca
- Confirmação de 1 passo: "Tem certeza? Risco: 30%"

**Ações do usuário:**
- Selecionar troca para espionar
- Confirmar

**Estados necessários:**
- Sem trocas ativas: estado vazio "Nenhuma troca acontecendo agora"
- Já espiou neste turno: botões desabilitados
- Processando: loading
- Resultado: abre WEB-012

**Notas de UX:** A percepção de risco é central para a decisão. A UI deve deixar o risco conspícuo — não esconder em texto miúdo. O botão "Espionar" deve ser vermelho ou âmbar para indicar ação de risco.

**Considerações mobile:** Bottom sheet com cards de troca e botão grande.

---

### WEB-012 — Modal: Resultado da Espionagem

**Objetivo:** Revelar o resultado da tentativa de espionagem ao jogador.

**Descrição sucinta:** Card de feedback após a tentativa: sucesso (dicas reveladas) ou descoberto (penalidade).

**Principais elementos de interface:**

*Se bem-sucedido:*
- Ícone de sucesso (olho aberto)
- "Você espiou com sucesso!"
- Dica A: "[palavra]" / Dica B: "[palavra]"
- Pontos: "+5 pts (bônus opcional)"

*Se descoberto:*
- Ícone de alerta (sirene)
- "Você foi descoberto!"
- Penalidade: "-10 pts"
- Aviso: "Todos os jogadores foram notificados"

**Ações do usuário:**
- Fechar modal (único CTA: "OK")

**Estados necessários:**
- Sucesso
- Penalidade

**Notas de UX:** Contraste visual forte entre sucesso e penalidade. Penalidade deve parecer impactante sem ser cruel — contexto de jogo. Animação de "quebra" ou "sirene" para descoberta aumenta o drama.

---

### WEB-013 — Painel de Scoring (inline em WEB-006)

**Objetivo:** Exibir os pontos ganhos/perdidos no turno encerrado antes de iniciar o próximo.

**Descrição sucinta:** Overlay ou seção expandida na tela de jogo que aparece automaticamente durante a SCORING_PHASE, com breakdown de pontuação por jogador.

**Principais elementos de interface:**
- Título: "Resultado do Turno X"
- Lista de jogadores com pontos ganhos neste turno (delta)
- Detalhe: origem dos pontos (palpite, ser adivinhado, espionagem)
- Placar acumulado atualizado
- Timer de 5–8s antes de avançar automaticamente
- Botão "Próximo Turno" (host) ou indicador de espera

**Estados necessários:**
- Automático (sem ação do usuário, timer)
- Último turno: transição para resultados finais

**Notas de UX:** O delta de pontos (ex: "+20" em verde, "-10" em vermelho) deve ser animado para criar impacto. Usar animação de counter incrementando os pontos aumenta o engajamento.

---

### WEB-014 — Tela de Resultados Finais

**Objetivo:** Exibir ranking, breakdown da partida e coletar voto de continuidade.

**Descrição sucinta:** Tela pós-jogo com pódio visual, tabela de pontos por turno e votação "Continuar?" com timer.

**Principais elementos de interface:**
- Pódio visual (top 3 com avatares e pontuações)
- Tabela: jogadores × turnos com pontos de cada turno
- Seção de votação: "Jogar mais uma rodada?" — botões "Sim / Não" com barra de progresso de votos
- Timer de votação (ex: 30s)
- Após votação: resultado e ação (reiniciar ou "Partida encerrada")
- Botão "Nova Partida" / "Sair"
- Link para histórico detalhado (WEB-019)

**Ações do usuário:**
- Votar para continuar ou encerrar
- Navegar para nova partida
- Ver histórico

**Estados necessários:**
- Votando: contagem de votos ao vivo
- Maioria quer continuar: animação + "Preparando nova rodada..."
- Maioria quer encerrar: "Partida encerrada — obrigado por jogar!"
- Timer de votação expirado: empate = encerra (premissa)

**Notas de UX:** O pódio é o momento mais memorável do pós-jogo — investir na apresentação visual. A votação deve ser visível a todos em tempo real.

**Considerações mobile:** Pódio simplificado. Tabela em scroll horizontal.

---

### WEB-015 — Regras do Jogo

**Objetivo:** Tutorial e referência para as mecânicas do jogo.

**Descrição sucinta:** Página estática com explicação das fases, sistema de pontuação, mecânica de troca e espionagem, com exemplos visuais.

**Principais elementos de interface:**
- Seções: Conceito | Fases do Turno | Pontuação | Troca Privada | Espionagem | Dicas de Estratégia
- Diagrama visual do ciclo de turnos
- Tabela de pontuação com exemplos numéricos
- Breadcrumb / link voltar para home

**Notas de UX:** A página de regras deve ser acessível durante o lobby para que novatos possam ler enquanto aguardam o início.

---

### WEB-016 / WEB-017 — Telas de Erro

**Objetivo:** Comunicar erros de sessão com contexto e caminho de saída claro.

**Principais elementos de interface:**
- Ícone temático do erro
- Título explicativo
- Descrição breve (ex: "O convite expirou ou é inválido")
- CTA primário: "Criar Nova Partida"
- CTA secundário: "Voltar ao Início"

---

## 7. Componentes Recorrentes

**Header de Jogo**
Aparece em WEB-006 durante toda a partida. Exibe turno atual, fase com badge colorido por fase, timer countdown animado e indicador de conexão (verde/âmbar/vermelho).

**Timer Component**
Aparece em WEB-006 (header), WEB-007, WEB-008, WEB-009, WEB-010, WEB-014. Variações: círculo progressivo (modais), barra horizontal (tela principal), badge numérico (lobby). Muda de cor: verde → amarelo (< 10s) → vermelho (< 5s).

**Player Avatar Card**
Aparece em WEB-005, WEB-006, WEB-008, WEB-009, WEB-011, WEB-013, WEB-014. Composto por: avatar gerado por inicial/cor, apelido, badge de host, indicador de status (online/offline/aguardando). Em WEB-006 inclui dicas acumuladas como chips.

**Phase Badge**
Aparece no header de WEB-006 e em transições. Cores distintas por fase: DICA (azul), PALPITE (verde), TROCA (roxo), ESPIONAGEM (âmbar), PONTUAÇÃO (dourado).

**Event Log Item**
Aparece no painel direito de WEB-006 e em WEB-014/WEB-019. Formato: [timestamp] [ícone de evento] [descrição]. Variações visuais: positivo (verde), negativo (vermelho), neutro (cinza).

**Chat Panel**
Aparece como tab do painel direito em WEB-006. Componentes: histórico com scroll, input com envio por Enter/botão, distinção visual entre mensagens de sistema e de jogadores.

**Scoreboard**
Aparece no painel direito de WEB-006 e em WEB-013/WEB-014. Lista rankeada com destaque para o jogador atual. Animação de incremento ao atualizar.

**Modal / Bottom Sheet Wrapper**
Componente de container para WEB-007 a WEB-012. Desktop: modal centralizado com overlay semi-transparente. Mobile: bottom sheet com drag-to-dismiss.

**Toast de Feedback**
Aparece em qualquer tela para eventos rápidos: dica enviada, palpite correto/errado, penalidade, troca recusada. Duração: 3s. Posição: topo direito (desktop), topo central (mobile).

**Connection Status Banner**
Aparece em WEB-006 quando conexão instável. Overlay não-bloqueante no topo com estado: "Reconectando..." (âmbar) ou "Conexão perdida" (vermelho) + botão "Tentar novamente".

**Hint Chips**
Componente pequeno para exibir dicas públicas acumuladas por jogador. Aparece em WEB-006 (sobre avatares de adversários) e WEB-008 (no modal de palpite). Formato: pill colorido com a palavra da dica e número do turno.

**Secret Object Card**
Componente exclusivo de WEB-006 para exibir a imagem secreta do próprio jogador. Tem borda destacada e label "Seu objeto". Não clicável, apenas visual.

---

## 8. Regras de Navegabilidade

**Como o usuário entra no jogo:**
Via `/create` (host) ou `/join/:code` (convidado). Ambos terminam no lobby antes do início.

**Como volta para telas anteriores:**
Durante lobby: botão "Sair do Lobby" retorna para `/`. Durante o jogo: não há "voltar" — abandono de partida requer confirmação explícita (ver abaixo).

**Como abandona uma partida:**
Botão "Sair" em menu de contexto (não no header principal para evitar cliques acidentais). Modal de confirmação: "Tem certeza? Você perderá sua posição na partida." Ao confirmar: servidor notifica jogadores restantes via evento público.

**Como entra via convite/link:**
`/join/:code` detecta o código automaticamente. Se sessão válida: pede apenas apelido. Se inválida: redireciona para WEB-016.

**Como lida com refresh da página:**
SessionStorage ou URL params mantém o `sessionId`. Ao recarregar em `/game/:sessionId`, o app faz `get_game_state` para restaurar o estado completo. Se sessão ativa e jogador reconhecido: restaura normalmente. Se sessão encerrada: redireciona para WEB-017.

**Como retoma uma partida em andamento:**
Reconexão automática ao voltar para a URL da partida dentro da sessão ativa. Banner de reconexão exibido enquanto estado é carregado.

**Como navega em desktop:**
Layout de painéis fixos sem scroll da página inteira. Navegação via tabs no painel direito (Placar / Eventos / Chat). Modais de ação em overlay. Header fixo com informações de turno/fase.

**Como navega em mobile:**
Bottom navigation com 3 tabs: Jogo | Placar/Log | Chat. A tab "Jogo" ocupa a tela toda com a imagem secreta, dicas dos adversários e zona de ação. Ações emergem como bottom sheets. Timer fixo no topo.

---

## 9. Estados Globais da Experiência

| Estado | Comportamento da UI |
|---|---|
| Sessão não criada | Visitante em `/` — acesso livre a landing e regras |
| No lobby (aguardando) | WEB-005 — atualiza jogadores em tempo real |
| Jogo não iniciado | Lobby com botão Iniciar disponível para host |
| Jogo em andamento | WEB-006 com fase ativa, timer, ações disponíveis |
| Fase específica ativa | Zona de ação muda; inputs de outras fases desabilitados |
| Ação já realizada na fase | Input desabilitado + confirmação visual + aguarda outros |
| Scoring automático | Overlay de pontuação, sem ação do usuário |
| Jogo pausado | *Não previsto no PRD — premissa: sem pausa* |
| Jogo encerrado | WEB-014 com resultados e votação |
| Conexão instável | Banner âmbar não-bloqueante + tentativa de reconexão |
| Offline completo | Banner vermelho + freeze da UI + CTA reconectar |
| Sessão expirada (pós-desconexão) | WEB-017 |
| Convite inválido | WEB-016 |
| Erro de permissão (rota sem sessão) | Redirecionamento para `/` |
| Jogador desconectado (evento recebido) | Toast público + remoção do avatar no jogo |

---

## 10. Lacunas, Premissas e Decisões Pendentes

### Premissas Adotadas

- **Sem autenticação/conta**: entrada apenas com apelido por sessão. Não há persistência entre partidas.
- **Número de jogadores**: mínimo 2, máximo 6 (inferido do PRD; não especificado explicitamente).
- **Modo espectador**: não existe no MVP.
- **Pausa**: não há pausa de jogo. Timer continua mesmo com jogadores ausentes.
- **Empate na votação de continuar**: empate resulta em encerramento da partida.
- **Timer de votação expirado sem todos votarem**: maioria dos votos recebidos decide; sem votos = encerra.
- **Imagem exibida como miniatura** durante fase de troca/espionagem: jogador não vê a imagem do adversário — apenas as dicas públicas e privadas.
- **Dica vazia automática**: quem não enviar dica no tempo recebe string vazia sem penalidade.
- **Arbitragem automática** (Solução 2 do PRD): sem validação manual pelo dono do objeto, pois complicaria o fluxo de UI.
- **Probabilidade de espionagem fixa**: 30% padrão; configuração avançada fora do MVP.
- **Chat sem moderação**: qualquer texto é aceito; sem filtros no MVP.
- **Imagens fornecidas pelo servidor**: não há upload de imagens pelo usuário.
- **Língua da interface**: português brasileiro.

### Dúvidas em Aberto

1. **Quantos jogadores são suportados?** O PRD menciona 2–N sem especificar máximo. O layout do painel de avatares precisa dessa informação para definir se usa scroll ou grid fixo.
2. **A imagem secreta é transmitida como URL ou base64?** Impacta latência de carregamento e tratamento de erro de imagem.
3. **Palpites são por rodada ou cumulativos?** O jogador pode palpitar sobre o mesmo adversário em turnos diferentes?
4. **O bônus de espionagem bem-sucedida (+5 pts) é obrigatório ou opcional?** O PRD marca como "opcional" — precisa de decisão.
5. **Timer configurável por fase ou único para todas?** O PRD menciona 30–60s mas não especifica se o host configura isso.
6. **O que acontece se um jogador abandona no meio do jogo?** A partida continua? O objeto do jogador desconectado segue sendo um alvo de palpites?
7. **Suporte a múltiplas sessões simultâneas no servidor?** Relevante para UX de "criar partida enquanto outra está ativa".
8. **Histórico de partida permanente?** O PRD não menciona. Sem persistência, WEB-019 só é viável durante a sessão ativa.

### Riscos de UX

- **Confusão entre chat e ações de jogo**: é o risco mais alto da aplicação. A separação visual e espacial precisa ser radical — cores, zonas, labels explícitos.
- **Sobrecarga cognitiva na tela principal**: o jogador precisa monitorar sua imagem, dicas de 5 adversários, placar, log e fase simultaneamente. Layout em painéis fixos e hierarquia visual forte são críticos.
- **Timer ansioso**: timer visível cria pressão — usuários iniciantes podem não conseguir pensar no palpite a tempo. Considerar timer configurável como melhoria pós-MVP.
- **Mecânica de espionagem opaca**: se o jogador não entende o risco claramente, pode espionar sem querer. A UI deve tornar o risco extremamente visível.
- **Dica privada falsa**: a mecânica de "dica pode ser mentira" é contra-intuitiva. Sem reforço visual constante ("esta dica pode ser falsa!"), jogadores podem confiar cegamente.
- **Desconexão durante fase crítica**: se um jogador desconecta durante a EXCHANGE_PHASE, o parceiro de troca fica em estado indefinido. A UI deve informar: "Troca cancelada — [X] se desconectou."
- **Mobile com muitas informações**: a tela de jogo é muito densa para mobile. O modelo de tabs/bottom sheet precisa de validação com usuários reais.

---

## 11. Recomendação de MVP de Telas

### Protótipo Essencial
*Telas mínimas para validar o fluxo completo do jogo de ponta a ponta.*

| ID | Tela | Justificativa |
|---|---|---|
| WEB-001 | Landing Page | Ponto de entrada obrigatório |
| WEB-002 | Criar Partida | Fluxo do host |
| WEB-004 | Entrada via Convite | Fluxo do convidado (mais comum) |
| WEB-005 | Lobby | Pré-jogo e sincronização |
| WEB-006 | Tela Principal de Jogo | Core de toda a experiência |
| WEB-007 | Modal: Fase de Dica | Mecânica principal |
| WEB-008 | Modal: Fase de Palpite | Mecânica principal |
| WEB-009/010 | Modais: Troca Privada | Diferencial do jogo |
| WEB-011/012 | Modais: Espionagem | Diferencial do jogo |
| WEB-013 | Painel de Scoring | Feedback de resultado |
| WEB-014 | Resultados Finais | Fechamento do loop |

### Protótipo Ideal
*Adicionar ao essencial para representar melhor a experiência completa.*

| ID | Tela | Justificativa |
|---|---|---|
| WEB-003 | Entrar na Partida (sem link) | Fluxo alternativo relevante |
| WEB-015 | Regras do Jogo | Reduz curva de aprendizado |
| WEB-016/017 | Telas de Erro | Experiência de borda importante |

### Pós-MVP

| ID | Tela | Justificativa |
|---|---|---|
| WEB-018 | Tela 404 | Baixo impacto no fluxo principal |
| WEB-019 | Histórico de Partida | Complementar; exige persistência de dados |

---

*Documento produzido com base no PRD "Jogo Multijogador de Adivinhação via RPC/RMI" — CC5SDT / UTFPR 2026-1.*
*Versão: 1.0 | Autor: Product Design Staff+ | Data: Maio 2026*
