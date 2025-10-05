import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def _call_generative_model(prompt):
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content(prompt)
        cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_text)

    except Exception as e:
        print(f"Error calling Generative AI Model: {e}")
        return {"error": "Failed to generate scenario from AI model."}

def generate_mcq(age, date, balance, income, loans, life_events, specifier="N/A"):
    if loans:
        loan_descriptions = [f"'{loan.get('description')}' with ${loan.get('remaining_amount', 0):,.2f} remaining" for loan in loans]
        formatted_loans = ", ".join(loan_descriptions)
    else:
        formatted_loans = "None"

    prompt = f"""
    You are a creative writer for a life simulation game called "FinLife".
    The current date in the simulation is {date}.
    
    Your goal is to generate a single, nuanced financial dilemma based on the player's current situation.
    If specified, the dilemma must focus on {specifier}.
    The choices should focus on one-time financial events, investments, or unique opportunities, NOT steady sources of income. 
    
    The dilemma must be relevant to the player's context.

    --- Player Context ---
    Age: {age}
    Current Checking Balance: ${balance:,.2f}
    Yearly Income: ${income:,.2f}
    Active Loans: {formatted_loans}
    Notable Past Life Events: {life_events if life_events else 'None'}
    --------------------

    The scenario must have three distinct choices. For each choice, you must provide:
    1.  A "description" of the choice. This description MUST end with a parenthesized summary of the financial impact. 
        - For DEPOSIT, use (+$<amount>).
        - For WITHDRAWAL, use (-$<amount>).
        - For CREATE_LOAN, use (Loan: $<amount>).
    2.  A "financial_impact" JSON object. This object MUST contain a string "action", an integer "amount", and a string "description".
        The action must be one of: ["DEPOSIT", "WITHDRAWAL", "CREATE_LOAN"].

    Example Output Format (for a player who previously started a side-hustle):
    {{
      "scenario_title": "An Old Hobby's New Potential",
      "scenario_description": "Looking at your past decision to start a photography side-hustle, a local gallery in New York offers you a spot in an upcoming show. This could be big, but it requires an investment.",
      "choices": [
        {{
          "description": "Go all in: rent professional lighting and print your best work on high-quality canvas. (-$2,500.00)",
          "financial_impact": {{ "action": "WITHDRAWAL", "amount": 2500, "description": "Gallery Show Investment" }}
        }},
        {{
          "description": "Play it safe: use your existing equipment and print on more affordable photo paper. (-$500.00)",
          "financial_impact": {{ "action": "WITHDRAWAL", "amount": 500, "description": "Basic Gallery Show Prep" }}
        }},
        {{
          "description": "Decline the offer and save your money for now. (+$0.00)",
          "financial_impact": {{ "action": "DEPOSIT", "amount": 0, "description": "Declined Opportunity" }}
        }}
      ]
    }}

    Now, based on the provided Player Context, generate a new, unique scenario. Your response must be only the valid JSON object, with no other text or markdown formatting.
    """

    return _call_generative_model(prompt)

def generate_jo(age, income, title, life_events):
    prompt = f"""
    You are a creative writer for a life simulation game called "FinLife".
    Your goal is to generate a realistic job offer or promotion opportunity for a player based on their current situation. 
    The offer should be logically connected to their past life events.

    --- Player Context ---
    Age: {age}
    Current Annual Income: ${income:,.2f}
    Current Job Title: {title}
    Notable Past Life Events: {life_events if life_events else 'None'}
    --------------------

    The scenario must provide two choices: accept the offer or decline it.
    For each choice, you must provide:
    1.  A "description" of the choice. This description MUST end with the resulting annual income in parentheses, formatted like (Income: $<amount>).
    2.  A "financial_impact" JSON object. This object MUST contain an integer "income" and a string "title".
    The income for the "decline" option must be exactly ${income:,.2f}.

    Example Output Format (for a player who completed a 'coding_bootcamp'):
    {{
      "scenario_title": "A New Opportunity",
      "scenario_description": "Thanks to the skills you gained from the coding bootcamp, a tech startup has offered you a position as a Junior Developer.",
      "choices": [
        {{
          "description": "Accept the Junior Developer position. (Income: $75,000.00)",
          "financial_impact": {{ "income": 75000, "title": "Junior Developer" }}
        }},
        {{
          "description": "Decline the offer and continue as a {title}. (Income: ${income:,.2f})",
          "financial_impact": {{ "income": {income}, "title": "{title}" }}
        }}
      ]
    }}

    Now, based on the provided Player Context, generate a new, unique job scenario. Your response must be only the valid JSON object, with no other text or markdown formatting.
    """

    return _call_generative_model(prompt)

def generate_fs(balance, income, loans, history):
    if loans:
        loan_descriptions = [f"'{loan.get('description', '')}' with ${loan.get('remaining_amount', 0):,.2f} remaining" for loan in loans]
        formatted_loans = ", ".join(loan_descriptions)
    else:
        formatted_loans = "None"

    simplified_history = [
        f"Date: {t.get('transaction_date')}, Type: {t.get('type')}, Amount: ${t.get('amount'):,.2f}, Desc: {t.get('description', 'N/A')}"
        for t in history
    ]

    prompt = f"""
    You are a friendly and insightful financial advisor summarizing a person's simulated financial life from the game "FinLife".

    --- Final Player Stats ---
    Final Balance: ${balance:,.2f}
    Final Annual Income: ${income:,.2f}
    Outstanding Loans: {formatted_loans}
    --------------------------

    --- Complete Transaction History ---
    {json.dumps(simplified_history, indent=2)}
    ------------------------------------

    Based on all of the data provided, please perform the following analysis:
    1.  **Financial Persona:** Give the player a descriptive persona title (e.g., "The Cautious Saver", "The Ambitious Investor", "The High-Risk Entrepreneur").
    2.  **Summary:** Write a short, encouraging paragraph summarizing their final balance, annual income, outstanding loans, and financial journey, explaining their persona.
    3.  **Best Decision:** Identify their three best financial decisions from the transaction history. Describe the transactions and explain briefly why they were smart moves.
    4.  **Worst Decision:** Identify their three worst financial decisions from the transaction history. Describe the transactions and explain briefly why they were poor moves.

    Your response must be only a valid JSON object with the keys: "persona_title", "summary", "best_decision", and "worst_decision".
    """

    return _call_generative_model(prompt)