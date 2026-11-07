---
layout: ./base.css
theme: ./theme.css
header: "MARKDOWN SLIDE COMPILER"
footer: "Example presentation"
paginate: true
mermaid:
  theme: dark
---
# Markdown → HTML Slides

A tiny **deterministic** compiler. One command produces one HTML presentation.

- Author slides in GitHub-Flavoured Markdown.
- Apply any compatible local CSS theme.
- Open the generated `presentation.html` in your browser.

---
## The pipeline

Two boxes connected by a single arrow:

```mermaid
flowchart LR
    A[Markdown input] --> B[HTML slide deck]
```

---
## Code and content

A Python code fence gets **Prism** highlighting automatically:

```python
from pathlib import Path
print(Path("presentation.html").exists())
```

| Input | Output |
| --- | --- |
| Markdown + CSS | Portable HTML file |
| Mermaid definition | Browser-rendered SVG |

Use **Right Arrow** or **Space** to advance and **Left Arrow** to go back.
