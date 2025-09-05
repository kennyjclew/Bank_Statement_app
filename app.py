import os
import logging
import tempfile
import pdfplumber
from dotenv import load_dotenv
from flask import Flask, request, render_template_string, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

# Google Sheets API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# PDF parsers
from read_pdf import get_transactions_uob, get_transactions_dbs, get_transactions_citi

# ---------------- Logging ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- Load Config ----------------
load_dotenv()
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
WEB_USERNAME = os.getenv("WEB_USERNAME")
WEB_PASSWORD = os.getenv("WEB_PASSWORD")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

if not SPREADSHEET_ID or not WEB_USERNAME or not WEB_PASSWORD:
    logger.error("❌ Missing SPREADSHEET_ID or WEB_USERNAME/WEB_PASSWORD in .env")
    exit(1)

# ---------------- Google Sheets ----------------
def get_service():
    """Authenticate and return Google Sheets service."""
    creds = None
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception as e:
            logger.warning(f"Invalid token.json, will recreate: {e}")
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("sheets", "v4", credentials=creds)

def bulk_add_rows(spreadsheet_id, transactions, sheet_name="Transactions"):
    """Bulk append multiple transactions into Google Sheets in one call."""
    try:
        service = get_service()
        values = []
        for txn in transactions:
            txn_date, description, amount, source = txn
            values.append([txn_date, amount, description, "", source])
        body = {"majorDimension": "ROWS", "values": values}
        response = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
            body=body,
            valueInputOption="USER_ENTERED"
        ).execute()
        logger.info(f"✅ Bulk upload complete: {response}")
        return True
    except HttpError as err:
        logger.error(f"❌ Bulk upload error: {err}")
        return False

# ---------------- Flask App ----------------
app = Flask(__name__)
auth = HTTPBasicAuth()

# ---------------- Password Setup ----------------
users = {WEB_USERNAME: generate_password_hash(WEB_PASSWORD)}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username
    return None

# ---------------- HTML Upload Form ----------------
UPLOAD_FORM = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Upload PDF Bank Statements</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background-color: #f8f9fa; }
    .container { max-width: 600px; margin-top: 80px; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.1);}
    .btn-primary { width: 100%; }
    h1 { font-size: 1.8rem; margin-bottom: 20px; text-align: center; color: #343a40; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Upload PDF Statements</h1>
    <form id="upload-form">
      <div class="mb-3">
        <label for="pdfs" class="form-label">Choose PDF Files</label>
        <input class="form-control" type="file" id="pdfs" name="pdfs" accept=".pdf" multiple required>
      </div>
      <button type="submit" class="btn btn-primary">Upload & Process</button>
    </form>
    <div id="result" class="mt-3"></div>
  </div>
  <script>
    const form = document.getElementById('upload-form');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const files = document.getElementById('pdfs').files;
      if (!files.length) return alert("Please select at least one PDF file!");
      
      const resultDiv = document.getElementById('result');
      resultDiv.innerHTML = 'Processing...';

      let successCount = 0;
      let failCount = 0;

      for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append('pdf', files[i]);

        try {
          const response = await fetch('/upload', { method: 'POST', body: formData });
          if (!response.ok) {
            failCount++;
            const text = await response.text();
            console.error(`File ${files[i].name} failed:`, text);
          } else {
            const data = await response.json();
            successCount += data.transactions_uploaded || 0;
          }
        } catch (err) {
          failCount++;
          console.error(`File ${files[i].name} error:`, err.message);
        }
      }

      resultDiv.innerHTML = `<div class="alert alert-success">✅ Total transactions uploaded: ${successCount}</div>`;
      if (failCount > 0) {
        resultDiv.innerHTML += `<div class="alert alert-warning">⚠️ ${failCount} file(s) failed to process.</div>`;
      }
    });
  </script>
</body>
</html>
"""

# ---------------- Routes ----------------
@app.route("/")
@auth.login_required
def index():
    return render_template_string(UPLOAD_FORM)

@app.route("/upload", methods=["POST"])
@auth.login_required
def upload_pdf():
    if "pdf" not in request.files:
        return "⚠️ No file uploaded", 400
    file = request.files["pdf"]
    if file.filename == "":
        return "⚠️ No selected file", 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        file.save(tmp_file.name)
        tmp_file_path = tmp_file.name

    try:
        with pdfplumber.open(tmp_file_path) as pdf:
            first_page_text = pdf.pages[0].extract_text() or ""
            if "DBS" in first_page_text:
                transactions = get_transactions_dbs(pdf)
            elif "UOB" in first_page_text:
                transactions = get_transactions_uob(pdf)
            elif "CITI" in first_page_text:
                transactions = get_transactions_citi(pdf)
            else:
                return "⚠️ Bank not recognized in PDF", 400

        success = bulk_add_rows(SPREADSHEET_ID, transactions)
        if success:
            return jsonify({"status": "ok", "transactions_uploaded": len(transactions)})
        else:
            return "⚠️ Failed to upload transactions", 500
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return f"⚠️ Error processing PDF: {str(e)}", 500
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
            logger.info(f"✅ Temp file deleted: {tmp_file_path}")

@app.route("/manual", methods=["POST"])
@auth.login_required
def manual_transaction():
    """Add a single manual transaction from JSON request"""
    data = request.json
    try:
        row = [[
            data["date"],
            data["value"],
            data["description"],
            data.get("remarks", ""),
            data.get("payment_method", "Manual")
        ]]
        service = get_service()
        resource = {"majorDimension": "ROWS", "values": row}
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Transactions",
            body=resource,
            valueInputOption="USER_ENTERED",
        ).execute()
        return jsonify({"status": "ok", "row_added": row})
    except Exception as e:
        logger.error(f"Manual add failed: {e}")
        return f"⚠️ Error: {str(e)}", 500

# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)
