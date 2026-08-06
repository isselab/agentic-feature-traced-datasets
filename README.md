# Agentic feature-traced datasets

This repository is a reference repository for Agent-HAnS evaluation datasets.

## Datasets

<!-- DATASETS:START -->
| Dataset | Repository | Local path |
|---|---|---|
| `datasets/dataset-TestRepo` | [https://github.com/isselab/dataset-TestRepo](https://github.com/isselab/dataset-TestRepo) | `datasets/dataset-TestRepo` |
<!-- DATASETS:END -->

## Clone the collection

Clone all registered datasets:

```bash
git clone --recurse-submodules https://github.com/isselab/agentic-feature-traced-datasets.git
cd agentic-feature-traced-datasets
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

Pull catalog changes and make checked-out submodules match the commits pinned
by the catalog:

```bash
git pull --recurse-submodules
git submodule update --init --recursive
```

## Add a dataset

The preferred path is to create a repository from
[`isselab/agentic-dataset-template`](https://github.com/isselab/agentic-dataset-template).
Its bootstrap workflow opens a pull request here. See
[CONTRIBUTING.md](CONTRIBUTING.md) for requirements and the manual fallback.

Do not place benchmark files directly in this repository. A directory under
`datasets/` is a submodule checkout, not an ordinary tracked directory.

## Work with submodules

Inspect pinned and checked-out states:

```bash
git submodule status
```

Update one local checkout to its remote `main`, then record the new pointer in
the parent:

```bash
git -C datasets/<name> switch main
git -C datasets/<name> pull --ff-only origin main
git add datasets/<name>
git commit -m "Update <name> dataset"
```

Update every local checkout to the configured remote branch:

```bash
git submodule update --remote
```

This changes local submodule checkouts. Commit the intended pointer changes in
this parent repository after reviewing them.

## Validate

```bash
git submodule update --init --recursive
python scripts/render_catalog.py --check
```

## License

The aggregation and its governance files are licensed under the
[MIT License](LICENSE). Each submodule is an independent work and may have
different license terms. Consult the `LICENSE` and `dataset.json` inside each
dataset before using its initial code, prompts, or annotations.
