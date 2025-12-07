import subprocess
from pathlib import Path

here = Path(__file__).parent

index = here / "index.qmd"
subprocess.run(
    [
        "quarto",
        "convert",
        str(here / "ToK_exploration.ipynb"),
        "--output",
        str(index),
    ]
)

with open(index, "r", encoding="utf8") as f:
    lines = [
        line
        for line in f.readlines()
        if not line.startswith("#| colab:") and not line.startswith("#| executionInfo:")
    ]

with open(index, "w", encoding="utf8") as f:
    f.writelines(lines)

with open(index, "r", encoding="utf8") as f:
    content = f.read()

content = content.replace(
    "jupyter: tok\n",
    """jupyter: tok
execute:
  echo: false
author:
    - Mathias Johansson
    - Ulrika Holgersson
""",
)

with open(index, "w", encoding="utf8") as f:
    f.write(content)
