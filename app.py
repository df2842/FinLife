import uuid
from datetime import date, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
import api_client
import ai_agent

app = Flask(__name__)
CORS(app)

PORT = 5500
START_BALANCE = 50000
ANNUAL_EXPENSES = 40000
START_AGE = 16
END_AGE = 67

game_sessions = {}

@app.route('/game/start', methods=['POST'])
def start_game():
    data = request.json
    first_name = data.get("firstName")
    last_name = data.get("lastName")
    if not first_name or not last_name:
        return jsonify({"error": "firstName and lastName are required."}), 400

    try:
        customer_id = api_client.create_customer(first_name, last_name)
        account_id = api_client.create_account(customer_id, START_BALANCE)

        game_id = str(uuid.uuid4())
        game_sessions[game_id] = {
            "customerId": customer_id,
            "accountId": account_id,
            "age": START_AGE,
            "currentDate": date(date.today().year, 1, 1),
            "balance": START_BALANCE,
            "income": 0,
            "jobTitle": "Unemployed",
            "loans": [],
            "life_events": []
        }

        response_state = game_sessions[game_id].copy()
        response_state["currentDate"] = response_state["currentDate"].isoformat()

        return jsonify({
            "gameId": game_id,
            "message": f"Welcome, {first_name}! Your financial life begins.",
            "playerState": response_state
        })

    except Exception as e:
        print(f"Error starting game: {e}")
        return jsonify({"error": "Failed to start game due to an internal server error."}), 500

@app.route('/game/state', methods=['POST'])
def get_game_state():
    data = request.json
    game_id = data.get("gameId")
    session = game_sessions.get(game_id)
    if not session:
        return jsonify({"error": "Game session not found."}), 404

    response_state = session.copy()
    response_state["currentDate"] = response_state["currentDate"].isoformat()
    return jsonify({"playerState": response_state})

@app.route('/game/advance-year', methods=['POST'])
def advance_year():
    data = request.json
    game_id = data.get("gameId")
    session = game_sessions.get(game_id)
    if not session:
        return jsonify({"error": "Game session not found."}), 404

    try:
        session["age"] += 1
        session["currentDate"] += timedelta(days=365)
        sim_date = session["currentDate"].isoformat()

        if session["income"] > 0:
            api_client.make_deposit(session["accountId"], sim_date, session["income"], session["jobTitle"] + " Annual Salary")
        if session["age"] >= 22:
            api_client.make_withdrawal(session["accountId"], sim_date, ANNUAL_EXPENSES, "Annual Living Expenses")

        session["balance"] = api_client.get_account_balance(session["accountId"])
        session["loans"] = api_client.get_all_loans(session["customerId"])

        if session["age"] >= 67:
            transaction_history = api_client.get_all_transactions_for_account(session["customerId"], session["accountId"])
            final_summary = ai_agent.generate_fs(session["balance"], session["income"], session["loans"], transaction_history)

            response_state = session.copy()
            response_state["currentDate"] = response_state["currentDate"].isoformat()

            del game_sessions[game_id]

            return jsonify({
                "gameOver": True,
                "message": "You've reached the retirement age of 67. Your financial journey is complete!",
                "playerState": response_state,
                "finalSummary": final_summary
            })

        event_type = "mcq"
        specifier = "N/A"

        age = session["age"]
        if age == 18:
            specifier = "paying or borrowing for college"
        elif age == 21:
            specifier = "paying or borrowing for a car"
        elif age == 38:
            specifier = "paying or borrowing for a house"
        elif (age <= 30 and age % 2 == 0) or (age > 30 and age % 5 == 0):
            event_type = "job"

        if event_type == "job":
            scenario = ai_agent.generate_jo(
                session["age"], session["income"],
                session["jobTitle"], session["life_events"]
            )
        else:
            scenario = ai_agent.generate_mcq(
                session["age"], sim_date, session["balance"],
                session["income"], session["loans"],
                session["life_events"], specifier
            )

        response_state = session.copy()
        response_state["currentDate"] = response_state["currentDate"].isoformat()

        return jsonify({
            "message": f"You are now {age} years old.",
            "playerState": response_state,
            "nextEvent": scenario
        })

    except Exception as e:
        print(f"Error advancing year: {e}")
        return jsonify({"error": "Failed to advance to the next year."}), 500

