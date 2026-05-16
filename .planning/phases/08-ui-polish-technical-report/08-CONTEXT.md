# Phase 8: UI Polish + Technical Report - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver two things: (1) a polished, production-quality web interface across all screens (Landing, CreateGame, Lobby, GameScreen, PostGame) that covers UI-01 through UI-10 — including phase modals, timer color states, animated scoring, reconnection banner, and radical chat/action separation; and (2) a complete academic technical report in Portuguese, written in Markdown compiled to PDF via pandoc, with Mermaid diagrams, covering REPORT-01 through REPORT-04.

Requirements in scope: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, UI-09, UI-10, REPORT-01, REPORT-02, REPORT-03, REPORT-04

</domain>

<decisions>
## Implementation Decisions

### Relatório Técnico (REPORT)

- **D-01:** Formato do relatório: **Markdown + pandoc → PDF**. O relatório é escrito em Markdown simples, compilado para PDF via pandoc. Arquivo versionado no repositório (ex: `docs/relatorio.md` + Makefile/script de compilação).
- **D-02:** Ferramenta para diagramas: **Mermaid**. Diagramas de sequência RPC e arquitetura de componentes em blocos Mermaid dentro do Markdown. Compilados junto com o pandoc. Sem dependência externa de editor gráfico.
- **D-03:** Idioma: **Português**. Todo o relatório em português (disciplina na UTFPR).
- **D-04:** Formatação: **Formato livre**, sem norma ABNT/IEEE. Template pandoc padrão com estilos profissionais.
- **D-05:** Extensão alvo: **5–10 páginas**. Denso e objetivo: priorizar diagramas, trechos de código e capturas de tela sobre texto narrativo.
- **D-06:** Seções obrigatórias (REPORT-01 a REPORT-04):
  - Introdução ao Pyro5 com comparativo de tecnologias RPC e justificativa da escolha
  - Arquitetura do sistema: diagrama de componentes (3 processos) + ≥2 diagramas de sequência (registro de callback + entrega de evento de jogo)
  - Capturas de tela da aplicação funcionando + trechos de código relevantes
  - Instruções completas de instalação e execução

### UI Polish — Escopo Geral

- **D-07:** Todas as telas precisam de polish: Landing, CreateGame, JoinByCode, Lobby, GameScreen, PostGame. Nível de qualidade: **profissional/produtivo** — visual consistente, hover states, tipografia hierarquizada, cores cuidadas. A interface deve parecer uma app real para impressionar na avaliação.
- **D-08:** Chips de dicas públicas (UI-04) já estão razoáveis — refinamento visual apenas, sem refatoração.

### Modais por Fase (UI-06)

- **D-09:** Atualmente as ações de fase são **inputs inline** no GameScreen. Todos os modais/overlays de fase devem ser **criados**: HINT, GUESS, EXCHANGE (papéis solicitante + receptor), SPY (lista de trocas ativas + confirmação de risco). Nenhuma fase pode usar input inline — todas ganham modal/overlay dedicado.
- **D-10:** EXCHANGE tem dois papéis distintos: solicitante vê o status da solicitação; receptor vê o pedido com opções de aceitar/recusar. O modal deve renderizar diferente para cada papel.
- **D-11:** SPY modal exibe lista de trocas ativas (dos outros jogadores), permite selecionar uma e confirma o risco de penalidade antes de executar.

### Timer com 3 Cores (UI-05)

- **D-12:** `CountdownDisplay.tsx` atualmente exibe o número sem mudar cor. Adicionar lógica de cor:
  - `> 10s` → verde
  - `≤ 10s` → amarelo/âmbar
  - `≤ 5s` → vermelho
  - Transição suave via CSS transition na cor.

### Animações e Transições

- **D-13:** Delta de pontos ao fim do turno (UI-07): **CSS keyframes elaborados**. O delta (ex: `+20`) aparece com efeito visual: slide up, pulso, cor verde para positivo / vermelho para negativo. Animação dura ~1.5s e remove o elemento após.
- **D-14:** Transições de fase: quando a fase muda (ex: HINT → GUESS), o modal/painel de ação entra com **slide ou fade** (CSS transition). Dá ritmo visual ao jogo.

### Banner de Reconexão (UI-09)

- **D-15:** Layout: **faixa superior fixa** (top sticky bar), não bloqueia o conteúdo abaixo.
- **D-16:** Estados:
  - Ao perder conexão: **âmbar imediato** ("Reconectando...")
  - Após **3 segundos** offline: **vermelho** ("Offline")
  - Ao reconectar: banner desaparece automaticamente
- **D-17:** Escopo: **apenas no GameScreen**. Lobby e PostGame não mostram o banner — o GameScreen é onde a desconexão causa perda crítica de estado.

### Claude's Discretion

