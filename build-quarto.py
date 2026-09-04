"""Factory-only pre-render hook.

Iterates a small config of ``(view × chamber)`` tuples and emits every
generated ``.qmd`` file programmatically. Each generated page pulls
data via ``tok_preparer.src.data`` and plots via ``tok_plots``. No
``.ipynb`` intermediate representation; no ``.sqlite3`` at render time.

Hand-authored pages (``index.qmd``, ``about.qmd``) live directly in the
tree and are exempted from the ``*.qmd`` gitignore rule.
"""

from __future__ import annotations

from itertools import product
from pathlib import Path

HERE = Path(__file__).parent

AUTHORS_YAML = """authors:
  - name: Mathias Johansson
    email: MathiasJohansson@kultur.lu.se
    orcid: https://orcid.org/0000-0002-3338-0551
  - name: Ulrika Holgersson
    orcid: https://orcid.org/0000-0002-0672-6166
"""

WORD_CATS = [
    ("k1_matches", "kvinna 1"),
    ("k2_matches", "kvinna 2"),
    ("k3_matches", "kvinna 3"),
    ("k_all_matches", "kvinna_all"),
]
UTT_CATS = [
    ("k1_utts", "kvinna 1"),
    ("k2_utts", "kvinna 2"),
    ("k3_utts", "kvinna 3"),
    ("k_all_utts", "kvinna_all"),
]

VIEWS = {
    "word_baseline": {
        "reader_base": "read_word_frequencies",
        "kind": "baseline",
        "categories": WORD_CATS,
        "baseline_metrics": [("total_words", "total words")],
        "page_prefix": "ToK_word_baseline",
        "title_stem": "Word baseline",
    },
    "word_relative": {
        "reader_base": "read_word_frequencies",
        "kind": "relative",
        "categories": WORD_CATS,
        "baseline": "total_words",
        "page_prefix": "ToK_word_relative",
        "title_stem": "Relative word frequencies",
    },
    "utt_baseline": {
        "reader_base": "read_word_frequencies",
        "kind": "baseline",
        "categories": UTT_CATS,
        "baseline_metrics": [
            ("utterance_count", "utterances"),
            ("total_words", "words"),
            ("char_count", "characters"),
        ],
        "page_prefix": "ToK_baseline",
        "title_stem": "Baseline",
    },
    "utt_relative": {
        "reader_base": "read_word_frequencies",
        "kind": "relative",
        "categories": UTT_CATS,
        "baseline": "utterance_count",
        "page_prefix": "ToK_relative",
        "title_stem": "Relative utterance frequencies",
    },
    "speakers": {
        "reader_base": "read_speakers",
        "kind": "speakers",
        "categories": UTT_CATS,
        "page_prefix": "ToK_speakers",
        "title_stem": "Speakers",
    },
    "tracked_words": {
        "reader_base": "read_word_frequencies",
        "kind": "tracked_words",
        "word_cats": [("damer_matches", "damer"), ("fru_matches", "fru")],
        "utt_cats": [("damer_utts", "damer"), ("fru_utts", "fru")],
        "page_prefix": "ToK_damer_fru",
        "title_stem": "Greetings: damer & fru",
    },
}

CHAMBERS = (None, 1, 2)


def _reader_symbol(base: str, chamber: int | None) -> str:
    return base if chamber is None else f"{base}{chamber}"


def _page_stem(prefix: str, chamber: int | None) -> str:
    return prefix if chamber is None else f"{prefix}.chamber{chamber}"


def _chamber_suffix(chamber: int | None) -> str:
    return "" if chamber is None else f" -- Chamber {chamber}"


def _frontmatter(title: str) -> str:
    # Quote the title so colons, ``&``, and other YAML metacharacters survive.
    escaped = title.replace('"', '\\"')
    return (
        "---\n"
        f'title: "{escaped}"\n'
        "jupyter: tok\n"
        "execute:\n"
        "    echo: false\n"
        f"{AUTHORS_YAML}"
        "---\n\n"
    )


def _preamble(reader: str) -> str:
    return (
        "```{python}\n"
        f"from tok_preparer.src.data import {reader} as read_frame\n"
        "import tok_plots\n"
        "```\n\n"
        "```{python}\n"
        "df = read_frame()\n"
        "tok_plots.configure()\n"
        "```\n\n"
    )


