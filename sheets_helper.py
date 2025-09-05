import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def add_row(spreadsheet_id, date_str, value, description, remarks, payment_method, range_value):
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("sheets", "v4", credentials=creds)

        row = [[date_str, value, description, remarks, payment_method]]
        resource = {"majorDimension": "ROWS", "values": row}

        response = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_value,
            body=resource,
            valueInputOption="USER_ENTERED",
        ).execute()

        if response:
            print("✅ Row added")
            # Also add to bank-specific sheets
            if "citi" in payment_method.lower() or "citibank" in payment_method.lower():
                service.spreadsheets().values().append(
                    spreadsheetId="1woLn_OuCpE5GQ-btYTacSTS2N738itIStWhXy0XkXww",
                    range="Citibank!E:I",
                    body=resource,
                    valueInputOption="USER_ENTERED",
                ).execute()
            elif "uob" in payment_method.lower():
                service.spreadsheets().values().append(
                    spreadsheetId="1woLn_OuCpE5GQ-btYTacSTS2N738itIStWhXy0XkXww",
                    range="UOB!E:I",
                    body=resource,
                    valueInputOption="USER_ENTERED",
                ).execute()
            return True
        else:
            return False

    except HttpError as err:
        print(f"❌ Error: {err}")
        return False
