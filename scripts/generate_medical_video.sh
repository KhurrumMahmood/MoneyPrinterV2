#!/bin/bash
# Generate a medical documentary video from end to end using AI Agents.
# Usage: bash scripts/generate_medical_video.sh <"Topic"> <project_id>
# Example: bash scripts/generate_medical_video.sh "The Magnesium Sleep Connection" magnesium-poc

set -e

TOPIC="$1"
PROJECT_ID="$2"

if [ -z "$TOPIC" ] || [ -z "$PROJECT_ID" ]; then
    echo "Usage: $0 \"<Topic>\" <project_id>"
    echo "Example: $0 \"The Magnesium Sleep Connection\" magnesium-poc"
    exit 1
fi

echo "========================================"
echo " Starting Generation Pipeline"
echo " Topic: $TOPIC"
echo " ID:    $PROJECT_ID"
echo "========================================"

# 1. Script Generation
echo "[1/3] Running Script Agent..."
python3 src/agents/script_agent.py --topic "$TOPIC" --id "$PROJECT_ID"

# 2. Asset Generation
echo ""
echo "[2/3] Running Asset Agent..."
python3 src/agents/asset_agent.py --id "$PROJECT_ID"

# 3. Render
echo ""
echo "[3/3] Running Remotion Render..."
mkdir -p output
cd remotion

# Render using the dynamic ID
npx tsx render.ts "$PROJECT_ID/spec.json" "../output/$PROJECT_ID.mp4"

echo ""
echo "========================================"
echo " Pipeline Complete!"
echo " Output Video: output/$PROJECT_ID.mp4"
echo "========================================"
