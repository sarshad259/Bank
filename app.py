from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
import random

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Change this in production

DATA_FILE = "Bank_system.json"
All_accounts = []

def load_users():
    global All_accounts
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            All_accounts = json.load(f)

def save_users():
    with open(DATA_FILE, "w") as f:
        json.dump(All_accounts, f, indent=4)

load_users()  # ✅ ALWAYS load users on startup (works on Render, Gunicorn, etc.)

class User:
    def __init__(self, account_data):
        self.data = account_data

    def deposit(self, amount):
        self.data["initial_balance"] += amount
        self.data["transaction_history"].append(f"Deposited {amount}")
        save_users()

    def withdraw(self, amount):
        if amount <= self.data["initial_balance"]:
            self.data["initial_balance"] -= amount
            self.data["transaction_history"].append(f"Withdraw {amount}")
            save_users()
            return True
        else:
            return False

    def get_balance(self):
        return self.data["initial_balance"]

    def get_transactions(self):
        return self.data["transaction_history"]

def find_user(username, pin):
    for acc in All_accounts:
        if acc["username"] == username and acc["PIN_CODE"] == pin:
            return User(acc)
    return None

def find_user_by_username(username):
    for acc in All_accounts:
        if acc["username"] == username:
            return User(acc)
    return None

def get_other_usernames(current_username):
    return [acc["username"] for acc in All_accounts if acc["username"] != current_username]

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=["GET", "POST"])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        username = request.form.get("username")
        pin = request.form.get("pin")
        if not pin or not pin.isdigit():
            flash("❌ Invalid PIN format.", "error")
            return redirect(url_for('login'))
        pin = int(pin)
        user = find_user(username, pin)
        if user:
            session['username'] = username
            session['pin'] = pin
            flash("✅ Logged in successfully.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("❌ Invalid username or PIN.", "error")
            return redirect(url_for('login'))

    return render_template("login.html")

@app.route('/create_account', methods=["GET", "POST"])
def create_account():
    if 'username' in session:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()  # Not used for auth here, just stored
        try:
            balance = float(request.form.get("balance"))
        except:
            flash("❌ Invalid initial balance.", "error")
            return redirect(url_for('create_account'))

        if not username or not password:
            flash("❌ Username and password are required.", "error")
            return redirect(url_for('create_account'))

        for acc in All_accounts:
            if acc["username"] == username:
                flash("❌ Username already exists.", "error")
                return redirect(url_for('create_account'))

        pin = random.randint(1000, 9999)
        account = {
            "username": username,
            "password": password,
            "PIN_CODE": pin,
            "initial_balance": balance,
            "transaction_history": []
        }
        All_accounts.append(account)
        save_users()

        session['username'] = username
        session['pin'] = pin

        flash(f"✅ Account created! Your PIN is: {pin}. Please keep it safe.", "success")
        return redirect(url_for('dashboard'))

    return render_template("create_account.html")

@app.route('/dashboard', methods=["GET", "POST"])
def dashboard():
    if 'username' not in session or 'pin' not in session:
        flash("Please log in first.", "error")
        return redirect(url_for('login'))

    user = find_user(session['username'], session['pin'])
    if not user:
        flash("User session invalid, please login again.", "error")
        session.clear()
        return redirect(url_for('login'))

    if request.method == "POST":
        action = request.form.get("action")
        if action == "transfer":
            recipient_username = request.form.get("recipient")
            try:
                amount = float(request.form.get("transfer_amount", 0))
            except:
                flash("❌ Invalid amount.", "error")
                return redirect(url_for('dashboard'))

            if amount <= 0:
                flash("❌ Amount must be greater than zero.", "error")
                return redirect(url_for('dashboard'))

            if recipient_username == user.data["username"]:
                flash("❌ Cannot transfer to yourself.", "error")
                return redirect(url_for('dashboard'))

            recipient = find_user_by_username(recipient_username)
            if not recipient:
                flash("❌ Recipient not found.", "error")
                return redirect(url_for('dashboard'))

            if user.get_balance() < amount:
                flash("❌ Insufficient balance for transfer.", "error")
                return redirect(url_for('dashboard'))

            user.data["initial_balance"] -= amount
            user.data["transaction_history"].append(f"Transferred {amount} to {recipient_username}")
            recipient.data["initial_balance"] += amount
            recipient.data["transaction_history"].append(f"Received {amount} from {user.data['username']}")
            save_users()
            flash(f"✅ Transferred {amount} to {recipient_username} successfully.", "success")
            return redirect(url_for('dashboard'))

        else:
            try:
                amount = float(request.form.get("amount", 0))
            except:
                flash("❌ Invalid amount.", "error")
                return redirect(url_for('dashboard'))

            if amount <= 0:
                flash("❌ Amount must be greater than zero.", "error")
                return redirect(url_for('dashboard'))

            if action == "deposit":
                user.deposit(amount)
                flash(f"✅ Deposited {amount} successfully.", "success")
            elif action == "withdraw":
                success = user.withdraw(amount)
                if success:
                    flash(f"✅ Withdrew {amount} successfully.", "success")
                else:
                    flash("❌ Insufficient balance.", "error")
            else:
                flash("❌ Invalid action.", "error")
            return redirect(url_for('dashboard'))

    return render_template(
        "dashboard.html",
        username=user.data["username"],
        pin=user.data["PIN_CODE"],
        balance=user.get_balance(),
        transactions=user.get_transactions(),
        other_users=get_other_usernames(user.data["username"])
    )

@app.route('/logout')
def logout():
    session.clear()
    flash("🔒 Logged out successfully.", "info")
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
