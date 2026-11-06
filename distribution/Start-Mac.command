#!/bin/bash
cd -- "$(dirname -- "$0")" || exit 1
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3,9))' >/dev/null 2>&1; then
        "$candidate" -B launch.py "$@"
        result=$?
        if [ "$result" -ne 0 ]; then read -r -p 'Press Enter to close...' reply; fi
        exit "$result"
    fi
done
echo 'Python 3.9+ is required: https://www.python.org/downloads/'
read -r -p 'Press Enter to close...' reply
exit 1
