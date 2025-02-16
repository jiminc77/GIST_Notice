# GIST_Notice

This project automatically checks for new notices on the GIST(Gwangju Institute of Science and Technology) academic bulletin board ([GIST Academic Notice Board](https://www.gist.ac.kr/kr/html/sub05/050209.html?mode=L)) and sends email alerts when new posts are discovered.

## Overview

- **Automated checks**: Uses GitHub Actions to run a Python script once a day (or on-demand) without requiring a local machine to stay powered on.
- **State management**: Stores the last seen post ID in a GitHub Gist so the project can keep track of which posts have already been processed, even when running on ephemeral CI environments.
- **Email notifications**: Sends an email to a specified list of recipients if there are new notices since the last check.  
- **Schedule**: Configured via a cron schedule in GitHub Actions (`.github/workflows/main.yml`).
  
## How It Works

1. **GitHub Actions triggers**  
   - The Actions workflow is triggered daily by a schedule (or manually via push or a workflow dispatch).
2. **Retrieve last seen post ID**  
   - The script reads the `last_id.txt` content from a Gist via the GitHub API.  
   - If the file doesn’t exist or is `-1`, it treats the state as “no posts seen yet.”
3. **Scrape the notice board**  
   - The script scrapes the [GIST academic bulletin board](https://www.gist.ac.kr/kr/html/sub05/050209.html?mode=L) using `requests` and `BeautifulSoup`.
   - It collects each post’s ID, title, date, and link.
4. **Compare IDs**  
   - The script compares post IDs against the last seen ID. All posts with IDs larger than `last_id` are considered new.
5. **Send email alerts**  
   - If there are new posts, it sends an email message with details of the new entries to the configured recipients.  
   - The script then updates `last_id.txt` in the Gist with the highest new post ID.
6. **Repeat**  
   - The GitHub Actions workflow repeats on schedule (or on demand), ensuring continuous monitoring.

## File Structure

```
.
├── gist_notice_emailer.py       # Main Python script (scraper + email sender + Gist updater)
├── requirements.txt             # Python dependencies
└── .github
    └── workflows
        └── main.yml            # GitHub Actions workflow
```

### `gist_notice_emailer.py`
- Scrapes the GIST bulletin board for notices (`requests`, `BeautifulSoup`).
- Retrieves and updates the last known post ID in a Gist (`requests` to GitHub API).
- Sends email via SMTP when new posts are found.

### `requirements.txt`
```
requests
beautifulsoup4
```

### `.github/workflows/main.yml`
- Specifies the cron schedule (e.g., daily from 00:00 to 12:00 UTC, every hour).
- Installs dependencies and runs the Python script.
- Passes environment variables (secrets) needed for Gist ID, SMTP configuration, etc.

## Configuration

You need to add the following secrets in your GitHub repository:

| Secret Name       | Description                                   |
|-------------------|-----------------------------------------------|
| **GIST_ID**       | The Gist ID where `last_id.txt` is stored.    |
| **GIST_TOKEN**    | A Personal Access Token with `public_gist` permission. |
| **SMTP_SERVER**   | SMTP server address (e.g., `smtp.gmail.com`). |
| **SMTP_PORT**     | SMTP server port (e.g., `587`).               |
| **SMTP_USERNAME** | SMTP user account (e.g., `myaccount@gmail.com`).  |
| **SMTP_PASSWORD** | An app-specific password if using Gmail’s 2FA. |
| **MAIL_SENDER**   | The email address that appears as sender.     |
| **MAIL_SENDER_NAME** | The display name for the sender (e.g., “공지봇”). |
| **MAIL_RECEIVER** | Comma-separated list of recipient emails.     |

## Usage

1. **Fork or clone** this repository.
2. **Create a Gist** with a file named `last_id.txt` (initially containing `-1`).
3. **Set up the required secrets** in your GitHub repo under **Settings → Secrets and variables → Actions**.
4. **(Optional) Modify** `.github/workflows/main.yml` to adjust the schedule or additional triggers.
5. **Push the changes** or run the workflow manually to test:
   - The script will detect all posts as new if `last_id.txt` is `-1`.
   - It will send an email, then update the Gist with the latest post ID.

## Troubleshooting

- **SMTPAuthenticationError**: Check that you are using an app password (if using Gmail) and that the username/password are correct.
- **No new posts**: If the script reports “No new posts,” it likely means your `last_id.txt` is already at or above the highest post ID.
