# Markdown to HTML Side Compiler

## Overview

Compile a Markdown presentation into a standalone HTML deck.

Slides are written in standard GitHub-Flavored Markdown with YAML frontmatter. 

Support for Cards:

Paired comment delimiters (`<!-- cards -->` / `<!-- /cards -->` and `<!-- card -->` / `<!-- /card -->`) can be used to structure card content while preserving natural document flow.

The important minimum markdown format requirements are 
- front matter contains custom theme, header/footer text and mermaid config for drawing diagrams.
- the ruler marker `---` acts as deck slide separator. 

To see what a basic sample output looks like, download and open `samples/simple-test/presentation.html` in the browser. Use arrows to go back and forward. It's produced from `samples/simple-test/presentation.md` source

## Detalied spec is avaiable

If you want to rebuild this is a different language, the full SPEC file is at `md-slide-compiler/SPEC.md`. 

The `tinycss2` is the python dependency however so this is something to be aware of - the `tinycss2` internals are not covered by the spec.

## Included skills

The skills folder has 3 skills for
- troubleshooting and making changes to the core code
- creting/updating themes to refine output deck appearence
- creating source content markdown in the right format

## Setup

Requires Python 3. The compiler dependencies are pinned in
`md-slide-compiler/requirements.txt` and installed into a local `.venv`:

```sh
./setup.sh
```

On Debian Linux, install the virtual-environment support first if needed:

```sh
sudo apt update
sudo apt install python3 python3-venv
```

Other distros/mac should be same package different manager

On windows try choco or winget or ask your friendly assistant
and you might want to port `compile-deck.sh` to powershell

## How to use

```sh
./compile-deck.sh samples/simple-test/presentation.md
```

The HTML output is written beside the Markdown input. The wrapper uses the
local `.venv` when it exists; otherwise, it uses `python3` from `PATH`.