- Biblioteca CSS para animações (CSS puro com keyframes vs. framer-motion) — Claude decide com base no que está instalado no projeto.
- Duração exata das transições de fase (200ms–400ms) — Claude decide o que parece mais fluido.
- Estrutura de arquivos para o relatório (`docs/relatorio.md`, `report/`, etc.) — Claude decide organização mais limpa.
- Template pandoc a usar (default, eisvogel, custom) — Claude decide o que produz melhor PDF sem dependência externa.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §UI-01 a UI-10 — Especificações completas de interface web
- `.planning/REQUIREMENTS.md` §REPORT-01 a REPORT-04 — Conteúdo obrigatório do relatório técnico
- `.planning/ROADMAP.md` §Phase 8 — 5 success criteria que devem ser TRUE para completar a fase

### Architecture
- `.planning/PROJECT.md` §Key Decisions — Decisões bloqueadas (threading, proxies, broadcast)
- `CLAUDE.md` §Technology Stack — Stack completo com justificativas (fonte para o relatório)
- `CLAUDE.md` §Key Pyro5 Patterns — Padrões 1–4 (exemplos de código para o relatório)

### Prior Phase Context
- `.planning/phases/07-reconnection-end-of-game/07-CONTEXT.md` — D-04 (separação visual chat/ação já definida com ChatPanel), D-01 a D-03 (lógica de reconexão implementada no bridge), UI-09 deferred para esta fase
- `.planning/phases/04-core-turn-loop/04-CONTEXT.md` — shape do get_player_view, estrutura de pontuação

### Existing Frontend (ler antes de modificar)
- `frontend/src/pages/GameScreen.tsx` — 552 linhas, ações de fase como inputs inline; D-09 exige migrar para modais
- `frontend/src/pages/PostGame.tsx` — 339 linhas, lógica de votação e pódio
- `frontend/src/pages/Landing.tsx` — tela de entrada atual
- `frontend/src/components/CountdownDisplay.tsx` — componente de timer sem cor; D-12 adiciona 3 estados
- `frontend/src/components/ChatPanel.tsx` + `frontend/src/components/ChatPanel.css` — separação visual chat/ação já implementada
- `frontend/src/pages/GameScreen.css` — estilos atuais do game screen

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/CountdownDisplay.tsx` — já recebe `remainingSeconds` prop; apenas adicionar lógica de cor (D-12)
- `frontend/src/components/PhaseBadge.tsx` — badge de fase existente; reutilizar no header do modal de cada fase
- `frontend/src/components/ChatPanel.tsx` — separação visual chat/ação já implementada em Phase 7; não modificar layout, apenas polish visual
- `PostGame.tsx:voteBarColor()` — padrão de cor por tempo já implementado para a barra de votação; reutilizar lógica para CountdownDisplay

### Established Patterns
- Tailwind CSS via CDN (play) — todo o styling usa classes Tailwind + CSS customizado nos arquivos `.css` por página
- Dark theme com `#0f1117` de fundo — todos os componentes devem respeitar o tema escuro
- Socket.IO events em `useEffect` com cleanup — padrão estabelecido em GameScreen.tsx e PostGame.tsx
- `socket.ts` — módulo singleton de conexão; banner de reconexão deve ouvir `socket.on('connect')` / `socket.on('disconnect')`

### Integration Points
- `GameScreen.tsx` — ponto central de modificação: adicionar modais por fase, timer colorido, banner de reconexão, transições de fase
- `CountdownDisplay.tsx` — adicionar prop ou derivar cor dos `remainingSeconds` existentes
- `frontend/src/index.css` ou `GameScreen.css` — adicionar keyframes CSS para animação de delta de pontos
- Novo arquivo `docs/relatorio.md` (ou `report/relatorio.md`) — relatório técnico; adicionar script de compilação pandoc

</code_context>

<specifics>
## Specific Ideas

- Delta de pontos: elemento aparece com `@keyframes slideUpFade` — desliza para cima e desaparece. Cor verde (`#22c55e`) para positivo, vermelho (`#ef4444`) para negativo, cinza para zero.
- Transição de fase: modal entra com `@keyframes slideInFromBottom` ou `fadeIn` ao receber `PHASE_CHANGED` event.
- Banner de reconexão: componente `<ReconnectionBanner>` em `GameScreen.tsx` que ouve `socket.on('connect')` / `socket.on('disconnect')` e usa `useRef` para o timer de 3s (âmbar → vermelho).
- Relatório: capturas de tela tiradas com o jogo rodando em 3 terminais (setup de demo já existe via docker-compose do quick task `260514-iib`).
- Relatório: comparativo de tecnologias RPC na introdução deve mencionar Java RMI, gRPC, RPyC e justificar Pyro5 com os critérios da disciplina.

</specifics>

<deferred>
## Deferred Ideas

- Modo espectador — v2, deferred em init
- Histórico de partida persistente — v2, deferred em init
- Internacionalização (suporte a inglês no relatório) — professor é brasileiro, português suficiente
- Animações mais elaboradas com framer-motion — CSS puro é suficiente para o escopo acadêmico

</deferred>

---

*Phase: 8-ui-polish-technical-report*
*Context gathered: 2026-05-16*
