# CUSTOM_FORK_WORKFLOW

## Repository layout

- origin: your private fork at https://github.com/hermanops/hermes-agent
- upstream: the canonical NousResearch/hermes-agent repository

## Remote meaning

- origin is the fork you push your custom work to
- upstream is the source you fetch and merge/rebase from

## Fetch upstream updates

```bash
git fetch upstream
git checkout main
git merge --ff-only upstream/main
```

## Merge or rebase onto upstream/main

Merge:

```bash
git checkout main
git merge upstream/main
git push origin main
```

Rebase:

```bash
git checkout main
git rebase upstream/main
git push --force-with-lease origin main
```

## Create future feature branches

```bash
git checkout main
git pull --ff-only origin main
git checkout -b feature/my-change
```

## Recommended maintenance workflow

1. Keep main aligned with upstream/main.
2. Branch from main for each customization.
3. Push feature branches to origin.
4. Open pull requests only within your private fork if desired.
5. Periodically fetch upstream and merge or rebase before starting new work.

## Example commands

```bash
git remote -v
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
git checkout -b feature/add-custom-routing
git push -u origin feature/add-custom-routing
```
