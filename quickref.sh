#!/bin/bash
# arbihedron quick reference

cat << 'EOF'
arbihedron quick reference
==========================

service control
---------------
  ./arbi start          start bot (background)
  ./arbi stop           stop bot gracefully
  ./arbi restart        restart bot
  ./arbi status         show status
  ./arbi logs           view recent logs
  ./arbi logs -f        follow logs real-time
  ./arbi install        install auto-start (launchagent)
  ./arbi uninstall      remove auto-start

monitoring & alerts
-------------------
  ./arbi health            show health metrics
  ./arbi test-alerts       test email/slack notifications
  ./arbi config-alerts     configure alert settings
  
  health dashboard:
    http://localhost:8080/status    (web browser)
    http://localhost:8080/health    (simple check)
    http://localhost:8080/metrics   (json data)

data & analytics
----------------
  python view_data.py sessions        list all sessions
  python view_data.py session <id>    session details
  python view_data.py summary         overall statistics
  python view_data.py export <id>     export to json
  python view_data.py export-all      export to csv
  
  ./arbi report markdown   generate md report
  ./arbi report html       generate html report  
  ./arbi report json       export analytics json
  ./arbi report all        generate all reports

testing & development
---------------------
  python test_database.py      test persistence
  python test_alerts.py        test notifications
  ./test_service.sh            test service mgmt
  python main.py               run directly (dev mode)

important files
---------------
  data/arbihedron.db           main database
  exports/                     csv/json exports
  logs/arbihedron_*.log        bot logs
  logs/service/                service logs
  .env                         configuration (alerts/health)

quick start (production)
------------------------
  1. ./arbi config-alerts # setup notifications (optional)
  2. ./arbi test-alerts   # test alerts (optional)
  3. ./arbi install       # setup auto-start
  4. ./arbi start         # start the bot
  5. ./arbi status        # verify running
  6. ./arbi health        # check health
  7. ./arbi logs -f       # monitor activity

monitoring routine
------------------
  daily:    ./arbi status
            ./arbi health
  weekly:   python view_data.py summary
            ./arbi report all
            python view_data.py export-all

alert configuration (.env)
--------------------------
  # email
  EMAIL_ENABLED=true
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=your-email@gmail.com
  SMTP_PASSWORD=app-password
  EMAIL_RECIPIENTS=you@example.com
  
  # slack
  SLACK_ENABLED=true
  SLACK_WEBHOOK_URL=https://hooks.slack.com/...
  
  # health
  HEALTH_ENABLED=true
  HEALTH_PORT=8080

troubleshooting
---------------
  bot won't start:
    → ./arbi logs
    → check .env file
    → python arbihedron_service.py (test directly)
  
  bot keeps crashing:
    → ./arbi logs
    → tail -f logs/arbihedron_*.log
    → check exchange api keys
  
  alerts not working:
    → ./arbi test-alerts
    → check .env configuration
    → verify smtp/slack credentials
  
  health endpoint not accessible:
    → check if running: ./arbi status
    → check port: lsof -i :8080
    → try: curl http://localhost:8080/health
  
  launchagent issues:
    → ./arbi uninstall
    → ./arbi install
    → launchctl list | grep arbihedron

best practices
--------------
  - configure alerts before long runs
  - check status & health daily
  - export data weekly (backup)
  - monitor health endpoint
  - test alerts after config changes
  - review alert logs for issues
  - keep .env file secure

current status
--------------
EOF

# show actual status
cd "$(dirname "$0")"
if [ -f "arbi" ]; then
    ./arbi status 2>/dev/null || echo "service stopped"
fi