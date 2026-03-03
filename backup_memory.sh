#!/bin/bash

# OpenClaw Memory Backup Script
# Backups MEMORY.md and daily memory files to pCloud (with local fallback)

WORKSPACE="/home/admin/.openclaw/workspace"
PCLOUD_BACKUP="/home/admin/pCloudDrive/openclaw"
LOCAL_BACKUP="$WORKSPACE/backup/local"

# Create backup directories if they don't exist
mkdir -p "$LOCAL_BACKUP"
mkdir -p "$PCLOUD_BACKUP/memory" 2>/dev/null || echo "pCloudDrive not available, using local backup only"

# Function to backup file
backup_file() {
    local src="$1"
    local dest_dir="$2"
    local filename=$(basename "$src")
    
    if [ -f "$src" ]; then
        cp "$src" "$dest_dir/$filename"
        echo "$(date): Backed up $filename to $dest_dir"
    fi
}

echo "$(date): Starting memory backup..."

# Backup to local (always)
backup_file "$WORKSPACE/MEMORY.md" "$LOCAL_BACKUP"

# Backup today's memory file
TODAY=$(date +%Y-%m-%d)
backup_file "$WORKSPACE/memory/$TODAY.md" "$LOCAL_BACKUP"

# Also backup yesterday's memory file
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
backup_file "$WORKSPACE/memory/$YESTERDAY.md" "$LOCAL_BACKUP"

# Try to backup to pCloud if available
if [ -d "$PCLOUD_BACKUP" ] && [ -w "$PCLOUD_BACKUP" ]; then
    backup_file "$WORKSPACE/MEMORY.md" "$PCLOUD_BACKUP"
    backup_file "$WORKSPACE/memory/$TODAY.md" "$PCLOUD_BACKUP/memory"
    backup_file "$WORKSPACE/memory/$YESTERDAY.md" "$PCLOUD_BACKUP/memory"
    echo "$(date): pCloud backup completed"
else
    echo "$(date): pCloudDrive not available, local backup only"
fi

echo "$(date): Memory backup completed"