def _cat_list_repr(categories: list[tuple[str, str]]) -> str:
    inner = ",\n    ".join(repr(pair) for pair in categories)
    return f"[\n    {inner},\n]"


def _render_baseline(cfg: dict) -> str:
    categories_repr = _cat_list_repr(cfg["categories"])
    metrics_repr = _cat_list_repr(cfg["baseline_metrics"])
    return f"""```{{python}}
CATEGORIES = {categories_repr}
METRICS = {metrics_repr}
```

## Absolute totals per year

```{{python}}
tok_plots.line_absolute(df, "year", METRICS, "Corpus totals per year")
```

## Category totals per year

```{{python}}
tok_plots.line_absolute(df, "year", CATEGORIES, "Category totals per year")
```

```{{python}}
tok_plots.line_absolute(df, "year", CATEGORIES, "Category totals per year (log scale)", log_y=True)
```

## Split by chamber

```{{python}}
for column, label in METRICS:
    tok_plots.line_absolute_per_group(df, "year", column, "chamber", f"{{label}} per year, by chamber")
```
"""


def _render_relative(cfg: dict) -> str:
    categories_repr = _cat_list_repr(cfg["categories"])
    baseline = cfg["baseline"]
    return f"""```{{python}}
CATEGORIES = {categories_repr}
BASELINE = {baseline!r}
```

## Category counts per year

```{{python}}
tok_plots.line_absolute(df, "year", [(BASELINE, "baseline")] + CATEGORIES, "Counting keywords by category")
```

## Relative frequencies per year

```{{python}}
tok_plots.line_relative(df, "year", CATEGORIES, BASELINE, "Relative keyword frequencies by category")
```

## Split by gender

```{{python}}
tok_plots.line_absolute_by_group(df, "year", CATEGORIES, "gender", "Counting keyword categories by gender")
```

```{{python}}
tok_plots.line_relative_by_group(df, "year", CATEGORIES, BASELINE, "gender", "Relative keyword frequencies by gender")
```

## Relative frequencies by party

```{{python}}
for column, label in CATEGORIES:
    tok_plots.line_per_group(df, "year", column, BASELINE, "party", f'Relative frequencies of "{{label}}" by party')
```
"""


def _render_speakers(cfg: dict) -> str:
    categories_repr = _cat_list_repr(cfg["categories"])
    return f"""```{{python}}
CATEGORIES = {categories_repr}
CATEGORY_LINES = [("*", "any speaker")] + [(col, label) for col, label in CATEGORIES]
```

## Distinct speakers per year

```{{python}}
tok_plots.line_distinct(df, "year", "who", CATEGORY_LINES, "Distinct speakers per year")
```

## Distinct speakers by gender

```{{python}}
tok_plots.line_distinct_by_group(df, "year", "who", "gender", "Distinct speakers per year, by gender")
```

```{{python}}
for column, label in CATEGORIES:
    tok_plots.line_distinct_by_group(
        df, "year", "who", "gender",
        f'Distinct speakers with "{{label}}" utterances, by gender',
        filter_col=column,
    )
```

## Distinct speakers by party

```{{python}}
tok_plots.line_distinct_by_group(df, "year", "who", "party", "Distinct speakers per year, by party")
```

```{{python}}
for column, label in CATEGORIES:
    tok_plots.line_distinct_by_group(
        df, "year", "who", "party",
        f'Distinct speakers with "{{label}}" utterances, by party',
        filter_col=column,
    )
```
"""


