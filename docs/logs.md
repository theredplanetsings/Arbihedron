# Logs Directory

This directory contains runtime logs for Arbihedron.

Logs are automatically rotated daily and retained for 7 days.

## Log Levels

- **DEBUG**: Detailed execution information
- **INFO**: Normal operations, opportunities found
- **WARNING**: Rate limits, configuration issues
- **ERROR**: Failed trades, API errors
- **SUCCESS**: Successful trade executions

## Log Files

- `arbihedron_YYYY-MM-DD_HH-MM-SS.log` - Main application logs

## Log Format

```
2025-10-23 14:30:45.123 | INFO     | arbitrage_engine:scan_opportunities:145 - Found 5 executable opportunities
2025-10-23 14:30:45.456 | SUCCESS  | executor:execute_opportunity:78 - Execution successful: $6.50 profit
```

## Monitoring Logs

To watch logs in real-time:
```bash
tail -f logs/arbihedron_*.log
```

To search for errors:
```bash
grep ERROR logs/arbihedron_*.log
```

To see only successful trades:
```bash
grep SUCCESS logs/arbihedron_*.log
```