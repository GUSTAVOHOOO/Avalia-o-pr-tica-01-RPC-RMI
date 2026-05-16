# Phase 8: UI Polish + Technical Report - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-16
**Phase:** 8-ui-polish-technical-report
**Areas discussed:** Relatório: formato e ferramentas, Escopo real do polish de UI, Animações e transições, Banner de reconexão (UI-09)

---

## Relatório: formato e ferramentas

| Option | Description | Selected |
|--------|-------------|----------|
| PDF via LaTeX ou pandoc | Arquivo compilado, profissional, versionável | ✓ |
| Google Docs / Word | Colaborativo mas fora do git | |
| Markdown no repositório | Simples mas formatação limitada | |
| Não sei / deixa Claude decidir | Claude escolhe | |

**Formato PDF:** Markdown + pandoc (recomendado) ✓

| Option | Description | Selected |
|--------|-------------|----------|
| Markdown + pandoc | Zero setup LaTeX manual, versionável | ✓ |
| LaTeX puro | Controle total, padrão ABNT | |

**Diagramas:**

| Option | Description | Selected |
|--------|-------------|----------|
| Mermaid | Texto no Markdown, sem ferramenta extra | ✓ |
| draw.io / diagrams.net | Visual, exporta PNG, binário | |
| PlantUML | Texto, requer JVM | |
| ASCII art | Já existe no CLAUDE.md | |

**Norma de formatação:**

| Option | Description | Selected |
|--------|-------------|----------|
| Livre (sem norma exigida) | Formato profissional sem ABNT/IEEE | ✓ |
| ABNT | Capa, sumário, referências NBR | |
| Formato do professor | Critérios específicos | |

**Páginas:**

| Option | Description | Selected |
|--------|-------------|----------|
| Curto (5–10 páginas) | Denso, foco em diagramas + screenshots | ✓ |
| Médio (10–20 páginas) | Cobertura completa com narrativa | |
| Sem limite | Claude decide | |

**Idioma:**

| Option | Description | Selected |
|--------|-------------|----------|
| Português | UTFPR, professor brasileiro | ✓ |
| Inglês | Professor pediu em inglês | |

**Notes:** Usuário optou por formato objetivo e denso. O docker-compose do quick task 260514-iib já facilita rodar o jogo para tirar screenshots.

---

## Escopo real do polish de UI

**Estado atual dos modais de fase:**

| Option | Description | Selected |
|--------|-------------|----------|
| Não existem — criar do zero | GameScreen sem modais | |
| Existem mas são básicos (inputs inline) | Ações funcionam via inputs inline | ✓ |
| Já são modais completos | HINT/GUESS/EXCHANGE/SPY com modais | |

**Timer ColorDisplay (UI-05):**

| Option | Description | Selected |
|--------|-------------|----------|
| Não, só número sem cor | CountdownDisplay sem lógica de cor | ✓ |
| Parcialmente — 2 estados | Falta um dos três estados | |
| Já funciona com 3 cores | Verde/amarelo/vermelho implementados | |

**Modais EXCHANGE e SPY:**

| Option | Description | Selected |
|--------|-------------|----------|
| Modais completos para EXCHANGE e SPY | Cada fase com overlay/modal com papéis | ✓ |
| Inline para EXCHANGE/SPY, modal só para HINT/GUESS | Cobertura parcial UI-06 | |
| Claude decide por fase | Claude avalia caso a caso | |

**Escopo de telas:**

| Option | Description | Selected |
|--------|-------------|----------|
| Foco no GameScreen e PostGame | Landing/Lobby ok | |
| Todas precisam de polish | Polish completo em todas as telas | ✓ |
| Só a Landing precisa de atenção | Landing é primeira impressão | |

**Nível de polish:**

| Option | Description | Selected |
|--------|-------------|----------|
| Profissional/produtivo — parece app real | Hover states, tipografia, cores | ✓ |
| Funcional e limpo — sem bugs visuais | Demonstração das mecânicas | |

**Chips de dicas públicas (UI-04):**

| Option | Description | Selected |
|--------|-------------|----------|
| Lista/texto simples, precisam virar chips | Criar componente chip | |
| Já são chips/badges razoáveis | Só refinamento visual | ✓ |
| Não exibem dicas dos outros ainda | Não implementado | |

**Notes:** O GameScreen (552 linhas) é o foco principal. Inputs inline viram modais para todas as 4 fases. Chips de dicas já existem — só refinamento.

---

## Animações e transições

**Delta de pontos (UI-07):**

| Option | Description | Selected |
|--------|-------------|----------|
| Contador animado simples | Número conta de 0 ao valor em ~1s | |
| CSS keyframes elaborados | Slide/fade, pulso, cor por positivo/negativo | ✓ |
| Só exibir delta sem animação | Estático, não cobre UI-07 | |

**Outras transições:**

| Option | Description | Selected |
|--------|-------------|----------|
| Transições de fase animadas também | Modal entra com slide/fade na troca de fase | ✓ |
| Só animação de pontos | CSS transitions simples no resto | |
| Claude decide | Animar onde agrega valor | |

**Notes:** Usuário quer experiência visual impactante. Keyframes elaborados para o delta + transições de fase. CSS puro (sem biblioteca extra) é preferível se disponível.

---

## Banner de reconexão (UI-09)

**Posição:**

| Option | Description | Selected |
|--------|-------------|----------|
| Faixa superior fixa | Sticky top bar, não bloqueia conteúdo | ✓ |
| Toast no canto inferior direito | Flutuante, pode ser ignorado | |
| Overlay semi-transparente | Mais dramático | |

**Threshold âmbar → vermelho:**

| Option | Description | Selected |
|--------|-------------|----------|
| 3 segundos | Rápido mas não hiperreativo | ✓ |
| 5 segundos | Mais tolerante | |
| Claude decide | Baseado no grace period de 5s do bridge | |

**Escopo de telas:**

| Option | Description | Selected |
|--------|-------------|----------|
| Apenas no GameScreen | Onde a desconexão é crítica | ✓ |
| Em todas as telas com socket ativo | Lobby e PostGame também | |

**Notes:** Alinhado com D-01 da Phase 7 (grace period de ~5s no bridge). Banner âmbar aparece ao desconectar, muda para vermelho em 3s, desaparece automaticamente ao reconectar.

---

## Claude's Discretion

- Biblioteca CSS para animações (CSS puro vs. framer-motion) — avaliar o que está instalado
- Duração exata das transições de fase (200ms–400ms)
- Estrutura de arquivos do relatório (docs/ vs. report/)
- Template pandoc para o PDF (default, eisvogel, custom)

## Deferred Ideas

- Modo espectador — v2, fora de escopo
- Histórico de partida persistente — v2, fora de escopo
- Animações com framer-motion — CSS puro suficiente para escopo acadêmico
- Versão em inglês do relatório — professor brasileiro, português suficiente
