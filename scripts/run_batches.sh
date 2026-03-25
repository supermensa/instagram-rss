#!/bin/bash
# Automatisk batch-kørsel af Instagram RSS generator
# Kører alle profiler i batches med pauser imellem
# Genoptager automatisk hvor den slap

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ─── KONFIGURATION ───────────────────────────────────────────────
BATCH_SIZE=50           # Hvor mange profiler per batch
PAUSE_MINUTES=15        # Hvor mange minutters pause mellem batches
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
SCRIPT="$PROJECT_ROOT/instagram_rss.py"
PROFILER_FIL="$PROJECT_ROOT/profiler.txt"
CACHE_FIL="$PROJECT_ROOT/posts_cache.json"
OUTPUT_FIL="public/instagram.xml"
# ─────────────────────────────────────────────────────────────────

cd "$PROJECT_ROOT"

echo "🚀 Instagram RSS Batch Runner"
echo "═══════════════════════════════════════════════════════"

# Læs totalt antal profiler fra filen
TOTAL_PROFILES=$(wc -l < "$PROFILER_FIL" | tr -d ' ')
echo "📋 Total profiler:  $TOTAL_PROFILES"

# Tjek hvor langt vi er kommet
if [ -f "$CACHE_FIL" ]; then
    CACHED_PROFILES=$($PYTHON_BIN -c "import json; cache=json.load(open('$CACHE_FIL')); print(len(cache.get('posts', {})))" 2>/dev/null || echo "0")
    TOTAL_POSTS=$($PYTHON_BIN -c "import json; cache=json.load(open('$CACHE_FIL')); print(sum(len(p) for p in cache.get('posts', {}).values()))" 2>/dev/null || echo "0")
    echo "💾 Cache fundet:    $CACHED_PROFILES profiler, $TOTAL_POSTS posts"

    # Find første profil der ikke er i cache
    START_FROM=$CACHED_PROFILES
else
    echo "🆕 Ingen cache fundet - starter fra begyndelsen"
    START_FROM=0
    CACHED_PROFILES=0
fi

echo "🎯 Starter fra:     Profil #$START_FROM"
echo "Batch størrelse:    $BATCH_SIZE profiler"
echo "Pause mellem batch: $PAUSE_MINUTES minutter"
echo "═══════════════════════════════════════════════════════"
echo ""

# Beregn resterende profiler og batches
REMAINING=$(($TOTAL_PROFILES - $START_FROM))
if [ $REMAINING -le 0 ]; then
    echo "✅ Alle profiler er allerede hentet!"
    echo ""
    echo "For at opdatere med nye posts, kør:"
    echo "  $PYTHON_BIN $SCRIPT"
    exit 0
fi

BATCHES=$(( ($REMAINING + $BATCH_SIZE - 1) / $BATCH_SIZE ))
echo "📦 $REMAINING profiler tilbage → $BATCHES batches"
echo ""

read -p "⚠️  VIGTIGT: Er VPN slået FRA? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Slå VPN fra først!"
    exit 1
fi

echo ""
START_TIME=$(date +%s)
batch_num=1

for ((start=START_FROM; start<TOTAL_PROFILES; start+=BATCH_SIZE)); do
    end=$((start + BATCH_SIZE))
    if [ $end -gt $TOTAL_PROFILES ]; then
        end=$TOTAL_PROFILES
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 Batch $batch_num/$BATCHES: Profiler $start-$((end-1))"
    PROGRESS=$(( ($start * 100) / $TOTAL_PROFILES ))
    echo "📊 Samlet fremskridt: $PROGRESS% ($start/$TOTAL_PROFILES profiler)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⏰ Startet: $(date '+%H:%M:%S')"
    echo ""

    # Kør batch
    "$PYTHON_BIN" "$SCRIPT" $start $end
    EXIT_CODE=$?

    if [ $EXIT_CODE -ne 0 ]; then
        echo ""
        echo "⚠️  Batch fejlede med exit code $EXIT_CODE"
        echo "💾 Fremskridt er gemt i cache - kan fortsætte senere"
        echo ""
        read -p "Vil du fortsætte med næste batch? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "🛑 Stoppet af bruger"
            exit 1
        fi
    fi

    echo ""
    echo "✅ Batch $batch_num færdig kl. $(date '+%H:%M:%S')"

    # Pause før næste batch (undtagen efter sidste)
    if [ $end -lt $TOTAL_PROFILES ]; then
        echo ""
        echo "💤 Pauser i $PAUSE_MINUTES minutter før næste batch..."
        echo "   (Ctrl+C for at stoppe)"

        # Countdown
        for ((i=PAUSE_MINUTES; i>0; i--)); do
            echo -ne "   ⏳ $i minutter tilbage...\r"
            sleep 60
        done
        echo -ne "\n"
        echo "⚡ Fortsætter..."
        echo ""
    fi

    ((batch_num++))
done

END_TIME=$(date +%s)
DURATION=$(( (END_TIME - START_TIME) / 60 ))

# Læs final statistik
FINAL_PROFILES=$($PYTHON_BIN -c "import json; cache=json.load(open('$CACHE_FIL')); print(len(cache.get('posts', {})))" 2>/dev/null || echo "?")
FINAL_POSTS=$($PYTHON_BIN -c "import json; cache=json.load(open('$CACHE_FIL')); print(sum(len(p) for p in cache.get('posts', {}).values()))" 2>/dev/null || echo "?")

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 ALLE BATCHES FÆRDIGE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏱️  Køretid denne session: $DURATION minutter"
echo "📊 Profiler i cache: $FINAL_PROFILES/$TOTAL_PROFILES"
echo "📝 Total posts: $FINAL_POSTS"
echo "📁 RSS fil: $OUTPUT_FIL"
echo "💾 Cache fil: posts_cache.json"
echo ""
echo "✅ Åbn $OUTPUT_FIL i din RSS-læser!"
echo ""