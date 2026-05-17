# Gmail Credit Card Statement to Google Sheets

Python app for Render Cron Job that:

1. Searches Gmail for credit card statement emails.
2. Downloads PDF attachments.
3. Unlocks password-protected PDFs.
4. Extracts amount due and due date using regex.
5. Appends results to Google Sheets.
6. Marks processed emails with Gmail label `processed`.

No AI is used.

## Project Structure

```text
project/
├── main.py
├── gmail_service.py
├── pdf_parser.py
├── sheets_service.py
├── requirements.txt
├── .env.example
├── credentials.json
├── token.json
└── service_account.json
```

## Install

```bash
pip install -r requirements.txt
```

## Environment Variables

Create `.env` from `.env.example`.

```env
GMAIL_CREDENTIALS_JSON=credentials.json
GMAIL_TOKEN_JSON=token.json
GOOGLE_SHEET_ID=your_google_sheet_id

PDF_PASSWORD_KBANK=DDMMYYYY
PDF_PASSWORD_SCB=DDMMYYYY
PDF_PASSWORD_KRUNGSI=DDMMYYYY

GMAIL_PROCESSED_LABEL=processed
SAVE_RAW_TEXT_ON_ERROR=true
```

## Google Sheet Columns

| Column | Field |
|---|---|
| A | Date Imported |
| B | Email Date |
| C | Bank Name |
| D | Card Name |
| E | Amount Due |
| F | Due Date |
| G | Email Subject |
| H | Processed Status |

## Gmail Query

```text
has:attachment filename:pdf (from:(kbank.com OR scb.co.th OR krungsri.com)) -label:processed
```

## First-time Gmail OAuth Setup

Run locally once:

```bash
python main.py
```

Browser will open for Gmail OAuth consent.

After success, `token.json` will be created.

Upload or configure these securely on Render:

- `credentials.json`
- `token.json`
- `service_account.json`

## Google Sheets Setup

1. Create Google Cloud service account.
2. Download `service_account.json`.
3. Share target Google Sheet with service account email.
4. Give Editor permission.

## Render Cron Job

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
python main.py
```

Schedule:

```cron
0 8 * * *
```

## Security

Do not commit these files:

```text
.env
credentials.json
token.json
service_account.json
logs/
```

Use Render Environment Variables and Secret Files instead.
