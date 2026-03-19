# Generic Wolfram oracle server for Eleguá.
#
# Provides a bare Wolfram kernel with the elegua[wolfram] HTTP server.
# Domain-specific init scripts and cleanup expressions are injected
# via environment variables:
#
#   ELEGUA_WOLFRAM_INIT     Path to .wl init script (optional)
#   ELEGUA_WOLFRAM_CLEANUP  Wolfram cleanup expression (optional)
#
# Example (sxAct):
#   docker run -e ELEGUA_WOLFRAM_INIT=/opt/xAct/init.wl \
#              -v ./xAct:/opt/xAct:ro \
#              elegua-wolfram-oracle

FROM wolframresearch/wolframengine:latest

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages elegua[wolfram]

EXPOSE 8765

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8765/health || exit 1

CMD ["python3", "-m", "elegua.wolfram", "serve"]
