# TradingLab — fase 1

Laboratório de coleta de dados e relatórios de viés de mercado, independente do Hermes.

## Escopo
- Cripto: MEXC **spot** (BTCUSDT, ETHUSDT, SOLUSDT), candles fechados em 15m, 1h e 4h.
- Outros mercados previstos: EUR/USD, GBP/USD, USD/JPY, XAU/USD, XAG/USD e WTI. **Fontes ainda não validadas; sem dados automáticos desses mercados.**
- Relatórios planejados: 07:00, 13:00 e 19:00 no fuso America/Sao_Paulo.
- **Sem ordens, sem execução automática, sem backtesting nesta fase.**

## Coleta
Execute `python src/mexc_public.py --output data/crypto/latest.json`.
Usa somente a API pública da MEXC, sem credenciais. Se qualquer consulta falhar, encerra com erro e não substitui o snapshot por dados incompletos.

## Agendamento
O workflow `.github/workflows/crypto-snapshot.yml` é executado às 06:50, 12:50 e 18:50 no horário de Brasília (09:50, 15:50, 21:50 UTC) e pode ser acionado manualmente. Horários de GitHub Actions podem atrasar. A conta GitHub precisa permitir Actions e escrita pelo GITHUB_TOKEN.

## Transparência
`data/crypto/latest.json` representa dados de **spot MEXC**, não futuros. Não presume integração automática com tarefas do ChatGPT. Cada relatório deve informar fontes, horários e indisponibilidades.
