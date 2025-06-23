from flask import Blueprint, request, jsonify
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
# import torch
import re
import os
import requests
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("idyie-llm")

llm_bp = Blueprint('llm', __name__)

MODEL_NAME = "tscholak/3vnuv1vf"
logger.info("Loading model: %s", MODEL_NAME)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
logger.info("Model loaded successfully.")

# Simple in-memory cache
schema_cache = {
    "schema": None,
    "timestamp": 0,
    "parsed_schema": None
}
CACHE_TTL_SECONDS = 300  # 5 minutes

STRICT_MODE = True  # fail hard if hallucination detected


def get_schema_from_db():
    global schema_cache
    now = time.time()

    if schema_cache["schema"] and now - schema_cache["timestamp"] < CACHE_TTL_SECONDS:
        logger.info("Using cached schema")
        return schema_cache["schema"], schema_cache["parsed_schema"]

    api_ip = os.getenv('IDYIE_API_URL', "http://idyie-api-application:8080")
    url = f"{api_ip}/api/v1/database/schema"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        raw_schema = response.json().get('schema')
        if not raw_schema:
            raise ValueError("Schema not found in response")

        schema_text, parsed_schema = convert_schema_to_prompt(raw_schema)
        schema_cache = {"schema": schema_text, "parsed_schema": parsed_schema, "timestamp": now}
        logger.info("Fetched and cached new schema")
        return schema_text, parsed_schema

    except Exception as e:
        logger.error("Failed to fetch schema: %s", e)
        raise RuntimeError("Could not retrieve database schema") from e


def convert_schema_to_prompt(raw_schema_text):
    schema_lines = []
    parsed_schema = {}

    tables = re.findall(r'CREATE TABLE `(\w+)` \((.*?)\) ENGINE=', raw_schema_text, re.DOTALL)
    for table_name, columns_raw in tables:
        columns = []
        parsed_schema[table_name] = []
        for line in columns_raw.strip().split("\n"):
            line = line.strip().strip(',')
            col_match = re.match(r'`(\w+)`\s+([a-zA-Z0-9()]+)', line)
            if col_match:
                col_name = col_match.group(1)
                col_type = simplify_sql_type(col_match.group(2))
                columns.append(f"{col_name} {col_type}")
                parsed_schema[table_name].append((col_name, col_type))
        columns_str = ", ".join(columns)
        schema_lines.append(f"Table {table_name}({columns_str})")

    return "\n".join(schema_lines), parsed_schema


def simplify_sql_type(sql_type):
    sql_type = sql_type.lower()
    if "tinyint" in sql_type:
        return "boolean"
    elif "int" in sql_type:
        return "int"
    elif "varchar" in sql_type or "char" in sql_type or "text" in sql_type:
        return "varchar"
    elif "timestamp" in sql_type or "datetime" in sql_type:
        return "timestamp"
    else:
        return "text"


def build_few_shot_prompt(parsed_schema, user_prompt):
    examples = []
    variants = [
        ("active", [
            "Get active {table}", "Get all active {table}", "Show active {table}", "List active {table}",
            "Retrieve active {table}"
        ]),
        ("inactive", [
            "Get inactive {table}", "Get all inactive {table}", "Show inactive {table}", "List inactive {table}",
            "Retrieve inactive {table}"
        ])
    ]

    for table, columns in parsed_schema.items():
        examples.append("Example:")
        examples.append(f"User query: Get all {table}")
        examples.append(f"SQL: SELECT * FROM {table};\n")

        for col_name, col_type in columns:
            if col_type == "boolean":
                for label, prompts in variants:
                    for phrasing in prompts:
                        condition = "TRUE" if label == "active" else "FALSE"
                        examples.append("Example:")
                        examples.append(f"User query: {phrasing.format(table=table)}")
                        examples.append(f"SQL: SELECT * FROM {table} WHERE {col_name} = {condition};\n")

    few_shot_text = "\n".join(examples)

    prompt = (
        "You are a professional data engineer. Generate valid SQL queries based strictly on the provided schema."
        "Only use tables and columns that exist. "
        "Do not invent any fields or tables. "
        "Always return clean SQL starting with SELECT.\n\n"
        "Schema:\n"
    )

    for table, columns in parsed_schema.items():
        columns_str = ", ".join([f"{col} {typ}" for col, typ in columns])
        prompt += f"Table {table}({columns_str})\n"

    prompt += f"\n{few_shot_text}\n\nUser query: {user_prompt}\nSQL:"
    return prompt


def generate_sql_with_llm(user_prompt, schema_text, parsed_schema):
    full_prompt = build_few_shot_prompt(parsed_schema, user_prompt)

    logger.info("Full prompt:\n%s", full_prompt)

    inputs = tokenizer(
        full_prompt,
        max_length=1024,
        padding=True,
        truncation=True,
        return_tensors="pt"
    )

    outputs = model.generate(
        inputs["input_ids"],
        max_length=256,
        min_length=5,
        num_beams=5,
        do_sample=False,
        early_stopping=True,
    )

    sql = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    logger.info("Raw model output: %s", sql)
    return sql


def clean_sql(sql):
    sql = re.sub(r'(?i)(FROM|JOIN)\s+t\d+\.', r'\1 ', sql)
    sql = sql.replace("active = 'T'", "active = TRUE")
    sql = sql.replace("active = 'F'", "active = FALSE")
    sql = sql.replace("active = '1'", "active = TRUE")
    sql = sql.replace("active = 1", "active = TRUE")
    sql = sql.replace("active = '0'", "active = FALSE")
    sql = sql.replace("active = 0", "active = FALSE")
    return sql.strip()


def validate_sql(sql, parsed_schema):
    if not sql.upper().startswith("SELECT"):
        raise ValueError("Generated SQL does not start with SELECT")

    used_tables = set(re.findall(r'FROM\s+(\w+)', sql, re.IGNORECASE))
    used_tables.update(re.findall(r'JOIN\s+(\w+)', sql, re.IGNORECASE))

    known_tables = set(parsed_schema.keys())
    unknown_tables = used_tables - known_tables

    if unknown_tables:
        logger.warning("Unknown tables detected in SQL: %s", unknown_tables)
        if STRICT_MODE:
            raise ValueError(f"Unknown tables in SQL: {unknown_tables}")


@llm_bp.route('/api/get_query', methods=['POST'])
def get_query():
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({'error': 'No prompt provided'}), 400

    prompt = data['prompt']
    logger.info("Received prompt: %s", prompt)

    try:
        schema_text, parsed_schema = get_schema_from_db()
        raw_sql = generate_sql_with_llm(prompt, schema_text, parsed_schema)
        cleaned_sql = clean_sql(raw_sql)
        validate_sql(cleaned_sql, parsed_schema)
        if not cleaned_sql.endswith(";"):
            cleaned_sql += ";"

        logger.info("Validated SQL: %s", cleaned_sql)

        return jsonify({
            'prompt': prompt,
            'sql_query': cleaned_sql,
            'source': 'llm'
        })

    except Exception as e:
        logger.exception("Error processing prompt")
        return jsonify({'error': str(e), 'message': 'Failed to generate valid SQL query'}), 500
