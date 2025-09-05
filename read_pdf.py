import pdfplumber
import csv
import re
import os

import time
from os import listdir
from os.path import isfile, join

def get_transactions_uob(lines):
    transactions = []
    for page in lines.pages:
        text = page.extract_text()
        if text:
            lines = text.split("\n")
            for line in lines:
                if "Ref No." in line:  
                    continue  # Skip lines with "Ref No."
                parts = line.split()
                # Get the last element
                date_pattern = re.compile(r"(\d{2}\s[A-Z]{3})\s+(\d{2}\s[A-Z]{3})")

                # Search for the pattern
                match = date_pattern.search(line)
                if match:
                    
                    line_arr = line.split()
                    if 'CR' in line_arr[-1]:
                        continue

                    post_date = line_arr[0] + ' ' + line_arr[1]
                    trans_date = line_arr[2] + ' ' + line_arr[3]
                    description = " ".join(line_arr[4:-1])
                    amount = line_arr[-1]
                    amount = amount.replace(",", "")
                    source = 'UOB'
                    transactions.append([trans_date, description.strip(), amount, source])
    return transactions

# transactions = []
def get_transactions_dbs(lines):
    date_pattern = re.compile(r"^\d{2}\s([A-Z]{3}|[A-Z]{1}[a-z]{2}\s[A-Z])")
    transactions = []
    is_paylah = False
    for page in lines.pages:
        text = page.extract_text()
        if text:
            lines = text.split("\n")
            # print(lines)
            for line in lines:
                if 'PayLah' in line:
                    is_paylah = True 
                # Search for the pattern
                match = date_pattern.search(line)

                if match:
                    line_arr = line.split()
                    if 'CR' in line_arr[-1]:
                        continue

                    trans_date = line_arr[0] + ' ' + line_arr[1]
                    if line_arr[-1] == "DB":
                        description = " ".join(line_arr[2:-2])
                        amount = line_arr[-2]
                    else:
                        description = " ".join(line_arr[2:-1])
                        amount = line_arr[-1]
                    # print(amount)
                    amount = amount.replace(",", "")
                    source = 'DBS Paylah' if is_paylah else 'DBS Credit Card'
                    transactions.append([trans_date, description.strip(), amount, source])
    return transactions

def get_transactions_citi(lines):
    date_pattern = re.compile(r"^\d{2}[A-Z]{3}")
    transactions = []
    for page in lines.pages:
        text = page.extract_text()
        if text:
            lines = text.split("\n")
            for line in lines:
                # print(line)
                # Search for the pattern
                match = date_pattern.search(line)

                if match:
                    line_arr = line.split()
                    print(line_arr)
                    if '(' in line_arr[-1]:
                        continue
                    if len(line_arr) > 1:

                        trans_date = line_arr[0]
                        description = " ".join(line_arr[1:-1])
                        amount = line_arr[-1]
                        amount = amount.replace(",", "")
                        source = 'CITI'
                        transactions.append([trans_date, description.strip(), amount, source])
    return transactions


# for pdffile in onlyfiles:
#     if '.DS' in pdffile:
#         continue
#     pdf_file = my_dir+'/'+pdffile
#     csv_file = my_dir+'/csv/'+pdffile+".csv"
#     # Open and read the PDF
#     with pdfplumber.open(pdf_file) as pdf:
#         # for page in pdf.pages:
#         print(pdf)
#         text = pdf.pages[0].extract_text()
#         # print(text)
#         # print(type(text))
#         if text:
#             lines = text.split("\n")
#             for line in lines:

#                 if "DBS" in line:
#                     transactions = get_transactions_dbs(pdf)
#                     # transactions.append(transactions_result)
#                     break

#                 if "UOB" in line:
#                     transactions = get_transactions_uob(pdf)
#                     break
                
#                 if "CITI" in line:
#                     transactions = get_transactions_citi(pdf)
#                     break


                    

#     print('hello')
# # print(transactions)

# # Save extracted transactions to a CSV file
#     with open(csv_file, "w", newline="", encoding="utf-8") as f:
#         writer = csv.writer(f)
#         writer.writerow(["Post Date", "Transaction Date", "Description", "Amount (SGD)"])
#         writer.writerows(transactions)

#     print(f"CSV file '{csv_file}' created successfully with {len(transactions)} transactions!")


