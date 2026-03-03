#!/bin/bash

# OpenClaw Memory Backup Script
# Backups MEMORY.md and daily memory files to local backup directory

WORKSPACE="/home/admin/.openclaw/workspace"
LOCAL_BACKUP="$WORKSPACE/backup/local"

# Create backup directory if it doesn't exist
mkdir -p "$LOCAL_BACKUP"

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

# Backup MEMORY.md
backup_file "$WORKSPACE/MEMORY.md" "$LOCAL_BACKUP"

# Backup today's memory file
TODAY=$(date +%Y-%m-%d)
backup_file "$WORKSPACE/memory/$TODAY.md" "$LOCAL_BACKUP"

# Also backup yesterday's memory file
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
backup_file "$WORKSPACE/memory/$YESTERDAY.md" "$LOCAL_BACKUP"

echo "$(date): Memory backup completed"