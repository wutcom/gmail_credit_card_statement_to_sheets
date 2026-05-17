import base64
import os
from pathlib import Path
from typing import Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def get_gmail_service():
    import shutil
    import tempfile

    credentials_path = os.getenv("GMAIL_CREDENTIALS_JSON", "credentials.json")
    token_path = os.getenv("GMAIL_TOKEN_JSON", "token.json")

    # Render /etc/secrets is read-only.
    # Copy token.json to /tmp before using it.
    if token_path.startswith("/etc/secrets/"):
        temp_token_path = os.path.join(tempfile.gettempdir(), "token.json")
        if not os.path.exists(temp_token_path):
            shutil.copyfile(token_path, temp_token_path)
        token_path = temp_token_path

    creds = None

    if Path(token_path).exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def ensure_label(service, label_name: str) -> str:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])

    for label in labels:
        if label.get("name") == label_name:
            return label["id"]

    created = service.users().labels().create(
        userId="me",
        body={
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        },
    ).execute()

    return created["id"]


def search_messages(service, query: str, max_results: int = 20) -> List[Dict]:
    response = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results,
    ).execute()

    return response.get("messages", [])


def get_message(service, message_id: str) -> Dict:
    return service.users().messages().get(
        userId="me",
        id=message_id,
        format="full",
    ).execute()


def get_header(message: Dict, header_name: str) -> str:
    headers = message.get("payload", {}).get("headers", [])
    for header in headers:
        if header.get("name", "").lower() == header_name.lower():
            return header.get("value", "")
    return ""


def iter_pdf_attachments(message: Dict):
    payload = message.get("payload", {})
    parts = []

    def walk(part):
        if "parts" in part:
            for child in part["parts"]:
                walk(child)
        else:
            parts.append(part)

    walk(payload)

    for part in parts:
        filename = part.get("filename", "")
        body = part.get("body", {})
        attachment_id = body.get("attachmentId")

        if filename.lower().endswith(".pdf") and attachment_id:
            yield {
                "filename": filename,
                "attachment_id": attachment_id,
            }


def download_attachment(service, message_id: str, attachment_id: str, output_path: str):
    attachment = service.users().messages().attachments().get(
        userId="me",
        messageId=message_id,
        id=attachment_id,
    ).execute()

    data = attachment.get("data")
    if not data:
        raise ValueError("Attachment data is empty")

    file_data = base64.urlsafe_b64decode(data.encode("utf-8"))

    with open(output_path, "wb") as file:
        file.write(file_data)


def mark_as_processed(service, message_id: str, label_id: str):
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={
            "addLabelIds": [label_id],
        },
    ).execute()
