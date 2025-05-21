import os
from flask import Blueprint, request, jsonify, abort, current_app
from jinja2 import Environment

TEMPLATE_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../email_templates_storage'))

templates_api = Blueprint('templates_api', __name__)

def allowed_template_name(name):
    # Only allow alphanumeric, dash, underscore, dot
    import re
    return re.match(r'^[\w\-.]+$', name)

def get_template_path(name):
    return os.path.join(TEMPLATE_FOLDER, f"{name}.html")

@templates_api.route('/api/email/templates', methods=['GET'])
def list_templates():
    files = [f[:-5] for f in os.listdir(TEMPLATE_FOLDER) if f.endswith('.html')]
    return jsonify({'templates': files})

@templates_api.route('/api/email/templates/<name>', methods=['GET'])
def get_template(name):
    if not allowed_template_name(name):
        abort(400, 'Invalid template name')
    path = get_template_path(name)
    if not os.path.exists(path):
        abort(404, 'Template not found')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    return jsonify({'name': name, 'content': content})

@templates_api.route('/api/email/templates', methods=['POST'])
def create_template():
    data = request.get_json()
    name = data.get('name')
    content = data.get('content')
    if not allowed_template_name(name):
        abort(400, 'Invalid template name')
    path = get_template_path(name)
    if os.path.exists(path):
        abort(409, 'Template already exists')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({'success': True})

@templates_api.route('/api/email/templates/<name>', methods=['PUT'])
def update_template(name):
    if not allowed_template_name(name):
        abort(400, 'Invalid template name')
    data = request.get_json()
    content = data.get('content')
    path = get_template_path(name)
    if not os.path.exists(path):
        abort(404, 'Template not found')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({'success': True})

@templates_api.route('/api/email/templates/<name>', methods=['DELETE'])
def delete_template(name):
    if not allowed_template_name(name):
        abort(400, 'Invalid template name')
    path = get_template_path(name)
    if not os.path.exists(path):
        abort(404, 'Template not found')
    os.remove(path)
    return jsonify({'success': True})

@templates_api.route('/api/email/preview-template', methods=['POST'])
def preview_template():
    data = request.get_json()
    html_content = data.get('html_template_content')
    subject_template = data.get('subject_template')
    sample_data = data.get('sample_data', {})
    env = Environment()
    try:
        rendered_subject = env.from_string(subject_template).render(sample_data)
        rendered_body = env.from_string(html_content).render(sample_data)
        return jsonify({'rendered_subject': rendered_subject, 'rendered_body': rendered_body})
    except Exception as e:
        abort(400, f'Jinja2 render error: {e}')
