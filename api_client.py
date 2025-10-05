import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("CAPITAL_ONE_API_KEY")
BASE_URL = "http://api.nessieisreal.com"

def create_customer(first_name, last_name):
    url = f"{BASE_URL}/customers?key={API_KEY}"
    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "address": {"street_number": "2920", "street_name": "Broadway", "city": "New York", "state": "NY", "zip": "10027"}
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()["objectCreated"]["_id"]

def create_account(customer_id, balance):
    url = f"{BASE_URL}/customers/{customer_id}/accounts?key={API_KEY}"
    payload = {"type": "Checking", "nickname": "checking", "balance": balance, "rewards": 0}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()["objectCreated"]["_id"]

def make_deposit(account_id, date, amount, description):
    url = f"{BASE_URL}/accounts/{account_id}/deposits?key={API_KEY}"
    payload = {"medium": "balance", "transaction_date": date, "amount": amount, "description": description}
    response = requests.post(url, json=payload)
    response.raise_for_status()

def make_withdrawal(account_id, date, amount, description):
    url = f"{BASE_URL}/accounts/{account_id}/withdrawals?key={API_KEY}"
    payload = {"medium": "balance", "transaction_date": date, "amount": amount, "description": description}
    response = requests.post(url, json=payload)
    response.raise_for_status()

def get_account_balance(account_id):
    url = f"{BASE_URL}/accounts/{account_id}?key={API_KEY}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()["balance"]

def get_all_transactions_for_account(account_id):
    try:
        deposits_url = f"{BASE_URL}/accounts/{account_id}/deposits?key={API_KEY}"
        withdrawals_url = f"{BASE_URL}/accounts/{account_id}/withdrawals?key={API_KEY}"

        deposits = requests.get(deposits_url).json()
        withdrawals = requests.get(withdrawals_url).json()

        for d in deposits: d['type'] = 'deposit'
        for w in withdrawals: w['type'] = 'withdrawal'

        all_events = deposits + withdrawals
        all_events = [t for t in all_events if t.get('transaction_date')]
        all_events.sort(key=lambda x: x['transaction_date'], reverse=True)

        return all_events

    except requests.exceptions.RequestException as e:
        print(f"Error fetching financial history for account {account_id}: {e}")
        return []