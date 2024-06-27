# Transition to Quantum-Safe Authentication in TLS
Files related to the master's thesis on the transition to quantum-safe authentication in TLS 1.3 by Joshua Drexel.

## Notes

- The python script `emulated-nw-assessmnt/run-bench_emulated-nw-assessmnt.py` assumes that the user can run `ip` commands with `sudo` without having to pass the password. One possible solution is to add the following to `/etc/sudoers.d/passwordless-ip`:
```bash
USERNAME HOST_NAME= NOPASSWD:SETENV: /usr/bin/ip
```
