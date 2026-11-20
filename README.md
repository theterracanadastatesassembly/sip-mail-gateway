# SIP Mail Gateway

**A Sovereign Infrastructure Project (SIP) Reference Implementation**

## Overview

SIP Mail Gateway is a reusable reference implementation that enables an Assembly to receive inbound email through Cloudflare and deliver it to its own locally operated mail infrastructure.

It is designed for Assemblies that want greater control over their email services without depending on a centrally operated gateway or an externally hosted mailbox provider.

Each Assembly operates and maintains its own installation.

## Purpose

This project provides a practical, documented approach to connecting:

- Cloudflare Email Routing
- A Cloudflare Worker
- A secure local mail-ingress receiver
- A Cloudflare Tunnel
- A locally operated mail server, such as Postfix

The components work together to receive an incoming message, securely transfer it to the Assembly's infrastructure, and pass it to the local mail server for delivery.

## Independent Operation

SIP Mail Gateway is intended to be independently deployed and administered.

Each participating Assembly is responsible for:

- Its own Cloudflare account and configuration.
- Its own Worker and Tunnel.
- Its own receiver installation and security credentials.
- Its own mail server, mailboxes and storage.
- Its own maintenance, backups and operational decisions.

No shared mailboxes, credentials or central gateway are required.

## Repository Contents

This repository will contain:

- **Source code:** The reusable mail-ingress receiver and supporting files.
- **Installation instructions:** Guidance for deploying and configuring the components.
- **Documentation:** Architecture, security, testing and troubleshooting guidance.
- **Examples:** Reference configurations that Assemblies can adapt to their own environments.

## Design Principles

SIP Mail Gateway follows these principles:

1. **Local control:** Each Assembly retains control of its own infrastructure.
2. **Independent operation:** An installation does not depend on another Assembly's gateway.
3. **Transparency:** Source code and deployment instructions are available for inspection.
4. **Adaptability:** Assemblies may modify the implementation to meet their own requirements.
5. **Security:** Credentials and configuration secrets remain under the control of the operating Assembly.
6. **Practical documentation:** Instructions are written to support administrators with varying levels of technical experience.

## Licence and Use

SIP Mail Gateway is intended to be freely accessed, used, modified and shared under the SIP Community Use Licence (SIP-CUL).

The licence is intended to prevent the sale or commercial resale of SIP itself while permitting reasonable fees for associated services, including installation, configuration, training, maintenance and technical support.

See `LICENSE.md` for the complete terms once the licence has been finalized.

## Downloading the Receiver on Ubuntu

To download the current generic receiver directly onto an Ubuntu server, run:

```bash
curl -fL --show-error -o receiver.py https://raw.githubusercontent.com/theterracanadastatesassembly/sip-mail-gateway/main/src/receiver.py
```

This saves the script as `receiver.py` in the current directory. The command downloads the source only; the receiver still needs to be configured for the Assembly's mail domain, token file and local mail environment before it is run.

If `curl` is not installed, install it first:

```bash
sudo apt update
sudo apt install -y curl
```

## Project Status

This repository is under development. Source code, installation procedures and documentation will be reviewed before being designated as an official SIP release.

## About SIP

The Sovereign Infrastructure Project (SIP) provides practical infrastructure reference materials intended to help Assemblies understand, establish and independently operate their own technical systems.

SIP resources are reference implementations, not mandatory prescriptions. Each Assembly remains responsible for evaluating and adapting them to its own requirements.
