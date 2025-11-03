# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: **[your-security-email@example.com]**

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

Please include the following information (as much as you can provide):

* Type of issue (e.g. buffer overflow, SQL injection, cross-site scripting, etc.)
* Full paths of source file(s) related to the manifestation of the issue
* The location of the affected source code (tag/branch/commit or direct URL)
* Any special configuration required to reproduce the issue
* Step-by-step instructions to reproduce the issue
* Proof-of-concept or exploit code (if possible)
* Impact of the issue, including how an attacker might exploit it

## Security Best Practices

When using Arbihedron, follow these security guidelines:

### 1. API Key Management

* **Never commit API keys to version control**
* Use environment variables (`.env` file)
* Enable IP whitelisting on your exchange account
* Use API keys with minimal required permissions (trade-only, no withdrawal)
* Rotate API keys regularly
* Use separate API keys for testing and production

### 2. Paper Trading First

* **Always test with paper trading enabled** before live trading
* Verify all configurations in a safe environment
* Start with small position sizes when going live

### 3. Network Security

* Use HTTPS for all API communications (default)
* Keep your system and dependencies up to date
* Use a firewall to restrict access to monitoring ports
* Consider using a VPN when trading from public networks

### 4. System Access

* Restrict access to the server running Arbihedron
* Use strong passwords and SSH keys
* Regularly review system logs
* Enable 2FA on your exchange accounts

### 5. Database Security

* The SQLite database contains trading history
* Secure the `data/` directory with appropriate permissions
* Regularly backup your database
* Never expose database files publicly

### 6. Docker Security

* Don't run containers as root (use the provided Dockerfile user configuration)
* Keep Docker images updated
* Scan images for vulnerabilities: `docker scan arbihedron:latest`
* Use secrets management for production deployments

### 7. Monitoring

* Enable alerts for suspicious activity
* Monitor for unusual trading patterns
* Set up rate limit notifications
* Review logs regularly for errors or warnings

## Known Security Considerations

### Exchange API Risks

* **Rate Limiting**: Exceeding rate limits can result in temporary bans
* **Slippage**: Large orders may experience significant slippage
* **Market Manipulation**: Be aware of potential wash trading or spoofing
* **Flash Crashes**: Implement circuit breakers for abnormal market conditions

### GNN Model Security

* The GNN model file (`models/gnn_arbitrage_best.pth`) should be verified before use
* Only load models from trusted sources
* Be cautious of adversarial attacks on ML models

### Configuration Vulnerabilities

* Incorrect configuration can lead to unexpected trading behavior
* Always validate configuration before starting the bot
* Use the `--paper-trading` flag for testing

## Dependency Security

We use several tools to maintain secure dependencies:

* **safety**: Checks for known security vulnerabilities in dependencies
* **bandit**: Scans Python code for security issues
* **Dependabot**: Automated dependency updates (GitHub)

Run security checks:
```bash
safety check
bandit -r . -x ./venv,./tests
```

## Vulnerability Disclosure Timeline

* **Day 0**: Vulnerability reported
* **Day 1-2**: Confirmation and assessment
* **Day 3-7**: Patch development and testing
* **Day 8-14**: Patch release and notification
* **Day 15+**: Public disclosure (if appropriate)

## Security Updates

Subscribe to security updates:
* Watch this repository for security advisories
* Enable notifications for releases
* Follow our Twitter/Discord for announcements

## Bug Bounty

We currently do not have a formal bug bounty program, but we greatly appreciate security researchers who responsibly disclose vulnerabilities. Recognition will be given in our security hall of fame.

## Attribution

We will acknowledge security researchers who report valid vulnerabilities:
* In the CHANGELOG.md
* In the security advisory
* In the CONTRIBUTORS.md (if they wish)

## Contact

Security Team: **[your-security-email@example.com]**

PGP Key: [Optional - Include your PGP public key fingerprint]

## Additional Resources

* [OWASP Top 10](https://owasp.org/www-project-top-ten/)
* [CWE Top 25](https://cwe.mitre.org/top25/)
* [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)

---

Last Updated: November 2, 2025
