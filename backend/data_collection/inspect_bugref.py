import pandas as pd

df = pd.read_csv("data/dataset.csv")
u = df[df.label_window_complete & ~df.is_revert_pr]
titles = df.set_index(["repo", "number"]).title

br = u[u.label_bug_ref]
print(f"{len(br)} bug_ref-labeled PRs\n")
br = br.sample(min(15, len(br)), random_state=0)
for _, r in br.iterrows():
    fix = titles.get((r.repo, int(r.bugref_pr)))
    print(f"{r.repo}#{r.number}: {r.title}\n   -> ref'd by #{int(r.bugref_pr)}: {fix}\n")