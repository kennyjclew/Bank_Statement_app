import os
import logging
from dotenv import load_dotenv

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import requests
import tempfile
import pdfplumber
from read_pdf import get_transactions_uob, get_transactions_dbs, get_transactions_citi
# Google Sheets API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ---------------- Logging ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- Load Config ----------------
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

if not TELEGRAM_TOKEN or not SPREADSHEET_ID:
    logger.error("❌ TELEGRAM_TOKEN or SPREADSHEET_ID missing in .env")
    exit(1)

# ---------------- Google Sheets ----------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

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

def add_row(spreadsheet_id, date_str, value, description, remarks, payment_method, range_value="Transactions"):
    """Append a row to Google Sheets."""
    try:
        service = get_service()

        row = [[date_str, value, description, remarks, payment_method]]
        resource = {"majorDimension": "ROWS", "values": row}

        response = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_value,  # just the sheet name
            body=resource,
            valueInputOption="USER_ENTERED",
        ).execute()

        if response:
            logger.info("✅ Row added successfully")
            return True
        else:
            logger.error("⚠️ Failed to append row")
            return False

    except HttpError as err:
        logger.error(f"Sheets API error: {err}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False
def bulk_add_rows(spreadsheet_id, transactions, sheet_name="Transactions"):
    """
    Bulk append multiple transactions into Google Sheets in one call.
    
    transactions = [
        ['12 JUL', 'WWW.WAACOW.SG* WAACOW SINGAPORE', '87.86', 'UOB'],
        ['12 JUL', 'SWEE HENG BAKERY-CL23 SINGAPORE', '2.00', 'UOB'],
        ['12 JUL', "MCDONALD'S (AMT2) SINGAPORE", '2.60', 'UOB']
    ]
    """
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

        # Transform PDF rows into the schema your sheet expects
        values = []
        for txn in transactions:
            txn_date, description, amount, source = txn
            values.append([txn_date, amount, description, "", source])

        body = {
            "majorDimension": "ROWS",
            "values": values
        }

        response = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,   # just sheet name for append
            body=body,
            valueInputOption="USER_ENTERED"
        ).execute()

        logger.info(f"✅ Bulk upload complete: {response}")
        return True

    except HttpError as err:
        logger.error(f"❌ Bulk upload error: {err}")
        return False
# ---------------- Conversation States ----------------
CHOOSING, MANUAL_INPUT, WAITING_FOR_PDF = range(3)

# ---------------- Handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Manual Transaction", "Upload PDF"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Hi! What would you like to do?",
        reply_markup=reply_markup
    )
    return CHOOSING

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.lower()
    logger.info(f"User chose: {choice}")

    if choice == "manual transaction":
        await update.message.reply_text(
            "Please send transaction details in this format:\n"
            "`date, value, description, remarks, payment_method`",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        return MANUAL_INPUT

    elif choice == "upload pdf":
        await update.message.reply_text(
            "Please upload your PDF file.",
            reply_markup=ReplyKeyboardRemove()
        )
        return WAITING_FOR_PDF

    else:
        await update.message.reply_text("Please choose a valid option.")
        return CHOOSING

async def handle_manual_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Handling manual input: {update.message.text}")

    try:
        data = update.message.text.split(",")
        if len(data) < 5:
            raise ValueError("Not enough fields provided")

        date_str, value, description, remarks, payment_method = [x.strip() for x in data]

        success = add_row(
            SPREADSHEET_ID,
            date_str,
            value,
            description,
            remarks,
            payment_method,
            "Transactions"  # sheet name only
        )

        if success:
            await update.message.reply_text("✅ Transaction saved to Google Sheet!")
        else:
            await update.message.reply_text("⚠️ Failed to save transaction.")

    except Exception as e:
        logger.error(f"Error in handle_manual_input: {e}")
        await update.message.reply_text(
            "⚠️ Error! Please use the format:\n"
            "`date, value, description, remarks, payment_method`",
            parse_mode="Markdown"
        )

    return ConversationHandler.END

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download uploaded PDF and process into Google Sheets."""
    try:
        document = update.message.document
        file_id = document.file_id

        # Get file from Telegram
        telegram_file = await context.bot.get_file(file_id)
        file_url = telegram_file.file_path
        logger.info(f"📄 Received PDF file URL: {file_url}")

        # Download file into a temp folder
        response = requests.get(file_url)
        if response.status_code != 200:
            await update.message.reply_text("⚠️ Failed to download PDF from Telegram.")
            return ConversationHandler.END

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(response.content)
            tmp_file_path = tmp_file.name

        logger.info(f"✅ PDF saved locally: {tmp_file_path}")
        with pdfplumber.open(tmp_file_path) as pdf:
            # for page in pdf.pages:
            print(pdf)
            text = pdf.pages[0].extract_text()
            # print(text)
            # print(type(text))
            if text:
                lines = text.split("\n")
                for line in lines:

                    if "DBS" in line:
                        transactions = get_transactions_dbs(pdf)
                        # transactions.append(transactions_result)
                        break

                    if "UOB" in line:
                        transactions = get_transactions_uob(pdf)
                        break
                    
                    if "CITI" in line:
                        transactions = get_transactions_citi(pdf)
                        break

        success = bulk_add_rows(SPREADSHEET_ID, transactions)

        if success:
            await update.message.reply_text(f"✅ {len(transactions)} transactions uploaded to Google Sheets.")
        else:
            await update.message.reply_text("⚠️ Failed to upload transactions.")
        await update.message.reply_text("✅ PDF uploaded and processed into Google Sheets!")

    except Exception as e:
        logger.error(f"Error in handle_pdf: {e}")
        await update.message.reply_text("⚠️ Error processing PDF.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ---------------- Main ----------------
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                MessageHandler(filters.Regex("(?i)^(manual transaction|upload pdf)$"), handle_choice)
            ],
            MANUAL_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_input)
            ],
            WAITING_FOR_PDF: [
                MessageHandler(filters.Document.PDF, handle_pdf)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    logger.info("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
