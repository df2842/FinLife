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

def generate_mcq(name, age, date, balance, income, life_events, specifier="N/A"):
    prompt = f"""
    You are a creative writer for a life simulation game called "FinLife".
    
    Your goal is to generate a single, nuanced financial dilemma based on {name}'s current situation.
    If specified, the dilemma absolutely must focus on {specifier}. No exceptions.
    The current date in the simulation is {date}.
    The choices should focus on one-time financial events, investments, or unique opportunities, NOT steady sources of income. 
    
    The dilemma must be relevant to the player's context.

    --- Player Context ---
    Name: {name}
    Age: {age}
    Current Checking Balance: ${balance:,.2f}
    Yearly Income: ${income:,.2f}
    Notable Past Life Events: {life_events if life_events else 'None'}
    --------------------

    The scenario must have three distinct choices. For each choice, you must provide:
    1.  A "description" of the choice. This description MUST end with a parenthesized summary of the financial impact. 
        - For DEPOSIT, use (+$<amount>).
        - For WITHDRAWAL, use (-$<amount>).
    2.  A "financial_impact" JSON object. This object MUST contain a string "action", an integer "amount", and a string "description".
        The action must be one of: ["DEPOSIT", "WITHDRAWAL"].

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

def generate_jo(name, age, income, title, life_events):
    prompt = f"""
    You are a creative writer for a life simulation game called "FinLife".
    Your goal is to generate a realistic job offer or promotion opportunity for {name} based on their current situation. 
    The offer should be logically connected to their past life events.

    --- Player Context ---
    Name: {name}
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

def generate_fs(name, balance, income, history):
    simplified_history = [
        f"Date: {t.get('transaction_date')}, Type: {t.get('type')}, Amount: ${t.get('amount'):,.2f}, Desc: {t.get('description', 'N/A')}"
        for t in history
    ]

    prompt = f"""
    You are a friendly and insightful financial advisor summarizing {name}'s simulated financial life from the game "FinLife".

    --- Final Player Stats ---
    Name: {name}
    Final Balance: ${balance:,.2f}
    Final Annual Income: ${income:,.2f}
    --------------------------

    --- Complete Transaction History ---
    {json.dumps(simplified_history, indent=2)}
    ------------------------------------

    Based on all of the data provided, please perform the following analysis:
    1.  **Financial Persona:** Give the player a descriptive persona title (e.g., "The Cautious Saver", "The Ambitious Investor", "The High-Risk Entrepreneur").
    2.  **Summary:** Write a short, encouraging paragraph summarizing their financial journey, explaining their persona. Do not show the final balance or income.
    3.  **Best Decision:** Identify their best financial decisions from the transaction history. Describe the transactions and explain briefly why they were smart moves in sentences.
    4.  **Worst Decision:** Identify their worst financial decisions from the transaction history. Describe the transactions and explain briefly why they were poor moves in sentences.

    Your response must be only a valid JSON object with the keys: "persona_title", "summary", "best_decision", and "worst_decision".
    """

    return _call_generative_model(prompt)