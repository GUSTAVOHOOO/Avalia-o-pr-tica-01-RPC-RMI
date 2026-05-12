# Jogo de Adivinhação Multijogador — RPC/Pyro5

## What This Is

Jogo multijogador de adivinhação em tempo real construído como trabalho acadêmico para a disciplina CC5SDT (Sistemas Distribuídos e Tecnologias) na UTFPR — Campus Santa Helena, semestre 2026-1. Cada jogador recebe uma imagem secreta de um objeto e, a cada turno, envia uma dica de uma palavra para todos. Os outros jogadores tentam adivinhar os objetos, com mecânicas de troca privada de dicas, espionagem com risco de penalidade e sistema de pontuação automático. Interface web (React/HTML) no front-end e comunicação exclusivamente via Pyro5 RPC no back-end.

## Context

- **Disciplina:** CC5SDT — Sistemas Distribuídos e Tecnologias
- **Instituição:** UTFPR — Campus Santa Helena
- **Professor:** Rafael Keller Tesser
- **Semestre:** 2026-1
- **Peso da avaliação:** 0,3 (3 pontos na nota final)
- **Equipe:** 2 integrantes
- **Prazo:** 2026-1 (data exata a confirmar)
- **Stack backend:** Python 3.8+ + Pyro5 (RPC com callbacks)
- **Stack frontend:** Web app (HTML/CSS/JS ou framework leve) com WebSocket/HTTP bridge para Pyro5
- **Restrição crítica:** Toda comunicação entre processos deve ser exclusivamente via RPC/Pyro5 (proibido sockets diretos)

## Core Value

Demonstrar arquitetura distribuída event-driven funcional: servidor Pyro5 com callbacks push para todos os clientes, mecânicas de jogo completas (dicas, palpites, trocas privadas, espionagem) e interface web reagindo em tempo real — tudo funcionando com 2–4 jogadores simultâneos.

## Problem

Trabalho acadêmico avaliado que exige demonstração prática de sistemas distribuídos com RPC. O desafio técnico central é implementar push de eventos (server → client callbacks) via Pyro5 enquanto se serve uma interface web no browser — os browsers não podem chamar Pyro5 diretamente, então é necessário uma camada de bridge WebSocket/HTTP.

## Who It's For

- **Professores/Avaliadores:** validar uso correto de RPC, arquitetura event-driven, thread-safety e mecânicas do jogo implementadas
- **Jogadores (2–6):** experiência de jogo fluida com turnos claros, feedback em tempo real, placar visível

## Architecture Decision

**Bridge WebSocket:** O servidor Pyro5 expõe os serviços de jogo (GameServer). Uma camada de bridge (Flask-SocketIO ou similar) converte chamadas WebSocket do browser em chamadas Pyro5 e repassa os callbacks Pyro5 como eventos WebSocket para o cliente web. Isso satisfaz o requisito de "comunicação exclusivamente via RPC" no back-end enquanto permite interface web.

```
Browser ←→ WebSocket/HTTP Bridge ←→ Pyro5 Daemon (GameServer)
                                         ↕ callbacks
                               [EventBroadcaster → Bridge → Browser]
```

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Core RPC / Backend**
- [ ] Servidor Pyro5 com GameServer exposto via RPC
- [ ] Sistema de registro de callbacks de clientes (register_callback)
- [ ] EventBroadcaster via Pyro5 callbacks (push, não polling)
- [ ] Thread-safety com RLock no servidor
- [ ] Name Server Pyro5 para descoberta de serviços
- [ ] Bridge WebSocket↔Pyro5 (Flask-SocketIO ou equivalente)

**Mecânicas de Jogo**
- [ ] Jogador entra/sai do jogo (join_game / leave_game)
- [ ] Distribuição de imagens de objetos por rodada
- [ ] Sistema de turnos com fases: HINT → GUESS → EXCHANGE → SPY → SCORING
- [ ] Timer por fase (30–60s) com transição automática
- [ ] Envio de dica pública (uma palavra) por turno
- [ ] Envio de palpite com arbitragem (WordNet sinonimos + similaridade)
- [ ] Troca privada de dicas entre dois jogadores (aceitação mútua)
- [ ] Notificação pública de troca sem revelar conteúdo
- [ ] Espionagem com 30% de chance de descoberta e penalidade de -10pts
- [ ] Sistema de pontuação automático (RF-20 a RF-23 do PRD)
- [ ] Chat em tempo real separado das ações de jogo
- [ ] Votação para continuar ou encerrar após último turno

**Interface Web**
- [ ] Landing page com CTAs criar/entrar
- [ ] Tela criar partida (apelido + número de turnos)
- [ ] Lobby com lista de jogadores e link de convite
- [ ] Tela principal de jogo com painéis: imagem secreta, dicas, ações, placar, chat
- [ ] Modais por fase (dica, palpite, troca solicitante/receptor, espionagem, resultado)
- [ ] Tela de resultados finais com pódio e votação
- [ ] Timer visual com mudança de cor (verde → amarelo < 10s → vermelho < 5s)
- [ ] Separação visual clara: chat vs ações de jogo (risco UX mais alto do projeto)
- [ ] Reconexão automática com restauração de estado

**Relatório Técnico (requisito acadêmico)**
- [ ] Introdução ao Pyro5 com justificativa de escolha
- [ ] Descrição do desenvolvimento com capturas de tela e trechos de código
- [ ] Instruções de instalação e uso
- [ ] Diagramas de sequência mostrando comunicação RPC

### Out of Scope

- Autenticação/contas persistentes — apelido por sessão apenas
- Modo espectador — apenas jogadores ativos
- Pausa de jogo — timer não para
- Upload de imagens pelos usuários — imagens fornecidas pelo servidor
- gRPC, RPyC ou Java RMI — Pyro5 confirmado
- Sockets diretos em qualquer camada de comunicação entre processos
- Persistência entre partidas (sem banco de dados)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Pyro5 como framework RPC | Melhor custo-benefício para Python: callbacks nativos permitem push event-driven, API simples, Name Server integrado | Confirmado |
| Interface web em vez de CLI | UI.md especifica web app com rotas, responsividade mobile, componentes visuais | Confirmado |
| Bridge WebSocket↔Pyro5 | Browsers não podem chamar Pyro5 diretamente; bridge satisfaz requisito RPC no back-end | Confirmado |
| Arbitragem automática (Solução 2) | Sem validação manual pelo dono — mais justo e não bloqueia o fluxo de UI | Confirmado |
| Probabilidade de espionagem 30% | Valor do PRD, configurável mas fixo no MVP | — Pending |
| Dica vazia automática | Quem não enviar dica no timer recebe string vazia sem penalidade | — Pending |

## Success Looks Like

1. Servidor Pyro5 rodando com callbacks push funcionais
2. 2–4 clientes web conectados simultaneamente recebendo eventos em tempo real
3. Turno completo executável: HINT → GUESS → EXCHANGE → SPY → SCORING
4. Pontuação calculada e transmitida automaticamente ao fim de cada turno
5. Chat funcionando separado das ações de jogo
6. Testes com 3 instâncias simultâneas sem race conditions

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-12 after initialization*
