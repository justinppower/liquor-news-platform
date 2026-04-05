#!/bin/bash
# Health Check: Validate all config files exist and are valid JSON
# Usage: bash scripts/check-config.sh

CONFIG_DIR="../config"
ERRORS=0

echo "=== Config Health Check ==="
echo ""

for file in site.config.json rss-feeds.json content-pillars.json ad-slots.json; do
    filepath="$CONFIG_DIR/$file"
    if [ -f "$filepath" ]; then
        if python3 -c "import json; json.load(open('$filepath'))" 2>/dev/null; then
            echo "[OK] $file - valid JSON"
        else
            echo "[!!] $file - INVALID JSON"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo "[!!] $file - FILE MISSING"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "All config files valid."
    exit 0
else
    echo "$ERRORS error(s) found."
    exit 1
fi
