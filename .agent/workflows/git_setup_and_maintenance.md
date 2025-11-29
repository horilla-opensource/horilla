---
description: How to manage a private SaaS fork of Horilla while keeping upstream updates.
---

# Git Workflow: Private SaaS Fork

This workflow explains how to maintain your own private repository for your SaaS product while keeping the ability to pull updates from the original Horilla open-source project.

## 1. Initial Setup (For Forked Repositories)

Since you have already forked the repository, your `origin` likely points to your fork. You just need to add the original Horilla repository as `upstream`.

### Steps:
1.  **Verify your remotes**:
    ```bash
    git remote -v
    # Should show your fork as 'origin'
    ```
2.  **Add the upstream remote** (Original Horilla Repo):
    ```bash
    git remote add upstream https://github.com/horilla-opensource/horilla.git
    ```
3.  **Verify again**:
    ```bash
    git remote -v
    # Should show:
    # origin   https://github.com/YOUR_USERNAME/horilla.git (fetch/push)
    # upstream https://github.com/horilla-opensource/horilla.git (fetch/push)
    ```

## 2. Daily Workflow (Working on your SaaS)

When you are building features, you work with `origin` as usual.

-   **Save changes**:
    ```bash
    git add .
    git commit -m "Built new feature"
    ```
-   **Push to your private repo**:
    ```bash
    git push origin main
    ```

## 3. Getting Future Updates from Horilla

When Horilla releases a new version or bug fix, you can pull it into your project.

### Steps:
1.  **Fetch the latest updates** from the open-source project:
    ```bash
    git fetch upstream
    ```
2.  **Merge updates** into your local branch:
    ```bash
    git merge upstream/master
    ```
    *(Note: Replace `master` with `main` if Horilla uses main)*

### Handling Conflicts
Since you have modified core files (like `views.py`, `models.py`), **merge conflicts are likely**.
-   Git will pause and tell you which files have conflicts.
-   Open those files, look for `<<<<<<< HEAD` markers.
-   Decide which code to keep (usually you want to keep YOUR SaaS logic while accepting THEIR bug fixes).
-   After resolving, run:
    ```bash
    git add .
    git commit -m "Merged upstream updates"
    ```
