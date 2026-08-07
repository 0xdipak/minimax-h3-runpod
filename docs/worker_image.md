# Worker image (CI-built, public pull)

Built by GitHub Actions — layers pulled on GitHub's network, not from a laptop.

| Registry | Image |
|---|---|
| Public (ttl.sh, 7d) | `ttl.sh/ruizmr-minimax-h3-runpod:7d` |
| GHCR | `ghcr.io/ruizmr/minimax-h3-runpod:latest` |

SHA: `974ef206d6e838eb46251b4f2ee5af52f41d15f3`

Point the Runpod template `imageName` at the public ttl.sh tag (or make GHCR public).
Preferred long-term: console **Import Git Repository** so Runpod builds from this Dockerfile.
