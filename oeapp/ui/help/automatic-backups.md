# Automatic Backups

## Overview

The Ænglisc Toolkit automatically creates backups of your project database to protect your work. Backups are created in the background without any action required from you.

## How Automatic Backups Work

### Automatic Creation

- Backups are created automatically at regular intervals
- The system checks every 5 minutes if a backup is needed
- No manual action is required - backups happen in the background
- You'll see a brief "Backup created" message when a backup is made

### Default Settings

- **Backup Interval**: Every 12 hours (720 minutes)
- **Number of Backups Kept**: 5 most recent backups
- Older backups are automatically deleted to save space

### Backup Location

Backups are stored in a `backups` folder next to your project database file. Each backup consists of two files:

- **Database file** (`.db`): A complete copy of your project database
- **Metadata file** (`.json`): Information about the backup, including:

    - When the backup was created
    - Which projects are included
    - Application version
    - Database size

## Configuring Backup Settings

You can customize backup behavior in Preferences:

1. Go to **File → Preferences**
2. Adjust the following settings:

   - **Number of backups to keep**: How many recent backups to retain (1-100)
   - **Backup interval (minutes)**: How often to create backups (1-1440 minutes)

### Recommended Settings

- **Frequent work**: Set interval to 60-120 minutes (1-2 hours)
- **Occasional work**: Default 720 minutes (12 hours) is usually sufficient
- **Number of backups**: 5-10 backups provides good protection without using too much disk space

## When Backups Are Created

Backups are created automatically:

- **On schedule**: Based on your configured interval
- **Before database migrations**: When the application updates its database structure
- **Before restore operations**: When restoring from a previous backup

## Backup Files

Each backup is named with a timestamp:

- Format: `project_db_YYYY-MM-DD_HH-MM-SS.db`
- Example: `project_db_2024-01-15_14-30-00.db`
- The corresponding metadata file has the same name with `.json` extension

## Restoring from a Backup

If you need to restore your project from a backup:

1. The application can restore backups automatically if database migrations fail
2. Manual restore functionality may be available in future versions
3. Backup files can be found in the `backups` folder if you need to access them directly

## Important Notes

- **Backups are local**: Backups are stored on your computer, not in the cloud
- **Disk space**: Each backup is a full copy of your database, so they can use significant disk space
- **Automatic cleanup**: Old backups beyond your retention limit are automatically deleted
- **No interruption**: Backups don't interrupt your work - they happen in the background

## Troubleshooting

**Problem**: Backups not being created

- **Solution**: Check that you have write permissions in the backups folder
- Ensure sufficient disk space is available
- Check Preferences to verify backup settings are configured

**Problem**: Too many backups using disk space

- **Solution**: Reduce the "Number of backups to keep" setting in Preferences
- Manually delete old backup files from the backups folder if needed

**Problem**: Want more frequent backups

- **Solution**: Reduce the "Backup interval (minutes)" setting in Preferences
- Minimum interval is 1 minute (not recommended for normal use)

## Best Practices

1. **Keep default settings** unless you have specific needs
2. **Monitor disk space** if you have very large projects
3. **Don't disable backups** - they're your safety net
4. **Check backup folder periodically** to ensure backups are being created
5. **Keep backups when upgrading** - the system creates backups before migrations automatically
