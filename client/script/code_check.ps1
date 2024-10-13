$root_path = (Resolve-Path ..).path;
Set-Location $root_path
black --check --verbose --config ./pyproject.toml ./
flake8 --verbose --config=./flake8.cfg ./