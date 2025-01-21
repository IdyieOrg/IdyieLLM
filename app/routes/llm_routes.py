from flask import Blueprint, request, jsonify
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import re

llm_bp = Blueprint('llm', __name__)

# Load the model for complex queries
MODEL_NAME = "tscholak/3vnuv1vf"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)

# Define templates for common queries
QUERY_TEMPLATES = {
    "active_users": {
        "patterns": [
            r"(?i).*\b(get|show|select|find)\b.*\bactive\b.*\busers?\b.*",
            r"(?i).*\busers?\b.*\bactive\b.*"
        ],
        "sql": "SELECT * FROM users WHERE active = TRUE"
    },
    "inactive_users": {
        "patterns": [
            r"(?i).*\b(get|show|select|find)\b.*\binactive\b.*\busers?\b.*",
            r"(?i).*\busers?\b.*\binactive\b.*"
        ],
        "sql": "SELECT * FROM users WHERE active = FALSE"
    },
    "all_users": {
        "patterns": [
            r"(?i).*\b(get|show|select|find)\b.*\ball\b.*\busers?\b.*",
            r"(?i).*\busers?\b.*\ball\b.*"
        ],
        "sql": "SELECT * FROM users"
    }
}


def match_template(prompt):
    """
    Try to match the prompt against predefined templates
    """
    for template_name, template in QUERY_TEMPLATES.items():
        for pattern in template["patterns"]:
            if re.match(pattern, prompt):
                return template["sql"]
    return None


def generate_ml_sql(prompt):
    """
    Generate SQL using the ML model for complex queries
    """
    schema = """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            email TEXT,
            created_at TIMESTAMP,
            active BOOLEAN
        );
    """

    full_prompt = f"Schema: {schema}\nQuery: {prompt}\nSQL:"

    # Tokenize
    inputs = tokenizer(
        full_prompt,
        max_length=512,
        padding=True,
        truncation=True,
        return_tensors="pt"
    )

    # Generate with corrected parameters
    outputs = model.generate(
        inputs["input_ids"],
        max_length=128,
        min_length=5,
        num_beams=5,
        do_sample=True,  # Enable sampling
        temperature=0.3,
        top_p=0.95,
        early_stopping=True,
    )

    sql = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    return sql


def clean_sql(sql):
    """
    Clean and validate the generated SQL
    """
    # Fix boolean values
    sql = sql.replace("active = '1'", "active = TRUE")
    sql = sql.replace("active = 1", "active = TRUE")
    sql = sql.replace("active = '0'", "active = FALSE")
    sql = sql.replace("active = 0", "active = FALSE")
    sql = sql.replace("active = boolean", "active = TRUE")

    # Remove schema references
    sql = re.sub(r't\d+\.schema:.*?(?=WHERE|$)', '', sql)

    # Fix improper joins
    sql = re.sub(r'FROM users.*?(?=WHERE|$)', 'FROM users ', sql)

    # Ensure basic SQL structure
    if not sql.upper().startswith("SELECT"):
        sql = f"SELECT * FROM users WHERE {sql}"

    return sql.strip()


@llm_bp.route('/api/get_query', methods=['POST'])
def get_query():
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({'error': 'No prompt provided'}), 400

    try:
        # First try template matching
        sql_query = match_template(data['prompt'])
        source = "template"

        # If no template matches, use ML model
        if not sql_query:
            sql_query = generate_ml_sql(data['prompt'])
            sql_query = clean_sql(sql_query)
            source = "ml"

        return jsonify({
            'prompt': data['prompt'],
            'sql_query': sql_query,
            'source': source
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to generate SQL query'
        }), 500
