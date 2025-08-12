
### Installing
``` py -m pip install --upgrade build twine```

### Building
Update version in pyproject.toml if needed
```py -m build```

### Uploading
```py -m twine upload dist/*```

```py -m build; py -m twine upload dist/*```


### Running Locally
Install dependencies
```py -m pip install proto-schema-parser```

Run module with example
```python src/main.py examples/myl_vehicle.proto --build_c --build_ts --build_py```

The generated files will be placed in the `generated/` directory with subdirectories for each language (`c/`, `ts/`, `py/`).

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
