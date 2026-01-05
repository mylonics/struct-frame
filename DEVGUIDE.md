
### Release Process (Automated)

The repository now has an automated release pipeline that handles version bumping, changelog updates, git tagging, and PyPI publishing.

**To create a new release:**

1. Navigate to the [Actions tab](https://github.com/mylonics/struct-frame/actions/workflows/release.yml) in GitHub
2. Click "Run workflow"
3. Select the version bump type:
   - **patch**: Bug fixes and minor changes (e.g., 0.0.50 → 0.0.51)
   - **minor**: New features (e.g., 0.0.50 → 0.1.0)
   - **major**: Breaking changes (e.g., 0.0.50 → 1.0.0)
4. Click "Run workflow"

The pipeline will automatically:
- Update the version in `pyproject.toml`
- Add a new entry to `CHANGELOG.md`
- Create a git tag (e.g., `v0.0.51`)
- Build the Python package
- Publish to PyPI

**Note:** This workflow requires PyPI trusted publisher to be configured on PyPI.org (not GitHub secrets). See RELEASE.md for setup instructions.

### Manual Release (Legacy)

If you need to release manually:

#### Installing
``` py -m pip install --upgrade build twine```

#### Building
Update version in pyproject.toml if needed
```py -m build```

#### Uploading
```py -m twine upload dist/*```

```py -m build; py -m twine upload dist/*```


### Running Locally

#### For Development (from source)
Install dependencies:

```py -m pip install proto-schema-parser```

Run module with example (using PYTHONPATH):

```PYTHONPATH=src python src/main.py examples/myl_vehicle.proto --build_c --build_ts --build_py --build_gql```

Or install in editable mode:

```pip install -e .```

Then run the code generator:

```python -m struct_frame examples/myl_vehicle.proto --build_c --build_ts --build_py --build_gql```

#### For Users (from pip)
Install the package:
```pip install struct-frame```

Run the code generator:
```python -m struct_frame examples/myl_vehicle.proto --build_c --build_ts --build_py --build_gql```

The generated files will be placed in the `generated/` directory with subdirectories for each language (`c/`, `ts/`, `py/`, `gql/`). GraphQL schemas are written with a `.graphql` extension.

### Testing Examples
After generating code, you can test the examples:

TypeScript:
```bash
npx tsc examples/index.ts --outDir generated/
node generated/examples/index.js
```

C:
```bash
gcc examples/main.c -I generated/c -o main
./main
```
