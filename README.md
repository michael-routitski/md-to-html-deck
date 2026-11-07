# Markdown Slide Compiler

Compile a Markdown presentation into a standalone HTML deck.

## Setup

Requires Python 3. The compiler dependencies are pinned in
`md-slide-compiler/requirements.txt` and installed into a local `.venv`:

```sh
./setup.sh
```

On Debian/Ubuntu, install the virtual-environment support first if needed:

```sh
sudo apt update
sudo apt install python3 python3-venv
```

## Compile

```sh
./compile-deck.sh samples/simple-test/presentation.md
```

The HTML output is written beside the Markdown input. The wrapper uses the
local `.venv` when it exists; otherwise, it uses `python3` from `PATH`.