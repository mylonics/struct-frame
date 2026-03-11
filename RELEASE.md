# Release Process

This document describes how to release new versions of struct-frame to PyPI.

## Automated Release Pipeline

The release process has been consolidated into a streamlined workflow that requires **only one manual action** — triggering the "Bump Version" workflow. Everything else happens automatically.

### Workflows Overview

1. **`release.yml`** (Bump Version) — Manual workflow to bump version and trigger a release
   - **Trigger**: Manual (`workflow_dispatch`) on the `develop` branch
   - **Inputs**: `version_bump` — patch, minor, or major
   - **Actions**:
     - Bumps version in `pyproject.toml`
     - Auto-generates a `CHANGELOG.md` entry from git commit history since the last tag
     - Creates a PR to `develop` branch with auto-merge enabled (SQUASH)
     - Tags the PR title with `[release]` to signal downstream workflows

2. **`release-to-main.yml`** (Auto: Merge to Release Branch) — Automatic workflow triggered when the version bump PR merges
   - **Trigger**: PR merged to `develop` branch, or manual `workflow_dispatch`
   - **Actions**:
     - Detects `[release]` tag in the merged PR title
     - Directly rebases `develop` onto `main` (no PRs, no squash, no merge commits)
     - Skips if no `[release]` tag is found

3. **`publish.yml`** (Publish to PyPI) — Automatic workflow for publishing the package
   - **Trigger**: Push to `main` branch (with `pyproject.toml` changes)
   - **Actions**:
     - Creates and pushes a git tag
     - Builds the Python package (wheel and sdist)
     - Publishes to PyPI via OIDC trusted publishing
     - Creates a GitHub Release with release notes

### Release Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Developer triggers "Bump Version" workflow                   │
│    - Selects bump type (patch/minor/major)                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. release.yml workflow runs                                    │
│    - Bumps version in pyproject.toml                           │
│    - Generates CHANGELOG.md entry from git history             │
│    - Creates PR to develop branch                              │
│    - PR title: "feat: Bump version to X.Y.Z [release]"         │
│    - Auto-merge enabled (SQUASH)                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. PR auto-merges to develop (after CI passes)                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. release-to-main.yml workflow triggers                        │
│    - Detects [release] tag in PR title                         │
│    - Rebases develop directly onto main                        │
│    - No PRs, no squash, no merge commits                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Push to main triggers publish.yml                            │
│    - Creates git tag (vX.Y.Z)                                  │
│    - Builds Python package                                     │
│    - Publishes to PyPI                                         │
│    - Creates GitHub Release                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Prerequisites

Before using the automated release pipeline, you need to configure:

#### PyPI Trusted Publishing

