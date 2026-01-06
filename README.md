# research-synth

Starter CLI tool for research synthesis.

## Dependency Note
This project pins `click==8.1.7` to avoid Typer/Click 8.2+ metavar signature incompatibilities.

## Optional format support

Base install supports .txt and .md.

Enable extras:
- PDF: `pip install -e '.[pdf]'`
- DOCX: `pip install -e '.[docx]'`
- Excel: `pip install -e '.[excel]'`
