"""Anti-AI-Slop Telemetry Console HTML renderer."""

from __future__ import annotations


def get_console_html() -> str:
    """Returns the Anti-AI-Slop Developer Telemetry Console HTML."""
    font_url = (
        "https://fonts.googleapis.com/css2?"
        "family=Inter:wght@400;500;600;700&"
        "family=JetBrains+Mono:wght@400;500;600&display=swap"
    )
    tmpl = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mutant-RL // Sim-to-Real Telemetry Console</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="__FONT_URL__" rel="stylesheet">"""
    rest = """
  <style>
    :root {
      --bg-canvas: #090b0e;
      --bg-panel: #101318;
      --bg-subtle: #161b22;
      --border-subtle: rgba(255, 255, 255, 0.08);
      --border-strong: rgba(255, 255, 255, 0.16);
      --text-primary: #e6edf3;
      --text-secondary: #8b949e;
      --text-muted: #6e7681;
      --accent-green: #2ea043;
      --accent-red: #f85149;
      --accent-amber: #d29922;
      --accent-blue: #388bfd;
      --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-canvas);
      color: var(--text-primary);
      font-family: var(--font-sans);
      font-size: 13px;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
    }
  </style>
</head>
<body>
  <div id="app">Mutant-RL Telemetry Console Initialized</div>
</body>
</html>
"""
    return tmpl.replace("__FONT_URL__", font_url) + rest
