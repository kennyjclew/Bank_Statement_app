# PDF Transaction Uploader to Google Sheets

This project allows you to upload PDF bank statements (UOB, DBS, CITI) via a **web interface** or a **Telegram bot**, parse the transactions, and automatically append them to a Google Sheet.  

It supports multiple PDFs at once and handles different bank statement formats.

---

## Features

- Upload **single or multiple PDF statements** via Flask web interface.  
- Optional **Telegram bot** interface for uploading PDFs.  
- Automatically detects the bank (UOB, DBS, CITI) and parses transactions.  
- Supports amounts with commas and decimals.  
- Filters out **summary lines**, extra dates, or `$` symbols.  
- Uploads transactions to **Google Sheets**.  

---

## Current Bank Statements Supported

- **Citibank Credit Card**  
- **DBS Paylah**  
- **DBS Credit Card**  
- **UOB Credit Card**  

---

# Bank Statement PDF Uploader — Setup Guide

This guide covers setting up environment variables, Google Sheets credentials, and running the Flask app in Docker.

---

## **2 Environment Variables (`.env`)**

Create a file named `.env` in the root of the project:

```dotenv
# Google Sheets spreadsheet ID
SPREADSHEET_ID=your_google_sheets_id_here

# Flask web authentication
WEB_USERNAME=your_username_here
WEB_PASSWORD=your_password_here

## **3 Google Sheets Credentials (credentials.json)**

1. Go to Google Cloud Console → APIs & Services → Credentials.
2. Create an OAuth 2.0 Client ID (Desktop App).
3. Download the file and save it as credentials.json in the project root.
    Important: Keep this file secure. Do not commit it to Git.
4. When you first run the app, token.json will be generated automatically after authenticating with Google Sheets.