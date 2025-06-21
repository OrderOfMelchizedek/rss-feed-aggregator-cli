# RSS Aggregator Scheduling Setup

This document explains how to set up automated RSS summaries that run at 9 AM and 6 PM daily.

## Quick Setup

1. Run the setup script:
   ```bash
   ./setup_cron.sh
   ```

That's it! The RSS summaries will now run automatically at 9 AM and 6 PM every day.

## Manual Setup (if needed)

If you prefer to set up manually:

1. Open your crontab:
   ```bash
   crontab -e
   ```

2. Add these lines:
   ```
   # RSS News Aggregator - Automated Summaries
   0 9 * * * /Users/svaug/dev/svl_apps/news_aggregator/run_rss_summaries.sh
   0 18 * * * /Users/svaug/dev/svl_apps/news_aggregator/run_rss_summaries.sh
   ```

3. Save and exit

## What Gets Run

The script runs the following commands in sequence:

1. **News**: Reuters and Mainstream categories
2. **Politics**: Categories 11-15 (Political News, Conservative, Left-Wing, Right-Wing, Opinion)
3. **Tech & AI**: Categories 80, 80.1, 80.2, 81 plus Hacker News feed
4. **Christian News**: Category 40
5. **Multiple Categories**: Local, World, Foreign Relations, Tanzania, Foreign News Sources, Science, Business, Crypto, Life Skills (with separate summaries)

## Logs

All output is logged to `logs/rss_summary_YYYY-MM-DD_HH-MM-SS.log`

Logs older than 30 days are automatically deleted.

## Managing the Schedule

### View current cron jobs:
```bash
crontab -l
```

### Temporarily disable:
```bash
crontab -e
# Comment out the RSS lines by adding # at the beginning
```

### Remove completely:
```bash
crontab -e
# Delete the RSS-related lines
```

### Test the script manually:
```bash
./run_rss_summaries.sh
```

## Troubleshooting

1. **Script not running**: Check that Python is in your PATH
2. **Permission denied**: Ensure scripts are executable (`chmod +x *.sh`)
3. **No summaries generated**: Check the log files in the `logs/` directory
4. **Cron not working**: Make sure cron service is enabled on macOS

## Notes

- The script assumes Python is available in your system PATH
- All summaries are saved to `/Users/svaug/Library/CloudStorage/Dropbox/Obsidian/News/YYYY-MM-DD/` (organized by date)
- The script will continue even if individual commands fail