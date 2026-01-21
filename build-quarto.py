import subprocess
from pathlib import Path

here = Path(__file__).parent

for notebook in here.glob("*.ipynb"):
    if notebook.name == "ToK_exploration.ipynb":
        out_file = here / "index.qmd"
    else:
        out_file = here / f"{notebook.stem}.qmd"

    subprocess.run(
        [
            "quarto",
            "convert",
            str(here / "ToK_exploration.ipynb"),
            "--output",
            str(out_file),
        ]
    )

    with open(out_file, "r", encoding="utf8") as f:
        lines = [
            line
            for line in f.readlines()
            if not line.startswith("#| colab:")
            and not line.startswith("#| executionInfo:")
        ]

    with open(out_file, "w", encoding="utf8") as f:
        f.writelines(lines)

    with open(out_file, "r", encoding="utf8") as f:
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

    with open(out_file, "w", encoding="utf8") as f:
        f.write(content)
