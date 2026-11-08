---
theme: ../../themes/card-theme.css
header: "MARKDOWN SLIDE COMPILER"
footer: "Example presentation with cards"
paginate: true
mermaid:
  theme: default
---
## Markdown → HTML Slides

Text before the cards

<!-- cards -->
<!-- card -->
### Card 1

- List item should be inside the card
- List item should be inside the card
<!-- /card -->

<!-- card -->
### Card 2

- List item should be inside the card
- List item should be inside the card
<!-- /card -->
<!-- /cards -->

Text After the cards

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
