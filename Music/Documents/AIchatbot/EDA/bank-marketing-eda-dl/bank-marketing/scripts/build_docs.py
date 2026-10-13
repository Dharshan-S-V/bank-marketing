"""Write docs/*.md checklists from scripts/rubric.py:  python scripts/build_docs.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from rubric import REQUIREMENTS, RUBRIC  # noqa: E402

D = ROOT / "docs"; D.mkdir(exist_ok=True)
esc = lambda s: str(s).replace("|", "\\|")  # noqa: E731

r = ["# Requirements checklist (Phase 1)\n", "Source of truth: *Assignment II - Case Study with Rubrics* (U21ADP05). Each mandatory instruction is mapped to its implementation and validation.\n",
     "| Requirement from the assignment | Implementation | File / report section | Validation |", "|---|---|---|---|"]
r += [f"| {esc(a)} | {esc(b)} | {esc(c)} | {esc(d)} |" for a, b, c, d in REQUIREMENTS]
r += ["\n## Ambiguities and how they were resolved\n",
      "* **'All 7 stages of visualization'** - the assignment does not list them. The standard framework of Fry (2007) is used (acquire, parse, filter, mine, represent, refine, interact). If your lecturer teaches a different seven-stage list, say so in the report discussion; the mapping table (Table 13) is easy to relabel.",
      "* **Deep learning: mandatory or optional?** Step 4 of the task says 'apply at least one deep learning model', while the rubric lists ML/DL as an optional *enrichment component*. It is implemented in full either way.",
      "* **Statistical analysis (CO4)** is not itemised in the task steps but is a 16-mark rubric block; it is covered explicitly (Section 4 of the report).",
      "* **'Visualization tool'** - Python (Matplotlib, Seaborn, Plotly) is used, which the assignment allows."]
(D / "REQUIREMENTS_CHECKLIST.md").write_text("\n".join(r), encoding="utf-8")

m = ["# Rubric compliance matrix (40 marks)\n", "This matrix shows how each criterion is addressed. It does not guarantee a particular grade.\n",
     "| Requirement | Max marks | Implementation evidence | File / report section | Validation status | Remaining work |", "|---|---|---|---|---|---|"]
m += [f"| {esc(a)} | {b} | {esc(c)} | {esc(d)} | {esc(e)} | {esc(f)} |" for a, b, c, d, e, f in RUBRIC]
m.append(f"\nTotal available: {sum(x[1] for x in RUBRIC)} marks (CO3 8 + CO4 16 + CO5 16).")
(D / "RUBRIC_CHECKLIST.md").write_text("\n".join(m), encoding="utf-8")

s = """# Final submission checklist (deadline: 15 October 2026)

Nothing below has been done on your behalf - GitHub and the Google Form need your own accounts.

## A. Before publishing
- [ ] Open `reports/final_report.pdf`; confirm your **name, roll number and department** on the title page (department was taken as AIML - edit `scripts/build_report.py` if needed) and replace `<your-github-id>` with your GitHub username (re-run `python scripts/build_report.py`).
- [ ] Skim the report once; be ready to explain the findings, the leakage decision (duration) and why accuracy is not the headline metric.
- [ ] Verify the reference list (DOIs) on the publisher pages; Moro et al. (2014) and the UCI description were verified online while preparing the report.
- [ ] Optional: re-run `pytest -q` and `python scripts/run_all.py --skip-train` on your own machine.

## B. Create the GitHub repository (public, under your own ID)
```bash
cd bank-marketing-eda-dl
git init
git add .
git commit -m "EDA, statistical visualization and deep learning on the UCI Bank Marketing dataset"
git branch -M main
# Create an EMPTY public repository named bank-marketing-eda-dl on https://github.com/new (no README/licence), then:
git remote add origin https://github.com/<your-username>/bank-marketing-eda-dl.git
git push -u origin main
```
Alternative with the GitHub CLI (after `gh auth login`): `gh repo create bank-marketing-eda-dl --public --source=. --remote=origin --push`

## C. Verify
- [ ] The repository is **public** (open the link in a private/incognito window).
- [ ] README renders, `reports/final_report.pdf`, `notebooks/eda_and_modeling.ipynb` and `data/raw/bank-full.csv` are present.
- [ ] Optional fresh-clone test: clone into a new folder, `pip install -r requirements.txt`, `pytest -q`.

## D. Submit
- [ ] Paste the public repository link into the Google Form: https://forms.gle/kT9DU5aERo2peTNh8 (and/or email it to the course coordinator, as the assignment allows).
- [ ] Keep a screenshot of the form confirmation.
"""
(D / "SUBMISSION_CHECKLIST.md").write_text(s, encoding="utf-8")
print("docs written")
