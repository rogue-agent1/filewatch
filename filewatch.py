#!/usr/bin/env python3
"""filewatch — Watch files for changes and run commands.

Usage:
    filewatch "*.py" -- python test.py         Run tests on .py changes
    filewatch src/ -- make build                Rebuild on src/ changes
    filewatch file.txt                          Just report changes
    filewatch "*.md" --debounce 2 -- cmd        Debounce rapid changes
    filewatch . --ext .py,.js -- echo changed   Filter by extension
    filewatch . --ignore __pycache__,.git       Ignore patterns
"""

import argparse
import fnmatch
import hashlib
import os
import subprocess
import sys
import time


def hash_file(path):
    """Quick hash of file contents."""
    try:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, PermissionError):
        return None


def scan_path(path, extensions=None, ignore_patterns=None):
    """Scan path and return {filepath: (mtime, size)} dict."""
    state = {}
    ignore = ignore_patterns or []

    if os.path.isfile(path):
        state[path] = (os.path.getmtime(path), os.path.getsize(path))
        return state

    for root, dirs, files in os.walk(path):
        # Filter ignored dirs in-place
        dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, p) for p in ignore)]

        for f in files:
            if any(fnmatch.fnmatch(f, p) for p in ignore):
                continue
            if extensions and not any(f.endswith(ext) for ext in extensions):
                continue
            fp = os.path.join(root, f)
            try:
                st = os.stat(fp)
                state[fp] = (st.st_mtime, st.st_size)
            except (OSError, PermissionError):
                pass
    return state


def resolve_glob(pattern):
    """Resolve glob pattern to list of paths."""
    import glob
    matches = glob.glob(pattern, recursive=True)
    return matches if matches else [pattern]


def diff_states(old, new):
    """Find changes between two states."""
    changes = []
    all_paths = set(old) | set(new)
    for path in all_paths:
        if path not in old:
            changes.append(("added", path))
        elif path not in new:
            changes.append(("deleted", path))
        elif old[path] != new[path]:
            changes.append(("modified", path))
    return changes


def main():
    # Split args at --
    argv = sys.argv[1:]
    command = None
    if "--" in argv:
        idx = argv.index("--")
        command = argv[idx + 1:]
        argv = argv[:idx]

    parser = argparse.ArgumentParser(description="Watch files for changes")
    parser.add_argument("paths", nargs="+", help="Files, dirs, or glob patterns to watch")
    parser.add_argument("--debounce", type=float, default=0.5, help="Debounce seconds (default: 0.5)")
    parser.add_argument("--interval", type=float, default=1.0, help="Poll interval seconds")
    parser.add_argument("--ext", help="File extensions to watch (comma-sep, e.g., .py,.js)")
    parser.add_argument("--ignore", default="__pycache__,.git,node_modules,.venv,*.pyc",
                        help="Ignore patterns (comma-sep)")
    parser.add_argument("--clear", action="store_true", help="Clear screen before command")
    parser.add_argument("--once", action="store_true", help="Run command once on first change then exit")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress change details")
    args = parser.parse_args(argv)

    extensions = [e.strip() for e in args.ext.split(",")] if args.ext else None
    ignore = [p.strip() for p in args.ignore.split(",")]

    # Resolve all paths
    watch_paths = []
    for p in args.paths:
        watch_paths.extend(resolve_glob(p))

    if not watch_paths:
        print("Error: No valid paths to watch", file=sys.stderr)
        sys.exit(1)

    cmd_str = " ".join(command) if command else None
    print(f"👁  Watching {len(watch_paths)} path(s)" + (f" → {cmd_str}" if cmd_str else ""))
    if extensions:
        print(f"   Extensions: {', '.join(extensions)}")
    print(f"   Poll: {args.interval}s | Debounce: {args.debounce}s")
    print(f"   Press Ctrl+C to stop\n")

    # Initial scan
    state = {}
    for p in watch_paths:
        state.update(scan_path(p, extensions, ignore))

    print(f"   Tracking {len(state)} files\n")
    last_run = 0

    try:
        while True:
            time.sleep(args.interval)
            new_state = {}
            for p in watch_paths:
                new_state.update(scan_path(p, extensions, ignore))

            changes = diff_states(state, new_state)
            if changes and (time.time() - last_run) >= args.debounce:
                ts = time.strftime("%H:%M:%S")
                if not args.quiet:
                    icons = {"added": "🟢", "modified": "🟡", "deleted": "🔴"}
                    for kind, path in changes[:10]:
                        rel = os.path.relpath(path)
                        print(f"[{ts}] {icons.get(kind, '?')} {kind}: {rel}")
                    if len(changes) > 10:
                        print(f"[{ts}] ... and {len(changes) - 10} more")

                if command:
                    if args.clear:
                        os.system("clear")
                    print(f"[{ts}] ▶ {cmd_str}")
                    try:
                        result = subprocess.run(command, timeout=300)
                        code = result.returncode
                        icon = "✅" if code == 0 else "❌"
                        print(f"[{ts}] {icon} Exit code: {code}\n")
                    except subprocess.TimeoutExpired:
                        print(f"[{ts}] ⏰ Timeout (300s)\n")
                    except FileNotFoundError:
                        print(f"[{ts}] ❌ Command not found: {command[0]}\n")

                last_run = time.time()
                state = new_state

                if args.once:
                    break
            else:
                state = new_state

    except KeyboardInterrupt:
        print("\n👋 Stopped watching.")


if __name__ == "__main__":
    main()
