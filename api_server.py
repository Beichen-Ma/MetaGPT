from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
import re
import json
import asyncio
import subprocess

from metagpt.const import RESEARCH_PATH

app = Flask(__name__)
CORS(app)

async def run_command(command):
    """ Run a shell command in subprocess """
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if stderr:
        print(f'Errors: {stderr.decode()}')
    return stdout.decode()

def extract_content_from_markdown(file_path):
    """ Extracts the answer, explanation, and references from a markdown file """
    with open(file_path, 'r') as file:
        content = file.read()
        answer_match = re.search(r'Answer: (Yes|No|Unclear)\n\n', content)
        answer = answer_match.group(1).strip() if answer_match else "Unclear"
        
        explanation_match = re.search(r'Explanation: (.*?)\n\nReferences:', content, re.S)
        explanation = explanation_match.group(1).strip() if explanation_match else "No detailed explanation found."
        
        references_match = re.search(r'References:\n(.*?)$', content, re.S)
        references = references_match.group(1).strip() if references_match else "No references found."
        
        full_content = f"Explanation: {explanation}\n\nReferences: {references}"
        return (answer == "Yes"), full_content

def process_outputs(company_name):
    """ Process markdown outputs and generate structured output """
    topics = [
        "Does the company {} have a human rights policy?".format(company_name),
        "Does the company {} provide human rights/esg training to employees?".format(company_name),
        "Does the company {} track scope 1 emissions?".format(company_name)
    ]
    
    file_names = [
        RESEARCH_PATH / "Does the company {} have a human rights policy .md".format(company_name),
        RESEARCH_PATH / "Does the company {} provide human rights esg training to employees .md".format(company_name),
        RESEARCH_PATH / "Does the company {} track scope 1 emissions .md".format(company_name)
    ]
    
    faqs = []
    for topic, file_name in zip(topics, file_names):
        flag, content = extract_content_from_markdown(file_name)
        faqs.append({
            "label": topic,
            "flag": flag,
            "content": content
        })
    
    return {"faqs": faqs}

@app.route('/analyze', methods=['POST'])
def analyze():
    """ Endpoint to analyze company data """
    data = request.json
    company_name = data.get('company_name')
    if not company_name:
        return jsonify({'error': 'Company name is required'}), 400

    asyncio.run(main(company_name))
    result = process_outputs(company_name)
    return jsonify(result)

async def main(company_name):
    """ Formulate topics and run research commands in parallel """
    topics = [
        f"Does the company {company_name} have a human rights policy?",
        f"Does the company {company_name} provide human rights/esg training to employees?",
        f"Does the company {company_name} track scope 1 emissions?"
    ]
    
    commands = [f'python metagpt/roles/researcher.py "{topic}"' for topic in topics]
    
    # Running the commands in parallel
    await asyncio.gather(*(run_command(cmd) for cmd in commands))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)