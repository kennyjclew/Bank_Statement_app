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