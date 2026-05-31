import subprocess
from pathlib import Path
import re

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
            str(notebook),
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
authors:
  - name: Mathias Johansson
    email: MathiasJohansson@kultur.lu.se
    orcid: https://orcid.org/0000-0002-3338-0551
  - name: Ulrika Holgersson
    orcid: https://orcid.org/0000-0002-0672-6166

""",
    )

    with open(out_file, "w", encoding="utf8") as f:
        f.write(content)

for qmd in here.glob("*.qmd"):
    if ".chamber" in qmd.name:
        continue
    elif qmd.name == "about.qmd":
        continue

    print("Chamberizing", qmd)
    if qmd.name == "index.qmd":
        out_base = "ToK_exploration"
    else:
        out_base = qmd.name.split(".")[0]

    raw_content = qmd.open().read()
    for chamber in {1, 2}:
        out_name = out_base + f".chamber{chamber}.qmd"
        out_file = qmd.parent / out_name

        out_content = raw_content.replace(
            "import tmp_db", f"import tmp_db{chamber} as tmp_db"
        )

        out_content = out_content.replace(
            "\njupyter: tok", f" -- Chamber {chamber}\njupyter: tok"
        )
        out_file.write_text(out_content)
        print("Wrote", out_name)
