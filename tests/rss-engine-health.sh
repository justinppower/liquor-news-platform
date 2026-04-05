#!/usr/bin/env bash
# RSS Engine Health Check
# Tests that the RSS fetch pipeline is functional end-to-end.
# Run from repo root: bash tests/rss-engine-health.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

pass() { echo -e "  ${GREEN}PASS${NC} $1"; PASS=$((PASS+1)); }
fail() { echo -e "  ${RED}FAIL${NC} $1"; FAIL=$((FAIL+1)); }
warn() { echo -e "  ${YELLOW}WARN${NC} $1"; WARN=$((WARN+1)); }

echo "==============================="
echo "  RSS Engine Health Check"
echo "  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "==============================="
echo ""

# 1. Check dependencies
echo "[1/6] Python dependencies"
python3 -c "import feedparser" 2>/dev/null && pass "feedparser installed" || fail "feedparser not installed"
python3 -c "from dateutil import parser" 2>/dev/null && pass "python-dateutil installed" || warn "python-dateutil missing (dates will use fallback)"

# 2. Check config files exist
echo "[2/6] Configuration files"
[ -f config/rss-feeds.json ] && pass "rss-feeds.json exists" || fail "rss-feeds.json missing"
[ -f config/site.config.json ] && pass "site.config.json exists" || fail "site.config.json missing"

# 3. Check config is valid JSON
echo "[3/6] Config validation"
python3 -c "import json; json.load(open('config/rss-feeds.json'))" 2>/dev/null && pass "rss-feeds.json is valid JSON" || fail "rss-feeds.json is invalid JSON"
python3 -c "import json; json.load(open('config/site.config.json'))" 2>/dev/null && pass "site.config.json is valid JSON" || fail "site.config.json is invalid JSON"

# 4. Validate feeds (quick check)
echo "[4/6] Feed validation (live check)"
FEED_RESULT=$(python3 site/scripts/rss-fetch.py --validate-feeds 2>&1 | tail -1)
OPERATIONAL=$(echo "$FEED_RESULT" | grep -oP '\d+(?=/)')
TOTAL=$(echo "$FEED_RESULT" | grep -oP '(?<=/)\d+')

if [ -n "$OPERATIONAL" ] && [ "$OPERATIONAL" -ge 10 ]; then
    pass "$OPERATIONAL/$TOTAL feeds operational"
elif [ -n "$OPERATIONAL" ] && [ "$OPERATIONAL" -ge 5 ]; then
    warn "$OPERATIONAL/$TOTAL feeds operational (degraded)"
else
    fail "${OPERATIONAL:-0}/${TOTAL:-?} feeds operational (critical)"
fi

# 5. Dry run test
echo "[5/6] Dry run fetch"
DRY_RESULT=$(python3 site/scripts/rss-fetch.py --dry-run 2>&1 | grep "New articles" | grep -oP 'New articles: \K\d+')
NEW_COUNT="$DRY_RESULT"
if [ -n "$NEW_COUNT" ] && [ "$NEW_COUNT" -ge 0 ]; then
    pass "Dry run completed ($NEW_COUNT articles would be created)"
else
    fail "Dry run failed"
fi

# 6. Check queue directory
echo "[6/6] Content queue"
QUEUE_DIR="site/content/queue"
if [ -d "$QUEUE_DIR" ]; then
    QUEUE_COUNT=$(ls -1 "$QUEUE_DIR"/*.md 2>/dev/null | wc -l)
    pass "Queue directory exists ($QUEUE_COUNT articles)"
else
    warn "Queue directory does not exist yet (will be created on first fetch)"
fi

# 7. Check workflow file
echo ""
echo "[Bonus] GitHub Actions workflow"
[ -f .github/workflows/rss-fetch.yml ] && pass "rss-fetch.yml workflow exists" || fail "rss-fetch.yml missing"

# Summary
echo ""
echo "==============================="
echo "  Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}, ${YELLOW}${WARN} warnings${NC}"
echo "==============================="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
