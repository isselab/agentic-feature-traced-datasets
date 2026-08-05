# Contributing a dataset

## Preferred: create from the template

1. In **Organization settings -> Secrets and variables -> Actions**, ensure the
   `PARENT_REPO_PAT` organization secret exists. For zero-touch creation, give
   it access to **All repositories**. For tighter access, select each generated
   repository after creation and rerun its **Sync parent submodule pointer**
   workflow.
2. Open
   [`isselab/agentic-dataset-template`](https://github.com/isselab/agentic-dataset-template)
   and select **Use this template → Create a new repository**.
3. Create the repository in `isselab` as **public**, with a unique name
   containing only letters, digits, periods, underscores, and hyphens.
   `isselab` uses GitHub Free, which does not make organization Actions secrets
   available to private repositories. A private dataset instead requires a
   repository-level `PARENT_REPO_PAT` secret or GitHub Team.
4. Wait for **Bootstrap dataset repository** and **Sync parent submodule
   pointer** to finish.
5. Review its pull request in this repository and merge it after catalog
   validation succeeds.
6. Replace the initial project, evolution-step skeleton, prompts, ground truth,
   and manual implementation oracle in the dataset repository. Future pushes
   to its `main` branch open pointer-update pull requests here.

GitHub does not copy Actions secrets from a template. `PARENT_REPO_PAT` should
therefore be an organization-level Actions secret made available to the
generated repository. It should be an organization-approved fine-grained token
with resource owner `isselab`, restricted to this parent repository with
**Contents: read and write** and **Pull requests: read and write**.

## Manual fallback

From a clean checkout of this parent:

```bash
git checkout -b add/<dataset-name>
git submodule add https://github.com/isselab/<dataset-name>.git datasets/<dataset-name>
python scripts/render_catalog.py
git add .gitmodules README.md datasets/<dataset-name>
git commit -m "Add <dataset-name> dataset"
git push --set-upstream origin add/<dataset-name>
```

Then open a pull request. A dataset is accepted only when:

- its repository URL uses HTTPS and its path is `datasets/<repository-name>`;
- it contains a valid schema-v2 `dataset.json`, initial subject project,
  ordered evolution steps, exact prompts, ground truth, and implementation
  oracles;
- `python scripts/validate_dataset.py` passes inside the dataset;
- its scope, provenance, feature/annotation formats, limitations, and licensing
  are adequately described;
- ground truth is kept separate from the project supplied to Agent-HAnS;
- generated Agent-HAnS outputs and evaluation runs are not committed as part
  of the reusable benchmark;
- the parent commit intentionally pins the reviewed dataset commit.

## Review policy

Submodule additions and updates enter through pull requests. Reviewers should
inspect the linked dataset commit, not only the small gitlink diff shown in the
parent pull request. Protect `main` and require the **Validate catalog** check.
