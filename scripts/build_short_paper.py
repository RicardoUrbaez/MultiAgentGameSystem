from __future__ import annotations

import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image as RLImage,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "short_paper"
ASSETS = OUT / "assets"
SCREENSHOTS = ASSETS / "screenshots"
PDF_PATH = OUT / "multi_agent_game_builder_ieee_short_paper.pdf"
TEX_PATH = OUT / "main.tex"
BIB_PATH = OUT / "references.bib"
RUN_ID = "run_20260812_101"


def font(name: str = "times.ttf", size: int = 16) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts") / name,
        Path("C:/Windows/Fonts/times.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def make_validation_chart() -> Path:
    ASSETS.mkdir(parents=True, exist_ok=True)
    path = ASSETS / "fig5_validation_summary.png"
    width, height = 1200, 620
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = font("arialbd.ttf", 34)
    label_font = font("arial.ttf", 22)
    small_font = font("arial.ttf", 18)
    draw.text((52, 36), "Validation Summary for Report Evidence", fill="#111827", font=title_font)
    checks = [
        ("Project unit tests", "39 passed", True),
        ("Generated game typecheck", "tsc exit 0", True),
        ("Generated production build", "Vite exit 0", True),
        ("Browser TestBridge", "state/reset/errors", True),
        ("Cloud deployment", "planned", False),
    ]
    x0, y0 = 310, 130
    bar_h = 52
    for index, (label, value, passed) in enumerate(checks):
        y = y0 + index * 82
        draw.text((52, y + 10), label, fill="#111827", font=label_font)
        draw.rectangle((x0, y, x0 + 760, y + bar_h), outline="#334155", width=2, fill="#f8fafc")
        fill = "#22c55e" if passed else "#f59e0b"
        draw.rectangle((x0, y, x0 + (760 if passed else 410), y + bar_h), fill=fill)
        draw.text((x0 + 20, y + 13), value, fill="#111827", font=small_font)
        draw.text((x0 + 790, y + 13), "PASS" if passed else "NEXT", fill="#111827", font=small_font)
    draw.text(
        (52, 560),
        "Evidence is local and source-grounded. Public deployment is intentionally listed as a remaining step.",
        fill="#475569",
        font=small_font,
    )
    image.save(path)
    return path


def write_latex() -> None:
    figures = "assets/screenshots"
    tex = rf"""
\documentclass[conference]{{IEEEtran}}
\IEEEoverridecommandlockouts
\usepackage{{graphicx}}
\usepackage{{booktabs}}
\usepackage{{url}}
\usepackage{{hyperref}}
\usepackage{{array}}

\title{{Multi-Agent Game Builder: A Google ADK Agentic Lab for Browser Game Generation}}

\author{{
\IEEEauthorblockN{{Ricardo Urbaez}}
\IEEEauthorblockA{{Department of Computer Science and Technology\\
Kean University\\
Union, NJ, USA\\
Urbaez@kean.edu}}
}}

\begin{{document}}
\maketitle

\begin{{abstract}}
This short paper presents Multi-Agent Game Builder, a Google Agent Development Kit (ADK) agentic lab that transforms a compact browser-game request into an executable Phaser/Vite artifact. The system uses five specialized agents, shared ADK state, Model Context Protocol (MCP) tooling, deterministic typecheck/build gates, browser evidence, and reviewer-controlled routing. The report follows the CHAINS reference by emphasizing auditable artifacts, reproducibility limits, and deployment governance. Local evidence includes source screenshots, the FastAPI lab interface, the generated Asphalt Evade game, browser TestBridge state, 39 passing project tests, and passing typecheck/build checks.
\end{{abstract}}

\begin{{IEEEkeywords}}
Google ADK, multi-agent systems, Model Context Protocol, Phaser, FastAPI, browser testing, agentic AI lab
\end{{IEEEkeywords}}

\section{{Introduction}}
Agentic AI coursework is strongest when the demonstration is more than a prompt box. The assignment asks for a web app using JavaScript or Python frameworks, a public-host deployment target, and a LaTeX-style report compiled to PDF. This project satisfies the framework requirement through a Python FastAPI lab wrapper and a Google ADK workflow that creates, builds, previews, and tests Phaser browser games. The app is intentionally framed as an agentic software-engineering laboratory: the visible UI is only the operator surface, while ADK agents, MCP tools, build tools, and browser checks perform the actual work.

The project is modeled after scientific short-paper conventions used by CHAINS, which emphasizes auditable human-AI agent workflows, typed artifacts, telemetry, and verifier-gated outputs \cite{{chains2026}}. Instead of describing an imaginary swarm, this report documents the actual repository evidence: the five ADK agents, the generated game run, the test bridge, the lab UI, and the remaining deployment boundary.

This paper makes four contributions. First, it documents a five-agent Google ADK workflow for generating compact 2D browser games. Second, it describes the tool boundaries that separate design, planning, development, browser testing, and review. Third, it reports local validation evidence from unit tests, TypeScript typechecking, production build output, and browser runtime state. Fourth, it provides a deployment recommendation that keeps model credentials and generated-game execution in a trusted server-side environment.

\section{{Related Work}}
Google ADK provides a code-first framework for building agents that reason, plan, use tools, and deploy to Google Cloud infrastructure \cite{{adkweb,cloudrunadk}}. CHAINS shows why agentic systems should preserve artifacts, hashes, run ledgers, and verification evidence instead of relying only on natural-language summaries \cite{{chains2026}}. Multi-Agent Game Builder applies that idea to a software-generation setting: each run produces source files, build logs, browser-observable state, and previewable game output.

General FastAPI hosting platforms such as Render and Railway can run Python web services from a Git repository or Dockerfile \cite{{renderfastapi,railwayfastapi}}, while Vercel supports FastAPI through Python serverless functions \cite{{vercelfastapi}}. For this project, serverless hosting is less natural because ADK, MCP subprocesses, local generated artifacts, and browser automation benefit from a long-running trusted backend.

\section{{Methodology}}
The architecture uses five production agents: GameDesigner, TechnicalPlanner, GameplayDeveloper, Playtester, and BugReviewer. GameDesigner converts the user prompt into gameplay intent and acceptance expectations. TechnicalPlanner translates that design into an implementation plan for the Phaser template. GameplayDeveloper performs the source-code edits through Filesystem MCP. Playtester opens the generated game in a real browser through Playwright MCP and records behavior. BugReviewer reads build and browser evidence, assigns the final route, and prevents the developer from approving its own work.

The workflow uses ADK shared state to carry the current run identifier, game design, technical plan, build result, structured test report, review decision, iteration count, route history, and human-review status. The key routes are \texttt{{APPROVE}}, \texttt{{REVISE\_DEVELOPER}}, \texttt{{REPLAN}}, and \texttt{{HUMAN\_REVIEW}}. This design makes the flow inspectable: a failed implementation can return to the developer, an incomplete plan can return to the planner, and repeated or unsafe failures can stop for human review.

\begin{{figure}}[t]
\centering
\includegraphics[width=\columnwidth]{{{figures}/fig1_workflow_diagram.png}}
\caption{{Google ADK workflow diagram generated from the current project source.}}
\label{{fig:workflow}}
\end{{figure}}

\begin{{figure}}[t]
\centering
\includegraphics[height=0.90\columnwidth]{{{figures}/fig9_user_agent_structure.png}}
\caption{{Agent-structure diagram showing START, GameDesigner, workspace creation, TechnicalPlanner, developer stage, build gate, Playtester, BugReviewer, revise/replan/approve paths, human review, and END.}}
\label{{fig:userstructure}}
\end{{figure}}

\begin{{table}}[t]
\caption{{Agent Roles and Boundaries}}
\label{{tab:agents}}
\centering
\begin{{tabular}}{{p{{0.25\columnwidth}}p{{0.43\columnwidth}}p{{0.22\columnwidth}}}}
\toprule
Agent & Responsibility & Boundary\\
\midrule
GameDesigner & Interprets the prompt and produces design requirements. & No edits\\
TechnicalPlanner & Converts the design into a Phaser implementation plan. & No edits\\
GameplayDeveloper & Writes and repairs generated game source files. & Filesystem MCP\\
Playtester & Tests the real game in a browser. & Playwright MCP\\
BugReviewer & Scores evidence and controls routing. & No tool calls\\
\bottomrule
\end{{tabular}}
\end{{table}}

\section{{Google ADK SDK Evidence}}
The project includes both UI-level and source-level evidence that the workflow uses Google's Agent Development Kit. The lab UI includes an ADK Flow panel for presentation, while the source code imports \texttt{{google.adk}}, defines \texttt{{LlmAgent}} objects, creates \texttt{{McpToolset}} instances, and registers the root \texttt{{Workflow}} graph. These screenshots make the Google ADK requirement visible in the report rather than leaving it only as a dependency name.

\begin{{figure}}[t]
\centering
\includegraphics[width=0.70\columnwidth]{{{figures}/fig6_adk_flow_section.png}}
\caption{{Google ADK Flow panel from the lab UI, showing the START node, five agents, build gate, and finalize node.}}
\label{{fig:adkflow}}
\end{{figure}}

\begin{{figure*}}[t]
\centering
\includegraphics[width=0.95\textwidth]{{{figures}/fig7_google_adk_sdk_source.png}}
\caption{{Google ADK SDK source evidence showing \texttt{{google.adk}} imports, MCP toolsets, \texttt{{LlmAgent}} declarations, and root \texttt{{Workflow}} routing.}}
\label{{fig:adksdk}}
\end{{figure*}}

\section{{Implementation}}
The lab wrapper is implemented with FastAPI and static HTML/CSS/JavaScript. It lists generated runs, submits new ADK jobs, previews built games, opens full-screen output, and packages the built distribution as a ZIP. The UI also exposes the five-agent sequence to make the system understandable during a class presentation without pretending that the UI itself is the agent runtime.

The canonical generated artifact used for evidence is \texttt{{{RUN_ID}}}, which contains a Phaser game named Asphalt Evade. The game implements a simple lane-switching car-dodge mechanic with score, obstacles, restart behavior, and a browser-observable test bridge. The bridge exposes \texttt{{window.\_\_GAME\_TEST\_\_}} with \texttt{{getState()}}, \texttt{{reset()}}, and \texttt{{getErrors()}} so automated checks can inspect real runtime state rather than trusting a screenshot alone.

\begin{{figure}}[t]
\centering
\includegraphics[width=\columnwidth]{{{figures}/fig2_lab_dashboard.png}}
\caption{{FastAPI lab interface showing the five ADK agents, generated runs, preview iframe, and run metadata.}}
\label{{fig:lab}}
\end{{figure}}

\begin{{figure}}[t]
\centering
\includegraphics[width=\columnwidth]{{{figures}/fig3_generated_game.png}}
\caption{{Generated Phaser game output after the browser automation starts the game and sends a lane-change input.}}
\label{{fig:game}}
\end{{figure}}

\section{{Current Results}}
The project was verified locally on August 12, 2026. Running the unit suite with the repository virtual environment produced 39 passing tests. The generated game in \texttt{{{RUN_ID}}} typechecked with \texttt{{npx tsc --noEmit}} and rebuilt with \texttt{{npm run build-nolog}}, both exiting successfully. Browser evidence confirmed that the TestBridge exists, state can be read, reset restores score and lane values, and the captured error list is empty.

\begin{{table}}[t]
\caption{{Verification Evidence}}
\label{{tab:evidence}}
\centering
\begin{{tabular}}{{p{{0.38\columnwidth}}p{{0.24\columnwidth}}p{{0.25\columnwidth}}}}
\toprule
Check & Result & Evidence\\
\midrule
Project tests & PASS & 39 tests OK\\
Generated typecheck & PASS & \texttt{{tsc}} exit 0\\
Generated build & PASS & Vite exit 0\\
Browser TestBridge & PASS & State/reset/errors exposed\\
Public deployment & Planned & Cloud Run recommended\\
\bottomrule
\end{{tabular}}
\end{{table}}

\begin{{figure}}[t]
\centering
\includegraphics[width=\columnwidth]{{assets/fig5_validation_summary.png}}
\caption{{Validation chart summarizing the local evidence and the remaining deployment step.}}
\label{{fig:validation}}
\end{{figure}}

\section{{Artifact and Evidence Model}}
Each run creates an isolated project directory under \texttt{{game\_workspace/runs}}. The generated run stores source files, installed dependencies, build logs, production \texttt{{dist}} output, screenshots, and browser-observable state. The lab app stores job records under \texttt{{game\_workspace/lab\_jobs}} so the presentation can explain when a prompt started, whether it completed, the exit code, and which run produced the visible game.

\begin{{table}}[t]
\caption{{Run Artifacts Used in the Report}}
\label{{tab:artifacts}}
\centering
\begin{{tabular}}{{p{{0.33\columnwidth}}p{{0.27\columnwidth}}p{{0.28\columnwidth}}}}
\toprule
Artifact & Location & Purpose\\
\midrule
Generated game & \texttt{{run\_101}} & Playable output\\
Production build & \texttt{{dist/}} & Hosted HTML5 game\\
Browser state & TestBridge JSON & Runtime verification\\
Lab job records & \texttt{{lab\_jobs/}} & Prompt/run trace\\
Screenshots & \texttt{{output/short\_paper}} & Report figures\\
\bottomrule
\end{{tabular}}
\end{{table}}

\section{{Security and Governance}}
The system is designed so model credentials stay server-side and are never bundled into frontend assets or generated game code. Filesystem MCP is scoped to generated run directories, while the reusable Phaser template and local secrets remain outside the generated-game write surface. Browser testing is read-only from the Playtester perspective. The BugReviewer route provides a governance checkpoint because it can force revision, replanning, or human inspection before presenting an artifact as complete.

\section{{Deployment Recommendation}}
For the exact full ADK system, the easiest robust deployment target is Google Cloud Run, because Google documents ADK deployment to Cloud Run and the application already depends on Google ADK. Cloud Run also fits a containerized Python service with server-side credentials and controlled runtime workers. If the class requires one of the highlighted general platforms, Render or Railway is easier than Vercel for this backend because both can host long-running FastAPI services. Vercel is best reserved for a static exported game or a lightweight frontend shell, not the full ADK/MCP/browser-automation backend.

\begin{{table}}[t]
\caption{{Deployment Platform Fit}}
\label{{tab:deploy}}
\centering
\begin{{tabular}}{{p{{0.25\columnwidth}}p{{0.23\columnwidth}}p{{0.38\columnwidth}}}}
\toprule
Platform & Fit & Reason\\
\midrule
Cloud Run & Best full-system fit & Official ADK path; containerized backend; server-side secrets\\
Render & Good class fallback & Simple FastAPI web service deployment\\
Railway & Good class fallback & FastAPI guide, Docker support, environment variables\\
Vercel & Limited & Python serverless is less suitable for ADK plus MCP workers\\
\bottomrule
\end{{tabular}}
\end{{table}}

\section{{Assignment Fit}}
The assignment requires a web app with an AI agentic lab, a JavaScript or Python framework, public-host planning, and a LaTeX report compiled to PDF. Multi-Agent Game Builder directly addresses those requirements with FastAPI, Google ADK, Phaser/TypeScript generated artifacts, deployment analysis, and the PDF/LaTeX package produced with this report.

\begin{{table}}[t]
\caption{{Assignment Requirement Mapping}}
\label{{tab:assignment}}
\centering
\begin{{tabular}}{{p{{0.35\columnwidth}}p{{0.52\columnwidth}}}}
\toprule
Requirement & Project Evidence\\
\midrule
Web app & FastAPI lab UI at local class-demo URL\\
AI agentic lab & Five Google ADK agents with workflow routing\\
JS/Python framework & FastAPI plus Phaser/Vite generated game\\
Public host plan & Cloud Run; Render/Railway fallback\\
Report PDF & IEEE-style PDF plus Overleaf-ready source\\
\bottomrule
\end{{tabular}}
\end{{table}}

\section{{Evaluation Protocol}}
Future evaluation should compare three modes under matched prompt and budget constraints: a manual template edit baseline, a single LLM prompt baseline, and the five-agent ADK workflow. Metrics should include workflow completion, typecheck/build success, browser-test pass rate, defect count, time to playable output, number of revision loops, and unsupported or unverifiable claims in the final artifact.

\section{{Discussion}}
The project demonstrates a real agentic software-engineering workflow, not a simulated UI. Its strongest evidence is the combination of ADK source code, MCP tool boundaries, generated artifacts, and runtime browser inspection. The main limitation is deployment complexity: full public hosting must keep Google credentials server-side, isolate generated workspace writes, and provide a controlled browser worker.

\section{{Conclusion}}
Multi-Agent Game Builder provides a compact scientific demonstration of a Google ADK agentic lab for browser-game generation. The system uses five specialized agents, shared state, deterministic build checks, Playwright-based browser evidence, and a FastAPI UI for class demonstration. The recommended full-system deployment path is Google Cloud Run, with Render or Railway as class-friendly alternatives when a simpler FastAPI host is required.

\begin{{figure*}}[t]
\centering
\includegraphics[width=0.95\textwidth]{{{figures}/fig4_source_evidence.png}}
\caption{{Source evidence screenshot showing ADK dependency, workflow source, FastAPI lab routes, and the generated game artifact.}}
\label{{fig:source}}
\end{{figure*}}

\bibliographystyle{{IEEEtran}}
\bibliography{{references}}
\end{{document}}
""".strip()
    TEX_PATH.write_text(tex + "\n", encoding="utf-8")

    bib = r"""
@inproceedings{chains2026,
  title = {Collaborative Human-AI ageNt Swarm for Conducting Scientific Research},
  author = {Villalobos, Wilbert and Kumar, Yulia and Li, J. Jenny and Kruger, Dov and Marchena, Jose},
  booktitle = {ICDS 2026: The Twentieth International Conference on Digital Society},
  year = {2026},
  url = {https://www.thinkmind.org/library/ICDS/ICDS_2026/icds_2026_1_30_10034.html}
}

@misc{adkweb,
  title = {Agent Development Kit},
  author = {{Google}},
  year = {2026},
  url = {https://adk.dev/}
}

@misc{cloudrunadk,
  title = {Quickstart: Build and deploy an AI agent to Cloud Run using the Agent Development Kit},
  author = {{Google Cloud}},
  year = {2026},
  url = {https://docs.cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-adk-service}
}

@misc{renderfastapi,
  title = {Deploy a FastAPI App},
  author = {{Render}},
  year = {2026},
  url = {https://render.com/docs/deploy-fastapi}
}

@misc{railwayfastapi,
  title = {Deploy a FastAPI App},
  author = {{Railway}},
  year = {2026},
  url = {https://docs.railway.com/guides/fastapi}
}

@misc{vercelfastapi,
  title = {Deploy a FastAPI app on Vercel},
  author = {{Vercel}},
  year = {2026},
  url = {https://vercel.com/docs/frameworks/backend/fastapi}
}
""".strip()
    BIB_PATH.write_text(bib + "\n", encoding="utf-8")


def para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(textwrap.fill(text, 100), style)


def make_pdf() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    chart = make_validation_chart()
    browser = json.loads((ASSETS / "browser_evidence.json").read_text(encoding="utf-8"))

    doc = BaseDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        leftMargin=0.62 * inch,
        rightMargin=0.62 * inch,
        topMargin=0.68 * inch,
        bottomMargin=0.68 * inch,
    )
    page_w, page_h = letter
    gutter = 0.24 * inch
    col_w = (doc.width - gutter) / 2
    title_h = 2.32 * inch
    first_frames = [
        Frame(doc.leftMargin, page_h - doc.topMargin - title_h, doc.width, title_h, id="title"),
        Frame(doc.leftMargin, doc.bottomMargin, col_w, doc.height - title_h, id="left"),
        Frame(doc.leftMargin + col_w + gutter, doc.bottomMargin, col_w, doc.height - title_h, id="right"),
    ]
    later_frames = [
        Frame(doc.leftMargin, doc.bottomMargin, col_w, doc.height, id="left"),
        Frame(doc.leftMargin + col_w + gutter, doc.bottomMargin, col_w, doc.height, id="right"),
    ]
    full_frames = [
        Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="full"),
    ]

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Times-Roman", 8)
        canvas.drawCentredString(page_w / 2, 0.38 * inch, str(canvas.getPageNumber()))
        canvas.restoreState()

    doc.addPageTemplates(
        [
            PageTemplate(id="first", frames=first_frames, onPage=footer, autoNextPageTemplate="later"),
            PageTemplate(id="later", frames=later_frames, onPage=footer),
            PageTemplate(id="full", frames=full_frames, onPage=footer),
        ]
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "IEEE Title",
        parent=styles["Title"],
        fontName="Times-Bold",
        fontSize=18,
        leading=21,
        alignment=TA_CENTER,
        spaceAfter=7,
    )
    author_style = ParagraphStyle(
        "IEEE Author",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    abstract_style = ParagraphStyle(
        "Abstract",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=8.7,
        leading=10.2,
        alignment=TA_JUSTIFY,
        firstLineIndent=0,
        spaceAfter=4,
    )
    body = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=9.2,
        leading=10.8,
        alignment=TA_JUSTIFY,
        spaceAfter=4,
    )
    section = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName="Times-Bold",
        fontSize=10,
        leading=12,
        spaceBefore=7,
        spaceAfter=4,
    )
    caption = ParagraphStyle(
        "Caption",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=8,
        leading=9.5,
        alignment=TA_CENTER,
        spaceAfter=7,
    )

    story = [
        Paragraph(
            "Multi-Agent Game Builder: A Google ADK Agentic Lab for Browser Game Generation",
            title_style,
        ),
        Paragraph(
            "Ricardo Urbaez<br/>Department of Computer Science and Technology, Kean University<br/>Union, NJ, USA<br/>Urbaez@kean.edu",
            author_style,
        ),
        Paragraph(
            "<b>Abstract-</b> This short paper presents Multi-Agent Game Builder, a Google ADK agentic lab that transforms a compact browser-game request into an executable Phaser/Vite artifact. The system uses five specialized agents, shared ADK state, MCP tooling, deterministic typecheck/build gates, browser evidence, and reviewer-controlled routing. Local evidence includes source screenshots, the FastAPI lab interface, the generated Asphalt Evade game, browser TestBridge state, 39 passing project tests, and passing generated-game checks.",
            abstract_style,
        ),
        Paragraph(
            "<b>Keywords-</b> Google ADK; multi-agent systems; MCP; Phaser; FastAPI; browser testing.",
            abstract_style,
        ),
    ]

    sections = [
        (
            "I. INTRODUCTION",
            "Agentic AI coursework is strongest when the demonstration is more than a prompt box. The assignment asks for a web app using JavaScript or Python frameworks, a public-host deployment target, and a LaTeX-style report compiled to PDF. This project satisfies the framework requirement through a Python FastAPI lab wrapper and a Google ADK workflow that creates, builds, previews, and tests Phaser browser games. The app is framed as an agentic software-engineering laboratory: the visible UI is the operator surface, while ADK agents, MCP tools, build tools, and browser checks perform the work. The report follows the CHAINS reference style by emphasizing auditable workflows, artifacts, telemetry, and verification evidence.",
        ),
        (
            "II. RELATED WORK",
            "Google ADK provides a code-first framework for agents that reason, plan, use tools, and deploy to Google Cloud. CHAINS shows why agentic systems should preserve artifacts, run ledgers, and verification evidence instead of relying only on natural-language summaries. Multi-Agent Game Builder applies that idea to software generation: each run produces source files, build logs, browser-observable state, and previewable output. FastAPI platforms such as Render and Railway can host Python services, while Vercel supports Python serverless functions. For this app, serverless hosting is less natural because ADK, MCP subprocesses, generated workspace files, and browser automation benefit from a long-running trusted backend.",
        ),
    ]
    for heading, text in sections:
        story.append(Paragraph(heading, section))
        story.append(para(text, body))

    story.append(Paragraph("III. CONTRIBUTIONS", section))
    story.append(
        para(
            "This paper makes four contributions: it documents a five-agent Google ADK workflow for compact 2D browser-game generation; it describes tool boundaries that separate design, planning, development, browser testing, and review; it reports local validation evidence from unit tests, TypeScript typechecking, production build output, and browser runtime state; and it provides a deployment recommendation that keeps model credentials and generated-game execution in a trusted server-side environment.",
            body,
        )
    )

    story.append(
        KeepTogether(
            [
                RLImage(str(SCREENSHOTS / "fig1_workflow_diagram.png"), width=col_w, height=col_w * 0.52),
                Paragraph("Fig. 1. Google ADK workflow diagram generated from the current project source.", caption),
            ]
        )
    )
    story.append(Paragraph("IV. METHODOLOGY", section))
    story.append(
        para(
            "The architecture uses five production agents: GameDesigner, TechnicalPlanner, GameplayDeveloper, Playtester, and BugReviewer. GameDesigner converts the user prompt into gameplay intent and acceptance expectations. TechnicalPlanner translates that design into an implementation plan for the Phaser template. GameplayDeveloper performs source-code edits through Filesystem MCP. Playtester opens the generated game in a real browser through Playwright MCP and records behavior. BugReviewer reads build and browser evidence, assigns the final route, and prevents the developer from approving its own work.",
            body,
        )
    )
    story.append(
        para(
            "The workflow uses ADK shared state to carry the current run identifier, game design, technical plan, build result, structured test report, review decision, iteration count, route history, and human-review status. The key routes are APPROVE, REVISE_DEVELOPER, REPLAN, and HUMAN_REVIEW. A failed implementation can return to the developer, an incomplete plan can return to the planner, and repeated or unsafe failures can stop for human review.",
            body,
        )
    )
    story.append(
        KeepTogether(
            [
                RLImage(str(SCREENSHOTS / "fig9_user_agent_structure.png"), width=col_w * 0.70, height=col_w * 1.22),
                Paragraph("Fig. 2. Agent-structure diagram showing START, GameDesigner, workspace creation, TechnicalPlanner, developer stage, build gate, Playtester, BugReviewer, revision/replan paths, human review, and END.", caption),
            ]
        )
    )

    agent_rows = [
        ["Agent", "Responsibility", "Boundary"],
        ["GameDesigner", "Design requirements", "No edits"],
        ["TechnicalPlanner", "Phaser plan", "No edits"],
        ["GameplayDeveloper", "Writes game source", "Filesystem MCP"],
        ["Playtester", "Browser tests", "Playwright MCP"],
        ["BugReviewer", "Routes evidence", "No tools"],
    ]
    table = Table(agent_rows, colWidths=[0.29 * col_w, 0.42 * col_w, 0.29 * col_w])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.4),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(KeepTogether([Paragraph("TABLE I. AGENT ROLES AND BOUNDARIES", caption), table, Spacer(1, 6)]))

    story.append(Paragraph("V. GOOGLE ADK SDK EVIDENCE", section))
    story.append(
        para(
            "The project includes both UI-level and source-level evidence that the workflow uses Google's Agent Development Kit. The lab UI includes an ADK Flow panel for presentation, while the source code imports google.adk, defines LlmAgent objects, creates McpToolset instances, and registers the root Workflow graph. These screenshots make the Google ADK requirement visible in the report rather than leaving it only as a dependency name.",
            body,
        )
    )
    story.append(
        KeepTogether(
            [
                RLImage(str(SCREENSHOTS / "fig6_adk_flow_section.png"), width=col_w * 0.58, height=col_w * 0.95),
                Paragraph("Fig. 3. Google ADK Flow panel from the lab UI, showing START, the five agents, build gate, and finalize node.", caption),
            ]
        )
    )
    story.append(
        KeepTogether(
            [
                RLImage(str(SCREENSHOTS / "fig7_google_adk_sdk_source.png"), width=col_w, height=col_w * 0.65),
                Paragraph("Fig. 4. Google ADK SDK source evidence: imports, MCP toolsets, LlmAgent declarations, and Workflow routing.", caption),
            ]
        )
    )

    story.append(Paragraph("VI. IMPLEMENTATION", section))
    story.append(
        para(
            f"The lab wrapper is implemented with FastAPI and static HTML/CSS/JavaScript. It lists generated runs, submits ADK jobs, previews built games, opens full-screen output, and packages built distributions as ZIP files. The UI also exposes the five-agent sequence to make the system understandable during a class presentation without pretending that the UI itself is the agent runtime. The evidence run is {RUN_ID}, a generated Phaser game named Asphalt Evade. The game implements a lane-switching car-dodge mechanic with score, obstacles, restart behavior, and a browser-observable test bridge.",
            body,
        )
    )
    story.append(
        KeepTogether(
            [
                RLImage(str(SCREENSHOTS / "fig2_lab_dashboard.png"), width=col_w, height=col_w * 0.76),
                Paragraph("Fig. 5. FastAPI lab interface showing five ADK agents, generated runs, preview iframe, and metadata.", caption),
            ]
        )
    )
    story.append(
        KeepTogether(
            [
                RLImage(str(SCREENSHOTS / "fig3_generated_game.png"), width=col_w, height=col_w * 0.66),
                Paragraph("Fig. 6. Generated Phaser game after browser automation starts the game and sends input.", caption),
            ]
        )
    )
    story.append(Paragraph("VII. CURRENT RESULTS", section))
    story.append(
        para(
            "The project was verified locally on August 12, 2026. Running the unit suite with the repository virtual environment produced 39 passing tests. The generated game typechecked with npx tsc --noEmit and rebuilt with npm run build-nolog. Browser evidence confirmed that the TestBridge exists, state can be read, reset restores score and lane values, and the captured error list is empty.",
            body,
        )
    )
    ev_rows = [
        ["Check", "Result", "Evidence"],
        ["Project tests", "PASS", "39 tests OK"],
        ["Generated typecheck", "PASS", "tsc exit 0"],
        ["Generated build", "PASS", "Vite exit 0"],
        ["Browser TestBridge", "PASS", "state/reset/errors"],
        ["Public deployment", "PLANNED", "Cloud Run target"],
    ]
    ev = Table(ev_rows, colWidths=[0.39 * col_w, 0.23 * col_w, 0.38 * col_w])
    ev.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.4),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ]
        )
    )
    story.append(KeepTogether([Paragraph("TABLE II. VERIFICATION EVIDENCE", caption), ev, Spacer(1, 6)]))
    story.append(
        KeepTogether(
            [
                RLImage(str(chart), width=col_w, height=col_w * 0.52),
                Paragraph("Fig. 7. Validation chart summarizing local evidence and the remaining deployment step.", caption),
            ]
        )
    )

    story.append(Paragraph("VIII. ARTIFACT AND EVIDENCE MODEL", section))
    story.append(
        para(
            "Each run creates an isolated project directory under game_workspace/runs. The generated run stores source files, installed dependencies, build logs, production dist output, screenshots, and browser-observable state. The lab app stores job records under game_workspace/lab_jobs so the presentation can explain when a prompt started, whether it completed, the exit code, and which run produced the visible game.",
            body,
        )
    )
    artifact_rows = [
        ["Artifact", "Location", "Purpose"],
        ["Generated game", "run_101", "Playable output"],
        ["Production build", "dist/", "Hosted HTML5 game"],
        ["Browser state", "TestBridge JSON", "Runtime verification"],
        ["Lab job records", "lab_jobs/", "Prompt/run trace"],
        ["Screenshots", "output/short_paper", "Report figures"],
    ]
    artifacts = Table(artifact_rows, colWidths=[0.34 * col_w, 0.30 * col_w, 0.36 * col_w])
    artifacts.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.2),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(KeepTogether([Paragraph("TABLE III. RUN ARTIFACTS USED IN THE REPORT", caption), artifacts, Spacer(1, 6)]))

    story.append(Paragraph("IX. SECURITY AND GOVERNANCE", section))
    story.append(
        para(
            "The system is designed so model credentials stay server-side and are never bundled into frontend assets or generated game code. Filesystem MCP is scoped to generated run directories, while the reusable Phaser template and local secrets remain outside the generated-game write surface. Browser testing is read-only from the Playtester perspective. The BugReviewer route provides a governance checkpoint because it can force revision, replanning, or human inspection before presenting an artifact as complete.",
            body,
        )
    )

    story.append(Paragraph("X. DEPLOYMENT RECOMMENDATION", section))
    story.append(
        para(
            "For the exact full ADK system, the easiest robust deployment target is Google Cloud Run because Google documents ADK deployment to Cloud Run and the application already depends on Google ADK. If the class requires one of the highlighted general platforms, Render or Railway is easier than Vercel for this backend. Vercel is best reserved for a static exported game or lightweight frontend shell, not the full ADK/MCP/browser-automation backend.",
            body,
        )
    )
    deploy_rows = [
        ["Platform", "Fit", "Reason"],
        ["Cloud Run", "Best", "Official ADK path; server-side secrets"],
        ["Render", "Good", "FastAPI web service deployment"],
        ["Railway", "Good", "Docker and env var support"],
        ["Vercel", "Limited", "Serverless is less natural for MCP workers"],
    ]
    dep = Table(deploy_rows, colWidths=[0.25 * col_w, 0.18 * col_w, 0.57 * col_w])
    dep.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.3),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ]
        )
    )
    story.append(KeepTogether([Paragraph("TABLE IV. DEPLOYMENT PLATFORM FIT", caption), dep, Spacer(1, 6)]))

    story.append(Paragraph("XI. ASSIGNMENT FIT", section))
    story.append(
        para(
            "The assignment requires a web app with an AI agentic lab, a JavaScript or Python framework, public-host planning, and a LaTeX report compiled to PDF. Multi-Agent Game Builder addresses those requirements with FastAPI, Google ADK, Phaser/TypeScript generated artifacts, deployment analysis, and the PDF/LaTeX package produced with this report.",
            body,
        )
    )
    assignment_rows = [
        ["Requirement", "Project Evidence"],
        ["Web app", "FastAPI lab UI at local class-demo URL"],
        ["AI agentic lab", "Five Google ADK agents with workflow routing"],
        ["JS/Python framework", "FastAPI plus Phaser/Vite generated game"],
        ["Public host plan", "Cloud Run; Render/Railway fallback"],
        ["Report PDF", "IEEE-style PDF plus Overleaf-ready source"],
    ]
    assignment = Table(assignment_rows, colWidths=[0.37 * col_w, 0.63 * col_w])
    assignment.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.2),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(KeepTogether([Paragraph("TABLE V. ASSIGNMENT REQUIREMENT MAPPING", caption), assignment, Spacer(1, 6)]))

    story.append(Paragraph("XII. EVALUATION PROTOCOL", section))
    story.append(
        para(
            "Future evaluation should compare manual template editing, a single LLM prompt baseline, and the five-agent ADK workflow under matched prompts and budgets. Metrics should include completion rate, typecheck/build success, browser-test pass rate, defect count, time to playable output, revision loops, and unsupported claims. A stronger study would run several game prompts, such as Pong, maze escape, car dodge, and top-down shooter, then report pass rates and defect categories across repeated trials.",
            body,
        )
    )
    story.append(Paragraph("XIII. DISCUSSION AND CONCLUSION", section))
    story.append(
        para(
            "The project demonstrates a real agentic software-engineering workflow rather than simulated UI activity. Its strongest evidence is the combination of ADK source code, MCP tool boundaries, generated artifacts, and runtime browser inspection. The main limitation is deployment complexity: full public hosting must preserve server-side credentials, generated workspace isolation, and controlled browser workers. For class presentation, the local lab is already useful because it can show the agent sequence, generated run list, playable output, and evidence bundle without exposing secrets.",
            body,
        )
    )
    story.append(
        para(
            f"Browser TestBridge evidence: bridgePresent={browser['bridgePresent']}, beforeReset.score={browser['beforeReset']['score']}, afterReset.score={browser['afterReset']['score']}, errors={len(browser['errors'])}.",
            body,
        )
    )
    story.append(Paragraph("REFERENCES", section))
    refs = [
        "[1] W. Villalobos et al., \"Collaborative Human-AI ageNt Swarm for Conducting Scientific Research,\" ICDS 2026.",
        "[2] Google, \"Agent Development Kit,\" https://adk.dev/.",
        "[3] Google Cloud, \"Build and deploy an AI agent to Cloud Run using ADK.\"",
        "[4] Render, \"Deploy a FastAPI App.\"",
        "[5] Railway, \"Deploy a FastAPI App.\"",
        "[6] Vercel, \"Deploy a FastAPI app on Vercel.\"",
    ]
    for ref in refs:
        story.append(Paragraph(ref, body))

    story.append(NextPageTemplate("full"))
    story.append(PageBreak())
    story.append(Paragraph("APPENDIX: SOURCE AND ARTIFACT EVIDENCE", section))
    story.append(RLImage(str(SCREENSHOTS / "fig4_source_evidence.png"), width=doc.width, height=doc.width * 0.69))
    story.append(Paragraph("Fig. 8. Source evidence screenshot: ADK dependency, workflow source, FastAPI routes, and generated game artifact.", caption))
    story.append(Spacer(1, 10))
    story.append(RLImage(str(SCREENSHOTS / "fig7_google_adk_sdk_source.png"), width=doc.width, height=doc.width * 0.62))
    story.append(Paragraph("Fig. 9. Full-width Google ADK SDK section screenshot included for detailed inspection of imports, MCP toolsets, agents, and Workflow routing.", caption))

    doc.build(story)


if __name__ == "__main__":
    write_latex()
    make_pdf()
    print(PDF_PATH)
    print(TEX_PATH)
    print(BIB_PATH)