@app.route('/decision/mcq', methods=['POST'])
def make_mcq_decision():
    data = request.json
    game_id = data.get("gameId")
    choice = data.get("choice")
    session = game_sessions.get(game_id)
    if not session:
        return jsonify({"error": "Game session not found."}), 404

    try:
        impact = choice["financial_impact"]
        action = impact["action"]
        amount = impact["amount"]
        description = impact["description"]
        sim_date = session["currentDate"].isoformat()

        if action == "DEPOSIT":
            api_client.make_deposit(session["accountId"], sim_date, amount, description)
        elif action == "WITHDRAWAL":
            api_client.make_withdrawal(session["accountId"], sim_date, amount, description)
        elif action == "CREATE_LOAN":
            api_client.create_loan(session["customerId"], sim_date, amount, description)

        session["balance"] = api_client.get_account_balance(session["accountId"])
        session["loans"] = api_client.get_all_loans(session["customerId"])
        session["life_events"].append(description)

        response_state = session.copy()
        response_state["currentDate"] = response_state["currentDate"].isoformat()

        return jsonify({
            "message": "Decision processed.",
            "playerState": response_state
        })

    except Exception as e:
        print(f"Error making MCQ decision: {e}")
        return jsonify({"error": "Failed to process decision."}), 500

@app.route('/decision/job', methods=['POST'])
def make_job_decision():
    data = request.json
    game_id = data.get("gameId")
    choice = data.get("choice")
    session = game_sessions.get(game_id)
    if not session:
        return jsonify({"error": "Game session not found."}), 404

    try:
        impact = choice["financial_impact"]
        session["income"] = impact["income"]
        session["jobTitle"] = impact["title"]
        session["life_events"].append(f"Became a {impact['title']}")

        response_state = session.copy()
        response_state["currentDate"] = response_state["currentDate"].isoformat()

        return jsonify({
            "message": f"Congratulations on your new role as a {impact['title']}!",
            "playerState": response_state
        })

    except Exception as e:
        print(f"Error making Job decision: {e}")
        return jsonify({"error": "Failed to process job decision."}), 500

@app.route('/game/pay-loan', methods=['POST'])
def pay_loan():
    data = request.json
    game_id = data.get("gameId")
    amount = data.get("amount")
    session = game_sessions.get(game_id)
    if not session:
        return jsonify({"error": "Game session not found."}), 404
    if not amount or amount <= 0:
        return jsonify({"error": "A valid payment amount is required."}), 400

    if not session["loans"]:
        return jsonify({"message": "You have no loans to pay off!", "playerState": session}), 200

    try:
        loan_to_pay = session["loans"][0]
        loan_id = loan_to_pay["_id"]

        api_client.make_loan_payment(loan_id, session["accountId"], session["currentDate"].isoformat(), amount)

        session["balance"] = api_client.get_account_balance(session["accountId"])
        session["loans"] = api_client.get_all_loans(session["customerId"])

        response_state = session.copy()
        response_state["currentDate"] = response_state["currentDate"].isoformat()

        return jsonify({
            "message": f"Successfully paid ${amount} towards your loan.",
            "playerState": response_state
        })

    except Exception as e:
        print(f"Error paying loan: {e}")
        return jsonify({"error": "Failed to process loan payment."}), 500

@app.route('/game/history', methods=['POST'])
def get_history():
    data = request.json
    game_id = data.get("gameId")
    session = game_sessions.get(game_id)
    if not session:
        return jsonify({"error": "Game session not found."}), 404

    try:
        history = api_client.get_all_transactions_for_account(session["customerId"], session["accountId"])
        return jsonify({"transaction_history": history})

    except Exception as e:
        print(f"Error fetching history: {e}")
        return jsonify({"error": "Failed to fetch transaction history."}), 500

if __name__ == '__main__':
    app.run(port=PORT, debug=True)