
### Installing
``` py -m pip install --upgrade build twine```

### Building
Update version in pyproject.toml if needed
```py -m build```

### Uploading
```py -m twine upload dist/*```

```py -m build; py -m twine upload dist/*```


### Running Locally

#### For Development (from source)
Install dependencies
```py -m pip install proto-schema-parser```

Run module with example (using PYTHONPATH)
```PYTHONPATH=src python src/main.py examples/myl_vehicle.proto --build_c --build_ts --build_py --build_gql```

Or install in editable mode:
```pip install -e .```
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
