#!/bin/bash
# Check disk space and alert if below threshold

THRESHOLD=20
DISK_USAGE=$(df / | grep -vE '^Filesystem|tmpfs|cdrom' | awk '{print $5}' | sed 's/%//g')

echo "Current disk usage: ${DISK_USAGE}%"
echo "Threshold: ${THRESHOLD}%"

if [ "$DISK_USAGE" -ge "$((100 - THRESHOLD))" ]; then
    echo "⚠️ WARNING: Disk space is low!"
    echo "Only $((100 - DISK_USAGE))% remaining."
    echo "Consider archiving large files to pCloudDrive."
    exit 1
else
    echo "✅ Disk space is healthy."
    exit 0
fi
