from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "short_paper" / "assets"
SCREENSHOTS = OUT / "screenshots"
RUN_ID = "run_20260812_101"
BASE_URL = "http://127.0.0.1:8010"


def read_excerpt(path: Path, start: int, end: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    excerpt = []
    for number in range(start, min(end, len(lines)) + 1):
        excerpt.append(f"{number:04d}  {lines[number - 1]}")
    return "\n".join(excerpt)


def source_html() -> str:
    snippets = [
        (
            "requirements.txt - Google ADK dependency",
            (ROOT / "requirements.txt").read_text(encoding="utf-8"),
        ),
        (
            "game_builder/agent.py - five-agent workflow",
            read_excerpt(ROOT / "game_builder" / "agent.py", 668, 751),
        ),
        (
            "lab_app/main.py - FastAPI lab wrapper",
            read_excerpt(ROOT / "lab_app" / "main.py", 144, 221),
        ),
        (
            f"{RUN_ID}/GameScene.ts - generated game artifact",
            read_excerpt(
                ROOT
                / "game_workspace"
                / "runs"
                / RUN_ID
                / "src"
                / "game"
                / "scenes"
                / "GameScene.ts",
                1,
                128,
            ),
        ),
    ]
    cards = "\n".join(
        f"""
        <section>
          <h2>{title}</h2>
          <pre>{code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</pre>
        </section>
        """
        for title, code in snippets
    )
    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{
          margin: 0;
          background: #f4f6f8;
          color: #111827;
          font-family: Arial, sans-serif;
        }}
        main {{
          width: 1420px;
          padding: 28px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 18px;
        }}
        section {{
          border: 1px solid #cbd5e1;
          background: #ffffff;
          border-radius: 6px;
          overflow: hidden;
          box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
        }}
        h1 {{
          grid-column: 1 / -1;
          margin: 0 0 2px;
          font-size: 28px;
        }}
        h2 {{
          margin: 0;
          padding: 10px 12px;
          background: #0f172a;
          color: #ffffff;
          font-size: 15px;
        }}
        pre {{
          margin: 0;
          max-height: 520px;
          overflow: hidden;
          padding: 12px;
          font-family: Consolas, "Courier New", monospace;
          font-size: 11px;
          line-height: 1.35;
          white-space: pre-wrap;
        }}
      </style>
    </head>
    <body>
      <main>
        <h1>Project Source Evidence</h1>
        {cards}
      </main>
    </body>
    </html>
    """


def workflow_html() -> str:
    return """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body { margin: 0; background: #ffffff; font-family: Arial, sans-serif; }
        .canvas { width: 1400px; height: 760px; padding: 36px; box-sizing: border-box; }
        h1 { margin: 0 0 20px; font-size: 30px; color: #111827; }
        svg { width: 100%; height: 660px; }
        .box { fill: #f8fafc; stroke: #334155; stroke-width: 2; rx: 8; }
        .tool { fill: #ecfeff; stroke: #0891b2; stroke-width: 2; rx: 8; }
        .decision { fill: #fff7ed; stroke: #ea580c; stroke-width: 2; rx: 8; }
        text { fill: #111827; font-size: 18px; font-weight: 700; }
        .small { fill: #475569; font-size: 13px; font-weight: 500; }
        .route { fill: none; stroke: #0f766e; stroke-width: 3; marker-end: url(#arrow); }
        .feedback { fill: none; stroke: #dc2626; stroke-width: 3; stroke-dasharray: 8 7; marker-end: url(#arrow-red); }
      </style>
    </head>
    <body>
    <div class="canvas">
      <h1>Google ADK Workflow: Multi-Agent Game Builder</h1>
      <svg viewBox="0 0 1320 660" role="img">
        <defs>
          <marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
            <path d="M2,2 L10,6 L2,10 z" fill="#0f766e" />
          </marker>
          <marker id="arrow-red" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
            <path d="M2,2 L10,6 L2,10 z" fill="#dc2626" />
          </marker>
        </defs>

        <rect class="box" x="30" y="70" width="185" height="82"/>
        <text x="122" y="104" text-anchor="middle">GameDesigner</text>
        <text class="small" x="122" y="128" text-anchor="middle">Design specification</text>

        <rect class="tool" x="250" y="70" width="190" height="82"/>
        <text x="345" y="104" text-anchor="middle">Workspace Tool</text>
        <text class="small" x="345" y="128" text-anchor="middle">Isolated Phaser run</text>

        <rect class="box" x="475" y="70" width="190" height="82"/>
        <text x="570" y="104" text-anchor="middle">TechnicalPlanner</text>
        <text class="small" x="570" y="128" text-anchor="middle">Manifest and plan</text>

        <rect class="box" x="700" y="70" width="190" height="82"/>
        <text x="795" y="104" text-anchor="middle">GameplayDeveloper</text>
        <text class="small" x="795" y="128" text-anchor="middle">Filesystem MCP edits</text>

        <rect class="tool" x="925" y="70" width="170" height="82"/>
        <text x="1010" y="104" text-anchor="middle">Build Gate</text>
        <text class="small" x="1010" y="128" text-anchor="middle">tsc + Vite build</text>

        <rect class="box" x="925" y="245" width="170" height="82"/>
        <text x="1010" y="279" text-anchor="middle">Playtester</text>
        <text class="small" x="1010" y="303" text-anchor="middle">Playwright MCP</text>

        <rect class="decision" x="700" y="245" width="190" height="82"/>
        <text x="795" y="279" text-anchor="middle">BugReviewer</text>
        <text class="small" x="795" y="303" text-anchor="middle">APPROVE / REVISE / REPLAN</text>

        <rect class="tool" x="475" y="430" width="190" height="82"/>
        <text x="570" y="464" text-anchor="middle">Finalize</text>
        <text class="small" x="570" y="488" text-anchor="middle">Preserve artifacts</text>

        <rect class="tool" x="700" y="430" width="190" height="82"/>
        <text x="795" y="464" text-anchor="middle">Human Review</text>
        <text class="small" x="795" y="488" text-anchor="middle">Bounded stop condition</text>

        <path class="route" d="M215 111 H250"/>
        <path class="route" d="M440 111 H475"/>
        <path class="route" d="M665 111 H700"/>
        <path class="route" d="M890 111 H925"/>
        <path class="route" d="M1010 152 V245"/>
        <path class="route" d="M925 286 H890"/>
        <path class="route" d="M700 286 C600 286 570 340 570 430"/>
        <path class="route" d="M795 327 V430"/>
        <path class="feedback" d="M700 286 C620 250 620 150 700 126"/>
        <path class="feedback" d="M795 245 C795 200 795 180 795 152"/>
        <text class="small" x="600" y="235">REPLAN</text>
        <text class="small" x="810" y="205">REVISE_DEVELOPER</text>
      </svg>
    </div>
    </body>
    </html>
    """


def adk_sdk_html() -> str:
    snippets = [
        (
            "game_builder/agent.py - Google ADK imports and model",
            read_excerpt(ROOT / "game_builder" / "agent.py", 1, 38),
        ),
        (
            "game_builder/agent.py - Filesystem and Playwright MCP toolsets",
            read_excerpt(ROOT / "game_builder" / "agent.py", 770, 821),
        ),
        (
            "game_builder/agent.py - ADK LlmAgent declarations",
            read_excerpt(ROOT / "game_builder" / "agent.py", 842, 910),
        ),
        (
            "game_builder/agent.py - root Google ADK Workflow",
            read_excerpt(ROOT / "game_builder" / "agent.py", 1628, 1733),
        ),
    ]
    cards = "\n".join(
        f"""
        <section>
          <h2>{title}</h2>
          <pre>{code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</pre>
        </section>
        """
        for title, code in snippets
    )
    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ margin: 0; background: #eef2f7; color: #0f172a; font-family: Arial, sans-serif; }}
        main {{
          width: 1460px;
          padding: 26px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          box-sizing: border-box;
        }}
        h1 {{
          grid-column: 1 / -1;
          margin: 0 0 4px;
          font-size: 28px;
        }}
        .subtitle {{
          grid-column: 1 / -1;
          margin: -2px 0 4px;
          color: #475569;
          font-size: 16px;
        }}
        section {{
          min-height: 300px;
          border: 1px solid #cbd5e1;
          background: white;
          border-radius: 7px;
          overflow: hidden;
          box-shadow: 0 12px 28px rgba(15, 23, 42, 0.1);
        }}
        h2 {{
          margin: 0;
          padding: 10px 12px;
          background: #111827;
          color: #ffffff;
          font-size: 15px;
        }}
        pre {{
          margin: 0;
          max-height: 360px;
          overflow: hidden;
          padding: 12px;
          font-family: Consolas, "Courier New", monospace;
          font-size: 10.6px;
          line-height: 1.35;
          white-space: pre-wrap;
        }}
      </style>
    </head>
    <body>
      <main>
        <h1>Google ADK SDK Evidence</h1>
        <div class="subtitle">Repository screenshots showing actual ADK imports, MCP toolsets, LlmAgent declarations, and Workflow routing.</div>
        {cards}
      </main>
    </body>
    </html>
    """


def capture() -> None:
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(viewport={"width": 1440, "height": 950}, device_scale_factor=1)
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path=SCREENSHOTS / "fig2_lab_dashboard.png", full_page=True)
        page.locator(".flow-card").screenshot(path=SCREENSHOTS / "fig6_adk_flow_section.png")

        game = browser.new_page(viewport={"width": 1280, "height": 850}, device_scale_factor=1)
        game.goto(f"{BASE_URL}/runs/{RUN_ID}/game/index.html", wait_until="networkidle")
        game.wait_for_timeout(2600)
        game.keyboard.press("Space")
        game.wait_for_timeout(900)
        game.keyboard.press("ArrowLeft")
        game.wait_for_timeout(400)
        evidence = game.evaluate(
            """() => {
              const bridge = window.__GAME_TEST__;
              const beforeReset = bridge && typeof bridge.getState === 'function'
                ? bridge.getState()
                : null;
              if (bridge && typeof bridge.reset === 'function') {
                bridge.reset();
              }
              const afterReset = bridge && typeof bridge.getState === 'function'
                ? bridge.getState()
                : null;
              const errors = bridge && typeof bridge.getErrors === 'function'
                ? bridge.getErrors()
                : [];
              return {
                pageTitle: document.title,
                bridgePresent: Boolean(bridge),
                hasGetState: Boolean(bridge && typeof bridge.getState === 'function'),
                hasReset: Boolean(bridge && typeof bridge.reset === 'function'),
                hasGetErrors: Boolean(bridge && typeof bridge.getErrors === 'function'),
                beforeReset,
                afterReset,
                errors,
              };
            }"""
        )
        (OUT / "browser_evidence.json").write_text(
            json.dumps(evidence, indent=2),
            encoding="utf-8",
        )
        game.wait_for_timeout(700)
        game.screenshot(path=SCREENSHOTS / "fig3_generated_game.png", full_page=True)

        source = browser.new_page(viewport={"width": 1480, "height": 980}, device_scale_factor=1)
        source.set_content(source_html(), wait_until="load")
        source.screenshot(path=SCREENSHOTS / "fig4_source_evidence.png", full_page=True)

        flow = browser.new_page(viewport={"width": 1460, "height": 840}, device_scale_factor=1)
        flow.set_content(workflow_html(), wait_until="load")
        flow.screenshot(path=SCREENSHOTS / "fig1_workflow_diagram.png", full_page=True)

        adk = browser.new_page(viewport={"width": 1480, "height": 940}, device_scale_factor=1)
        adk.set_content(adk_sdk_html(), wait_until="load")
        adk.screenshot(path=SCREENSHOTS / "fig7_google_adk_sdk_source.png", full_page=True)

        browser.close()


if __name__ == "__main__":
    capture()
