---
status: diagnosed
phase: 06-synonym-arbitration
source: 06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-03-SUMMARY.md
started: 2026-05-15T17:30:00Z
updated: 2026-05-15T18:00:00Z
---

## Current Test

## Current Test

[testing complete]

## Tests

### 1. Nomes de objetos em português
expected: Inicie uma partida com 2+ jogadores. O objeto secreto atribuído a cada jogador deve aparecer em português (maçã, bicicleta, cadeira, relógio, violão, chapéu, laptop, guarda-chuva, livro, xícara, sapato, árvore) — não em inglês.
result: pass

### 2. Palpite exato aceito
expected: Em uma partida em andamento, envie um palpite com a palavra exata do objeto alvo (ex: se o alvo é "maçã", envie "maçã" ou "MAÇÃ"). O servidor deve retornar is_correct=True e o jogador deve ganhar pontos.
result: pass

### 3. Sinônimo aceito (arbitração Wu-Palmer)
expected: Em uma partida, envie um palpite com um sinônimo do objeto alvo reconhecido pelo WordNet em português (ex: "copo" quando o alvo é "xícara"). O servidor deve aceitar como correto — o palpite é um sinônimo com similaridade Wu-Palmer acima de 0.7.
result: issue
reported: "testei 'copo' para xícara e deu como errado | testei 'boina' para chapéu e também deu como errado"
severity: major

### 4. Palpite incorreto rejeitado
expected: Envie um palpite sem relação semântica com o objeto alvo (ex: "cachorro" quando o alvo é "maçã"). O servidor deve retornar is_correct=False e o palpite não deve dar pontos.
result: pass

### 5. GUESS_RESULT com matched_word e match_type
expected: Ao enviar qualquer palpite, o broadcast GUESS_RESULT recebido pelos clientes deve conter os campos matched_word (a palavra canônica do alvo ou null) e match_type (exact, synonym ou fallback). Você pode verificar isso nos logs do servidor/bridge ou inspecionando os eventos recebidos no console do navegador.
result: pass
notes: "Verificado por inspeção de código: broadcast_data inclui matched_word (linha 600) e match_type (linha 601) em game_server.py; bridge emite o dict completo (linha 133 em bridge.py). Log do bridge omite esses campos por design mas o evento guess_result chega ao browser com eles."

### 6. validate_manifest.py reporta 12 palavras válidas
expected: Execute `python validate_manifest.py` na raiz do projeto. O script deve imprimir as 12 palavras portuguesas com cobertura omw-1.4 (maçã, bicicleta, etc.) e sair com código 0 (sem erros).
result: pass

## Summary

total: 6
passed: 5
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Palpite com sinônimo reconhecido pelo WordNet PT (ex: 'copo' para 'xícara') deve ser aceito como correto"
  status: failed
  reason: "User reported: testei 'copo' para xícara e deu como errado | testei 'boina' para chapéu e também deu como errado"
  severity: major
  test: 3
  root_cause: "_assign_images_for_turn() está wired apenas em on_round_start; a partir do turno 2, ROUND_START é pulado (D-06) então _assign_images_for_turn() nunca é chamado; _consume_image_assignments() retorna {} no HINT_PHASE do turno 2+; TurnState.image_assignments = {} → expected = '' para qualquer target_player_id → arbitrate(guess, '', threshold) sempre retorna False; o arbitrate() em si está correto — o bug está no ciclo de assignamento de turnos"
  artifacts:
    - path: "server/game_server.py"
      issue: "on_round_start callback (linha 461) é a única origem de _assign_images_for_turn(); não é chamado nos turnos 2+"
    - path: "server/turn_machine.py"
      issue: "_compute_next() retorna 'HINT_PHASE' direto de TURN_END sem passar por ROUND_START (linha 237)"
  missing:
    - "Chamar _assign_images_for_turn() também no início de cada HINT_PHASE (turnos 2+) — mover o assign para on_hint_phase_start ou adicionar um segundo hook"
  debug_session: ".planning/debug/synonym-rejection-live-game.md"
