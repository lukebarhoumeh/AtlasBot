# Changelog

## Unreleased
- Profit-first exits with ATR TP/SL
- ATR TP/SL exits with timeout in IntradayTrader
- Prometheus exit counters
- Paper backend retry with Fill dataclass
- Heartbeat watchdog and ledger gzip
- Tunable edge threshold and conflict filter
- Breakout signal with adaptive trade-count curb
- Kill switch on 5% equity drawdown and trade log review utility
- Removed vendored dependency stubs; use real wheels
- Maker vs taker tracking and conflict debounce
- Circuit breaker and feed watchdog safeguards
- Thread-safe ledger with stress test
- Slim Dockerfile and CI cache
- Fee updater thread activated automatically
- Ledger snapshots written every minute
- Maker fill ratio metric exposed
- Configurable max hold time via MAX_HOLD_MIN
- Decision engine scales edge by signal strength
- Market-data readiness bypassed in CI with retry logic and longer timeout
- Env-driven loop cycle, edge filter, symbols, notional & cash
- On-screen fills log info-level; end-run P&L summary
- Maker limit orders fall back to taker after 5 s with debug log
- Per-run CSV ledger
- EXECUTION_MODE env to toggle maker vs taker
- Windows-compatible run logger via safe fsync

## 0.4.0 - 2025-05-30
- Sprint 5 features and bug fixes
- Diagnostics module summarising env + last rejects
