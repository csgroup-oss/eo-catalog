# Contribute

Thank you for considering contributing to API-Key Manager!

## Report issues

Issue tracker: <https://github.com/csgroup-oss/eo-catalog/>

Please check that a similar issue does not already exist and include the
following information in your post:

- Describe what you expected to happen.
- If possible, include a [minimal reproducible
  example](https://stackoverflow.com/help/minimal-reproducible-example)
  to help us identify the issue. This also helps check that the issue
  is not with your own code.
- Describe what actually happened. Include the full traceback if there
  was an exception.
- List your Python and apikeymanager versions. If possible, check if this
  issue is already fixed in the latest releases or the latest code in
  the repository.

## Submit patches

If you intend to contribute to EO Catalog source code:

```bash
git clone https://github.com/csgroup-oss/eo-catalog.git
cd eo-catalog

# for eo_catalog.stac
python -m pip install "runtimes/eoapi/stac[dev]"
pre-commit install
```

We use `pre-commit` to run a suite of linters, formatters and pre-commit
hooks (`ruff`, `mypy`, `trailing-whitespace`) to ensure the code base is
homogeneously formatted and easier to read. It's important that you
install it, since we run the exact same hooks in the Continuous
Integration.

## Release of EO Catalog

<!-- TODO: explain the process of auto release with semantic release.  -->

### Create and publish the Docker image

<!-- TODO: explain how the docker image is automatically created by CI and available from github registry. -->