1. Go to [PyPI](https://pypi.org/) and log in
2. Navigate to your project: https://pypi.org/manage/project/struct-frame/
3. Go to "Publishing" → "Add a new pending publisher"
4. Configure the trusted publisher with:
   - **PyPI Project Name**: `struct-frame`
   - **Owner**: `mylonics`
   - **Repository name**: `struct-frame`
   - **Workflow name**: `publish.yml`
   - **Environment name**: (leave blank)

This allows GitHub Actions to publish to PyPI using OIDC authentication, which is more secure than API tokens.

#### Required Secrets

The following secrets must be configured in the GitHub repository settings:

| Secret | Purpose |
|--------|---------|
| `PAT_GITHUB` | GitHub PAT with `repo` + `workflow` scopes. Required for auto-merge and to trigger downstream workflows (pushes with `GITHUB_TOKEN` do not trigger other workflows). |

#### Repository Settings

- **Enable "Allow auto-merge"** in repository settings (Settings → General → Pull Requests)
- **Branch protection rules** on `develop` should require at least one status check (the test suite) for auto-merge to work

### Running a Release

1. Navigate to the [Bump Version workflow](https://github.com/mylonics/struct-frame/actions/workflows/release.yml)
2. Click **"Run workflow"**
3. Select the branch: **`develop`**
4. Choose the version bump type:
   - **patch**: Bug fixes and minor changes (e.g., `0.0.50` → `0.0.51`)
   - **minor**: New features (e.g., `0.0.50` → `0.1.0`)
   - **major**: Breaking changes (e.g., `0.0.50` → `1.0.0`)
5. Click **"Run workflow"**

That's it! The rest happens automatically:
- PR is created and auto-merges after CI passes
- `develop` is rebased onto `main`
- Package is built and published to PyPI
- GitHub Release is created

### What Gets Published

The workflow builds and publishes:
- **Source distribution** (`.tar.gz`)
- **Wheel distribution** (`.whl`)

Both are uploaded to [PyPI](https://pypi.org/project/struct-frame/).

### Versioning Strategy

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version: Incompatible API changes
- **MINOR** version: New functionality in a backward-compatible manner
- **PATCH** version: Backward-compatible bug fixes

### Changelog Management

The `CHANGELOG.md` follows the [Keep a Changelog](https://keepachangelog.com/) format and is automatically generated using [git-changelog](https://github.com/pawamoy/git-changelog).

The workflow automatically:
1. Parses commit messages since the last release
2. Categorizes commits into sections (Added, Fixed, Changed, etc.) based on commit message prefixes
3. Generates a new version entry with:
   - Links to commits and comparisons
   - Organized sections based on conventional commits
   - Release date
4. Inserts the new entry at the `<!-- insertion marker -->` in the CHANGELOG.md

**Commit Message Conventions:**

For best results, use conventional commit prefixes:
- `feat:` or `add:` → Added section
- `fix:` → Fixed section  
- `change:` or `refactor:` → Changed section
- `remove:` or `delete:` → Removed section
- `docs:` → Documented section
- `merge:` → Merged section

**Example:**
```bash
git commit -m "feat: add new serialization feature"
git commit -m "fix: resolve buffer overflow in C parser"
```

The `[Unreleased]` section can be manually maintained for planned changes and will be preserved during releases.

## Manual Release (Alternative)

If you need to release manually without using the automated workflow:

### 1. Update Version

Edit `pyproject.toml` and update the version:
```toml
version = "0.0.51"
```

### 2. Update Changelog

Add a new section to `CHANGELOG.md`:
```markdown
## [0.0.51] - 2026-01-05

### Changed
- Description of changes
```

### 3. Commit Changes

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "Bump version to 0.0.51"
git push
```

### 4. Create Tag

```bash
git tag v0.0.51
git push origin v0.0.51
```

### 5. Build Package

```bash
python -m pip install --upgrade build
python -m build
```

### 6. Publish to PyPI

```bash
python -m pip install --upgrade twine
python -m twine upload dist/*
```

You'll need PyPI credentials (username/password or API token) for the manual upload.

## Troubleshooting

### Workflow Fails at PyPI Publish

If the workflow fails during the PyPI publish step:

1. **Check PyPI trusted publisher configuration**: Ensure the publisher is configured correctly on PyPI
2. **Check permissions**: The workflow needs `contents: write` and `id-token: write` permissions
3. **Check package name**: Ensure the package name in `pyproject.toml` matches the PyPI project name

### Version Already Exists

If you try to release a version that already exists on PyPI, the workflow will fail. You cannot overwrite existing versions on PyPI. You'll need to:

1. Choose a different version number
2. Manually update the tag if one was created
3. Run the workflow again with the new version

### Changelog Update Fails

If the changelog update step fails, it might be because:

1. The `CHANGELOG.md` format doesn't match the expected structure
2. There's no `[Unreleased]` section
3. The regex pattern needs adjustment

You can manually update the changelog and re-run the workflow, or manually create the release.

## Best Practices

1. **Test before release**: Ensure all tests pass before triggering a release
2. **Update changelog**: Keep the `[Unreleased]` section updated with meaningful changes
3. **Review changes**: Before running the release, review what's being released
4. **Monitor workflow**: Watch the workflow execution to ensure all steps complete successfully
5. **Verify PyPI**: After release, check [PyPI](https://pypi.org/project/struct-frame/) to confirm the new version is available
6. **Test installation**: Test installing the new version: `pip install struct-frame==X.Y.Z`

## Release Checklist

- [ ] All tests pass on develop branch
- [ ] CHANGELOG.md [Unreleased] section is up to date (optional — auto-generated from commits)
- [ ] Choose appropriate version bump (major/minor/patch)
- [ ] Run the "Bump Version" workflow on the `develop` branch
- [ ] Verify the PR was created and auto-merged to develop
- [ ] Verify develop was rebased onto main
- [ ] Verify the git tag was created
- [ ] Verify the new version appears on PyPI
- [ ] Test installing the new version: `pip install struct-frame==X.Y.Z`
