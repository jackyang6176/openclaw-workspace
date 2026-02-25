#!/bin/bash

# OpenClaw Memory Backup Script
# Backups MEMORY.md and daily memory files to pCloud

WORKSPACE="/home/admin/.openclaw/workspace"
PCLOUD_BACKUP="/home/admin/pCloudDrive/openclaw"

# Create backup directory if it doesn't exist
mkdir -p "$PCLOUD_BACKUP/memory"

# Backup MEMORY.md if it exists
if [ -f "$WORKSPACE/MEMORY.md" ]; then
    cp "$WORKSPACE/MEMORY.md" "$PCLOUD_BACKUP/MEMORY.md"
    echo "$(date): Backed up MEMORY.md"
fi

# Backup today's memory file if it exists
TODAY=$(date +%Y-%m-%d)
if [ -f "$WORKSPACE/memory/$TODAY.md" ]; then
    cp "$WORKSPACE/memory/$TODAY.md" "$PCLOUD_BACKUP/memory/$TODAY.md"
    echo "$(date): Backed up memory/$TODAY.md"
fi

# Also backup yesterday's memory file
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
if [ -f "$WORKSPACE/memory/$YESTERDAY.md" ]; then
    cp "$WORKSPACE/memory/$YESTERDAY.md" "$PCLOUD_BACKUP/memory/$YESTERDAY.md"
    echo "$(date): Backed up memory/$YESTERDAY.md"
fi

echo "$(date): Memory backup completed"