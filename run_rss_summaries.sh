#!/bin/bash

# RSS News Aggregator - Automated Summary Script
# Runs daily at 9 AM and 6 PM

# Set up the environment
cd /Users/svaug/dev/svl_apps/news_aggregator

# Activate the virtual environment
source /Users/svaug/dev/virtual_environments/svl_dev/bin/activate

# Create logs directory if it doesn't exist
mkdir -p logs

# Get current timestamp for logging
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOGFILE="logs/rss_summary_${TIMESTAMP}.log"

echo "Starting RSS summaries at $(date)" | tee -a "$LOGFILE"
echo "================================================" | tee -a "$LOGFILE"

# Find existing date folder or show where new one will be created
DATE_PREFIX=$(date +%Y-%m-%d)
NEWS_BASE="/Users/svaug/Library/CloudStorage/Dropbox/Obsidian/News"
EXISTING_FOLDER=$(find "$NEWS_BASE" -maxdepth 1 -type d -name "${DATE_PREFIX}*" 2>/dev/null | head -1)

if [ -n "$EXISTING_FOLDER" ]; then
    echo "Summaries will be saved to existing folder: $EXISTING_FOLDER" | tee -a "$LOGFILE"
else
    echo "Summaries will be saved to new folder: $NEWS_BASE/$DATE_PREFIX/" | tee -a "$LOGFILE"
fi
echo "================================================" | tee -a "$LOGFILE"

# Command 1: News (Reuters and Mainstream)
echo -e "\n[$(date +%H:%M:%S)] Running Command 1: News..." | tee -a "$LOGFILE"
python rss_reader.py -c "Reuters" -c "Mainstream" --summarize 2>&1 | tee -a "$LOGFILE"

# Command 2: Politics
echo -e "\n[$(date +%H:%M:%S)] Running Command 2: Politics..." | tee -a "$LOGFILE"
python rss_reader.py -c "11" -c "12" -c "13" -c "14" -c "15" --summarize 2>&1 | tee -a "$LOGFILE"

# Command 3: Tech & AI
echo -e "\n[$(date +%H:%M:%S)] Running Command 3: Tech & AI..." | tee -a "$LOGFILE"
python rss_reader.py -c "80" -c "80.1" -c "80.2" -c "81" -f "Hacker News" --summarize 2>&1 | tee -a "$LOGFILE"

# Command 4: Christian News Sources
echo -e "\n[$(date +%H:%M:%S)] Running Command 4: Christian News..." | tee -a "$LOGFILE"
python rss_reader.py -c "40 Christian News" --summarize 2>&1 | tee -a "$LOGFILE"

# Command 5: Business, Crypto & Life Skills (with separate summaries)
echo -e "\n[$(date +%H:%M:%S)] Running Command 5: Multiple categories with separate summaries..." | tee -a "$LOGFILE"
python rss_reader.py -c "20" -c "30" -c "32" -c "35" -c "50" -c "60" -c "70" -c "71" -c "82" --summarize --separate-summaries 2>&1 | tee -a "$LOGFILE"

echo -e "\n================================================" | tee -a "$LOGFILE"
echo "All RSS summaries completed at $(date)" | tee -a "$LOGFILE"

# Optional: Clean up old logs (keep only last 30 days)
find logs -name "rss_summary_*.log" -mtime +30 -delete 2>/dev/null