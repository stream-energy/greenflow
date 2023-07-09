from os import environ

# Self-Monkey-Patch the REQUESTS_CA_BUNDLE env var as the cert is self-signed
environ["REQUESTS_CA_BUNDLE"] = f"${environ['PWD']}/api-proxy-lille-grid5000-fr-chain.pem"
