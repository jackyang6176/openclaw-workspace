#!/bin/bash
# Archive old memory files to pCloudDrive
# Keep last 3 days on local host

MEMORY_DIR="/home/admin/.openclaw/workspace/memory"
PCLOUD_DIR="/home/admin/pCloudDrive/openclaw/memory"
RETENTION_DAYS=3

echo "=== Memory Archive Script ==="
echo "Date: $(date)"
echo ""

# Create pCloud directory if not exists
mkdir -p "$PCLOUD_DIR"

# Find files older than retention days
find "$MEMORY_DIR" -name "*.md" -type f -mtime +$RETENTION_DAYS | while read file; do
    filename=$(basename "$file")
    echo "Archiving: $filename"
    
    # Copy to pCloud
    if cp "$file" "$PCLOUD_DIR/"; then
        # Remove from local if copy successful
        rm "$file"
        echo "  ✓ Moved to pCloudDrive"
    else
        echo "  ✗ Copy failed, keeping local copy"
    fi
done

echo ""
echo "=== Archive Complete ==="
echo "Local files remaining: $(ls $MEMORY_DIR/*.md 2>/dev/null | wc -l)"
echo "Archived files in pCloud: $(ls $PCLOUD_DIR/*.md 2>/dev/null | wc -l)"
