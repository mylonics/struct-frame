# Git Submodules in struct-frame

This repository uses git submodules for external dependencies.

## ASIO Submodule

The ASIO (Asynchronous I/O) library is included as a git submodule for C++ network transport support.

### Location

- **Submodule path**: `src/struct_frame/boilerplate/cpp/struct_frame_sdk/asio-repo`
- **Symlink**: `src/struct_frame/boilerplate/cpp/struct_frame_sdk/asio` → `asio-repo/asio/include/asio`
- **Repository**: https://github.com/chriskohlhoff/asio.git
- **Version**: asio-1-30-2 (1.30.2)

### Cloning the Repository

When cloning this repository, initialize submodules to get the ASIO library:

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/mylonics/struct-frame.git

# Or if already cloned
git submodule update --init --recursive
```

### Building the Pip Package

When building the pip package, the ASIO headers are automatically included via the configuration in `pyproject.toml`:

```toml
[tool.hatch.build.targets.sdist.force-include]
"src/struct_frame/boilerplate" = "src/struct_frame/boilerplate"
"src/struct_frame/boilerplate/cpp/struct_frame_sdk/asio-repo/asio/include/asio" = "src/struct_frame/boilerplate/cpp/struct_frame_sdk/asio-repo/asio/include/asio"
```

### Updating ASIO

To update the ASIO version:

```bash
cd src/struct_frame/boilerplate/cpp/struct_frame_sdk/asio-repo
git fetch --tags
git checkout <new-version-tag>
cd ../../../../..
git add src/struct_frame/boilerplate/cpp/struct_frame_sdk/asio-repo
git commit -m "Update ASIO to <new-version>"
```

Update the `.gitmodules` file to point to the new branch/tag if needed.

## Other Submodules

### MkDocs Theme

- **Submodule path**: `docs/theme_overrides`
- **Repository**: https://github.com/mylonics/mylonics-mkdocs-theme
