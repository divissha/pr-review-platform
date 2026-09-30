import pandas as pd

df = pd.read_csv("data/dataset.csv")
u = df[df.label_window_complete & ~df.is_revert_pr]
titles = df.set_index(["repo", "number"]).title

hot = u[u.label_hotfix]
print(f"{len(hot)} hotfix-labeled PRs\n")
hot = hot.sample(min(15, len(hot)), random_state=0)
for _, r in hot.iterrows():
    fix = titles.get((r.repo, int(r.hotfix_pr)))
    print(f"{r.repo}#{r.number}: {r.title}\n   -> fix #{int(r.hotfix_pr)}: {fix}\n")