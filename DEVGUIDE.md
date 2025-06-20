
### Installing
``` py -m pip install --upgrade build twine```

### Building
Update version in pyproject.toml if needed
```py -m build```

### Uploading
```py -m twine upload dist/*```

```py -m build; py -m twine upload dist/*```


### Running Locally
Install dependancies
```py -m pip install proto-schema-parser```

Run module
```py .\src\main.py ```
