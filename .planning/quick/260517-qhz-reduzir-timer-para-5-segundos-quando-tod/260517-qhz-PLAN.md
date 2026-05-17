---
quick_id: 260517-qhz
status: complete
created: 2026-05-17
---

# Quick Task: Reduzir timer para 5 segundos quando todos concluirem a fase

## Assumptions

- Fases com respostas obrigatorias devem manter um countdown visivel curto, nao avancar instantaneamente.
- O tempo curto deve ser centralizado em `config.py`.
- O frontend deve atualizar o timer sem reiniciar o estado da fase atual.

## Plan

1. Add a `TurnMachine` path to shorten the active timer and broadcast the new countdown.
2. Replace immediate completion advances in hint, guess, exchange, and spy actions with timer shortening.
3. Forward the new event through the bridge and update the React countdown.
4. Update focused tests to expect a short grace timer before phase transition.

## Verification

- `python -m py_compile config.py server\turn_machine.py server\game_server.py bridge\bridge.py`
- `python -m pytest tests\test_turn_machine.py tests\test_turn_state.py::test_all_hints_shortens_timer_then_advances tests\test_turn_state.py::test_all_guesses_shortens_timer_then_advances tests\test_exchange.py::test_exchange_phase_shortens_timer_when_no_pair_available tests\test_exchange.py::test_spy_phase_skipped_when_no_eligible_spy tests\test_exchange.py::test_spy_phase_shortens_timer_after_all_eligible_attempt -q`
- `python -m pytest tests\test_exchange.py::test_spy_phase_entered_when_exchange_exists -q`
- `npm run build`
