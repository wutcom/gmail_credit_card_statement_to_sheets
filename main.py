import os
import tempfile
from datetime import datetime
from email.utils import parsedate_to_datetime

from dotenv import load_dotenv

from gmail_service import (
    download_attachment,
    ensure_label,
    get_header,
    get_gmail_service,
    get_message,
    iter_pdf_attachments,
    mark_as_processed,
    search_messages,
)
from pdf_parser import parse_statement, save_raw_text
from sheets_service import append_row_with_retry


GMAIL_SEARCH_QUERY = (
    'has:attachment filename:pdf '
    '(from:(kbank.com OR scb.co.th OR krungsri.com)) '
    '-label:processed'
)


def detect_bank(sender: str):
    sender_lower = sender.lower()

    if "kbank" in sender_lower:
        return {
            "bank_name": "KBank",
            "card_name": "KBank Credit Card",
            "password_env": "PDF_PASSWORD_KBANK",
        }

    if "scb" in sender_lower:
        return {
            "bank_name": "SCB",
            "card_name": "SCB Credit Card",
            "password_env": "PDF_PASSWORD_SCB",
        }

    if "krungsri" in sender_lower:
        return {
            "bank_name": "Krungsri",
            "card_name": "Krungsri Credit Card",
            "password_env": "PDF_PASSWORD_KRUNGSI",
        }

    return None


def parse_email_date(date_header: str) -> str:
    if not date_header:
        return ""

    try:
        return parsedate_to_datetime(date_header).strftime("%Y-%m-%d")
    except Exception:
        return date_header


def process_message(service, message_id: str, processed_label_id: str):
    message = get_message(service, message_id)

    subject = get_header(message, "Subject")
    sender = get_header(message, "From")
    email_date = parse_email_date(get_header(message, "Date"))

    bank = detect_bank(sender)
    if not bank:
        print(f"SKIP: cannot detect bank. sender={sender}")
        return

    password = os.getenv(bank["password_env"])
    if not password:
        print(f"SKIP: missing password env {bank['password_env']}")
        return

    attachments = list(iter_pdf_attachments(message))
    if not attachments:
        print(f"SKIP: no PDF attachment. subject={subject}")
        return

    all_success = True

    with tempfile.TemporaryDirectory() as temp_dir:
        for attachment in attachments:
            filename = attachment["filename"]
            pdf_path = os.path.join(temp_dir, filename)

            try:
                download_attachment(
                    service=service,
                    message_id=message_id,
                    attachment_id=attachment["attachment_id"],
                    output_path=pdf_path,
                )

                result = parse_statement(pdf_path, password)

                if not result["success"]:
                    all_success = False
                    print(f"PARSE FAILED: {filename} - {result['error']}")

                    if os.getenv("SAVE_RAW_TEXT_ON_ERROR", "true").lower() == "true":
                        saved_path = save_raw_text("logs", filename, result.get("text", ""))
                        print(f"Raw text saved: {saved_path}")

                    continue

                imported_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                row = [
                    imported_at,
                    email_date,
                    bank["bank_name"],
                    bank["card_name"],
                    result["amount_due"],
                    result["due_date"],
                    subject,
                    "DONE",
                ]

                append_row_with_retry(row)
                print(f"APPENDED: {bank['bank_name']} amount={result['amount_due']} due={result['due_date']}")

            except Exception as ex:
                all_success = False
                print(f"ERROR: {filename} - {ex}")

    if all_success:
        mark_as_processed(service, message_id, processed_label_id)
        print(f"MARKED PROCESSED: {subject}")
    else:
        print(f"NOT MARKED: some attachment failed. subject={subject}")


def main():
    load_dotenv()

    service = get_gmail_service()
    label_name = os.getenv("GMAIL_PROCESSED_LABEL", "processed")
    processed_label_id = ensure_label(service, label_name)

    messages = search_messages(service, GMAIL_SEARCH_QUERY, max_results=20)

    if not messages:
        print("No new credit card statement emails found.")
        return

    print(f"Found {len(messages)} message(s).")

    for item in messages:
        process_message(service, item["id"], processed_label_id)


if __name__ == "__main__":
    main()
