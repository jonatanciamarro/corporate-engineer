# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

Corporate compliance mandates safe disclosure:
1. Do not open public GitHub issues for security vulnerabilities.
2. Run the local pre-flight scanner:
   ```powershell
   python .agents/skills/corp-pipeline/scripts/secret_scanner.py .
   ```
3. Report any critical security findings directly to the project maintainers or corporate security team.
