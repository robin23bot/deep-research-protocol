---
name: deep-research
description: Orchestrates parallel, high-fidelity deep research using a Supervisor-Executor model. Gathers 50+ sources via fan-out search (Tavily, Serper, OpenAI), synthesizes insights with provenance tracking, and generates a formatted PDF report. Use for complex investigative tasks requiring high accuracy and broad source coverage.
---

# Deep Research Protocol

This skill implements the **Fulvio Deep Research Model**: a hierarchical, asynchronous orchestration pattern designed for maximum performance and citation quality.

## Core Workflow

1.  **Orchestration**: Spawn a Supervisor sub-agent (`sessions_spawn`).
2.  **Fan-Out**: Supervisor generates 3-5 specialized sub-queries and executes them in parallel using `scripts/research_fanout.py`.
3.  **Map-Reduce**: 
    - **Map**: Executors scrape and summarize sources in batches (filter score > 0.75).
    - **Reduce**: Planner synthesizes high-signal fragments into a master report.
4.  **Verification**: Independent Critic cross-references claims against raw logs.
5.  **Output**: Generate a professional PDF report using the browser tool.

## Tools & Commands

### 1. Parallel Fan-Out
Gather 50+ sources across multiple engines simultaneously.
```bash
python3 scripts/research_fanout.py "Main Topic" --queries "Subquery 1" "Subquery 2" "Subquery 3"
```

### 2. PDF Generation
Once research is synthesized into Markdown, use `agent-browser` to render and save as a pretty PDF.
- Format Markdown with clear headers and CSS-styled sections.
- Use `agent-browser pdf output.pdf` on the rendered local HTML or temporary preview.

## Multi-Agent Prompts

**Supervisor Prompt:**
> "You are the Research Supervisor. Decompose [Topic] into a hierarchical task tree. Manage state via JSON objects. Your goal is to map out the 'Truth' by checking multiple conflicting or complementary sources."

**Critic Prompt:**
> "You are the Red-Team Fact Checker. Find contradictions between the synthesis and raw sources. Flag any claim missing a direct source URL and quote."

## Best Practices
- **Parallelism**: Always run search engines concurrently to cut latency by 70%.
- **Provenance**: Tag every insight with a UUID linked to the raw source.
- **Cheapest Reasoning**: Use `o4-mini` for heavy agentic search steps to optimize cost.
- **Structured Handoffs**: Pass JSON state objects between agents, not conversational history.
