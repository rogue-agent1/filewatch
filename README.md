# filewatch

Watch files for changes and run commands. Like `entr` or `fswatch` but pure Python, zero dependencies.

## Usage

```bash
# Run tests when Python files change
filewatch "*.py" -- python -m pytest

# Rebuild on source changes
filewatch src/ -- make build

# Just report changes
filewatch .

# Filter by extension
filewatch . --ext .py,.js -- echo "code changed"

# Debounce rapid saves
filewatch . --debounce 2 -- npm run build

# Clear screen before each run
filewatch "*.go" --clear -- go test ./...

# Run once on first change then exit
filewatch config.yaml --once -- systemctl reload nginx
```

## Features

- **Glob patterns** — `"*.py"`, `src/**`, specific files
- **Command execution** — anything after `--`
- **Extension filter** — `--ext .py,.js,.ts`
- **Smart ignore** — `__pycache__`, `.git`, `node_modules` by default
- **Debounce** — prevents rapid re-runs on burst saves
- **Clear screen** — `--clear` for clean output each run
- **Exit codes** — shows ✅/❌ after each command run
- **Zero dependencies**

## License

MIT