def _render_tracked_words(cfg: dict) -> str:
    word_cats_repr = _cat_list_repr(cfg["word_cats"])
    utt_cats_repr = _cat_list_repr(cfg["utt_cats"])
    return f"""```{{python}}
WORD_CATS = {word_cats_repr}
UTT_CATS = {utt_cats_repr}
VLINES = tok_plots.WOMEN_IN_CHAMBER_VLINES
```

## Raw word counts per year

```{{python}}
tok_plots.line_absolute(df, "year", WORD_CATS, "Raw word counts per year", vlines=VLINES)
```

## Utterances containing the word per year

```{{python}}
tok_plots.line_absolute(df, "year", UTT_CATS, "Utterances containing the word per year", vlines=VLINES)
```

## Relative frequency of utterances containing the word

```{{python}}
tok_plots.line_relative(df, "year", UTT_CATS, "utterance_count", "Share of utterances containing the word", vlines=VLINES)
```

## Split by speaker gender

```{{python}}
tok_plots.line_absolute_by_group(df, "year", UTT_CATS, "gender", "Utterances containing the word, by gender", vlines=VLINES)
```

```{{python}}
tok_plots.line_relative_by_group(df, "year", UTT_CATS, "utterance_count", "gender", "Share of utterances containing the word, by gender", vlines=VLINES)
```

## Split by party

```{{python}}
for column, label in UTT_CATS:
    tok_plots.line_per_group(df, "year", column, "utterance_count", "party", f'Share of utterances containing "{{label}}", by party', vlines=VLINES)
```

## Split by chamber

```{{python}}
for column, label in WORD_CATS:
    tok_plots.line_absolute_per_group(df, "year", column, "chamber", f'"{{label}}" per year, by chamber', vlines=VLINES)
```

```{{python}}
for column, label in UTT_CATS:
    tok_plots.line_absolute_per_group(df, "year", column, "chamber", f'Utterances containing "{{label}}" per year, by chamber', vlines=VLINES)
```
"""


RENDERERS = {
    "baseline": _render_baseline,
    "relative": _render_relative,
    "speakers": _render_speakers,
    "tracked_words": _render_tracked_words,
}


def emit_qmd(view_name: str, chamber: int | None) -> Path:
    cfg = VIEWS[view_name]
    reader = _reader_symbol(cfg["reader_base"], chamber)
    stem = _page_stem(cfg["page_prefix"], chamber)
    title = f'{cfg["title_stem"]}{_chamber_suffix(chamber)}'

    body = _frontmatter(title) + _preamble(reader) + RENDERERS[cfg["kind"]](cfg)

    out = HERE / f"{stem}.qmd"
    out.write_text(body)
    print(f"Factory wrote {out.name}")
    return out


# Public paper-figure functions in tok_preparer.src.plots. Hardcoded rather
# than introspected because the tok_preparer submodule pointer may lag the
# tok_preparer branch that actually defines these — this list needs a manual
# bump when a new plot_ function ships. Order = the order they appear in the
# emitted qmd.
PAPER_FIGURE_FUNCS: tuple[str, ...] = (
    "plot_baseline_corpus",
    "plot_keyword_coverage",
    "plot_keyword_coverage_by_pattern",
    "plot_keyword_shares_by_pattern",
    "plot_kvinna_net_composition",
    "plot_kvinna_all_by_chamber",
    "plot_category_composition",
    "plot_utterance_share_by_gender",
    "plot_word_share_by_gender",
    "plot_party_share",
    "plot_speaker_share_distribution",
    "plot_top_male_speakers",
    "plot_speaker_rate_vs_volume",
)


def emit_paper_figures_qmd() -> Path:
    """Emit ToK_paper_figures.qmd: one chunk per plot_ in tok_preparer.src.plots.

    Iterates :data:`PAPER_FIGURE_FUNCS` and writes one section per
    function, each calling it with defaults. This is the companion-
    site catch-all for the DHQ paper — it shows every experiment that
    was run, so the paper itself can carry only the pared-down subset.
    Split-per-function .qmds can come later; a single page is enough
    for now. Add a new plot_ function → add its name to
    ``PAPER_FIGURE_FUNCS``.
    """
    body_parts = [
        _frontmatter("Paper figures (all plot_ functions)"),
        "```{python}\n"
        "from tok_preparer.src import plots as tp_plots\n"
        "```\n\n",
    ]
    for func in PAPER_FIGURE_FUNCS:
        body_parts.append(f"## `{func}`\n\n")
        body_parts.append(f"```{{python}}\ntp_plots.{func}()\n```\n\n")

    out = HERE / "ToK_paper_figures.qmd"
    out.write_text("".join(body_parts))
    print(f"Factory wrote {out.name} ({len(PAPER_FIGURE_FUNCS)} plot functions)")
    return out


def main() -> None:
    for view_name, chamber in product(VIEWS, CHAMBERS):
        emit_qmd(view_name, chamber)
    emit_paper_figures_qmd()


if __name__ == "__main__":
    main()
