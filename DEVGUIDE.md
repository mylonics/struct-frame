
### Installing
``` py -m pip install --upgrade build twine```

### Building
Update version in pyproject.toml if needed
```py -m build```

### Uploading
```py -m twine upload dist/*```

```py -m build; py -m twine upload dist/*```


### Running Locally
```py .\src\main.py ```
