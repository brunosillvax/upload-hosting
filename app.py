import os
import time
import math
import json
import string
import random
from flask import Flask, request, redirect, url_for, render_template, flash, send_from_directory, jsonify, abort
from flask_apscheduler import APScheduler
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect

# --- Configurações ---
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
DATA_FILE = 'file_data.json'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
FILES_PER_PAGE = 10
AUTO_DELETE_SECONDS = 300  # 5 minutos

app = Flask(__name__)
app.secret_key = 'chave_secreta_segura_aqui'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

csrf = CSRFProtect(app)
scheduler = APScheduler()
scheduler.init_app(app)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({}, f)

# --- Helpers ---

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def random_id(size=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=size))

def allowed_file(filename):
    return '.' in filename

def cleanup_files():
    data = load_data()
    now = time.time()
    changed = False
    to_delete = []

    for short_id, meta in data.items():
        path = os.path.join(UPLOAD_FOLDER, meta['filename'])
        age = now - meta['uploaded_at']
        if age > AUTO_DELETE_SECONDS or not os.path.isfile(path):
            try:
                if os.path.isfile(path):
                    os.remove(path)
                to_delete.append(short_id)
                changed = True
            except Exception as e:
                app.logger.error(f"Erro ao excluir arquivo {path}: {e}")
    
    for sid in to_delete:
        del data[sid]

    if changed:
        save_data(data)

# --- Rotas ---

@app.route('/', methods=['GET', 'POST'])
def index():
    data = load_data()
    search = request.args.get('search', '').lower()
    page = request.args.get('page', 1, type=int)

    # POST: upload arquivos
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nenhum arquivo enviado.', 'error')
            return redirect(request.url)
        files = request.files.getlist('file')
        if not files or all(f.filename == '' for f in files):
            flash('Nenhum arquivo válido selecionado.', 'error')
            return redirect(request.url)

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                base, ext = os.path.splitext(filename)

                # Renomear se já existir arquivo igual
                counter = 1
                final_filename = filename
                while os.path.exists(os.path.join(UPLOAD_FOLDER, final_filename)):
                    final_filename = f"{base}_{counter}{ext}"
                    counter += 1
                
                path = os.path.join(UPLOAD_FOLDER, final_filename)
                file.save(path)

                # Gerar short_id único
                short_id = random_id()
                while short_id in data:
                    short_id = random_id()
                
                data[short_id] = {
                    'filename': final_filename,
                    'uploaded_at': time.time(),
                    'downloads': 0
                }
                app.logger.info(f"Upload: {final_filename} short_id={short_id}")
            else:
                flash(f'Arquivo não permitido: {file.filename}', 'error')

        save_data(data)
        flash('Arquivo(s) enviado(s) com sucesso! Eles serão excluídos após 5 minutos.', 'success')
        return redirect(url_for('index'))

    # GET: listar arquivos paginados e filtrados
    files_list = []
    for sid, meta in data.items():
        if search and search not in meta['filename'].lower():
            continue
        elapsed = time.time() - meta['uploaded_at']
        time_left = max(0, AUTO_DELETE_SECONDS - int(elapsed))
        files_list.append({
            'short_id': sid,
            'filename': meta['filename'],
            'downloads': meta['downloads'],
            'time_left': time_left,
            'uploaded_at': meta['uploaded_at']  # para ordenação correta
        })
    files_list = sorted(files_list, key=lambda x: x['uploaded_at'], reverse=True)

    total_files = len(files_list)
    total_pages = max(1, math.ceil(total_files / FILES_PER_PAGE))
    start = (page - 1) * FILES_PER_PAGE
    end = start + FILES_PER_PAGE
    files_page = files_list[start:end]

    return render_template('index.html',
        files=files_page,
        page=page,
        total_pages=total_pages,
        search=search,
        max_content_length=MAX_CONTENT_LENGTH,
        auto_delete_minutes=AUTO_DELETE_SECONDS // 60
    )

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/s/<short_id>')
def redirect_short(short_id):
    data = load_data()
    if short_id not in data:
        abort(404)
    meta = data[short_id]
    filepath = os.path.join(UPLOAD_FOLDER, meta['filename'])
    if not os.path.isfile(filepath):
        abort(404)

    # Incrementar contador downloads
    meta['downloads'] += 1
    save_data(data)

    return redirect(url_for('uploaded_file', filename=meta['filename']))

# --- API pública ---

@app.route('/api/upload', methods=['POST'])
@csrf.exempt
def api_upload():
    if 'file' not in request.files:
        return jsonify({'status':'error','message':'Nenhum arquivo enviado.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status':'error','message':'Arquivo inválido.'}), 400

    if not allowed_file(file.filename):
        return jsonify({'status':'error','message':'Arquivo não permitido.'}), 400

    filename = secure_filename(file.filename)
    base, ext = os.path.splitext(filename)

    counter = 1
    final_filename = filename
    while os.path.exists(os.path.join(UPLOAD_FOLDER, final_filename)):
        final_filename = f"{base}_{counter}{ext}"
        counter += 1

    path = os.path.join(UPLOAD_FOLDER, final_filename)
    file.save(path)

    data = load_data()
    short_id = random_id()
    while short_id in data:
        short_id = random_id()

    data[short_id] = {
        'filename': final_filename,
        'uploaded_at': time.time(),
        'downloads': 0
    }
    save_data(data)

    return jsonify({
        'status': 'success',
        'message': 'Arquivo enviado com sucesso.',
        'short_id': short_id,
        'url': url_for('redirect_short', short_id=short_id, _external=True)
    })

@app.route('/api/file/<short_id>', methods=['GET'])
def api_file_info(short_id):
    data = load_data()
    if short_id not in data:
        return jsonify({'status': 'error', 'message': 'Arquivo não encontrado.'}), 404

    meta = data[short_id]
    elapsed = time.time() - meta['uploaded_at']
    time_left = max(0, AUTO_DELETE_SECONDS - int(elapsed))

    return jsonify({
        'status': 'success',
        'filename': meta['filename'],
        'downloads': meta['downloads'],
        'time_left_seconds': time_left,
        'url': url_for('redirect_short', short_id=short_id, _external=True)
    })

# ROTA DE EXCLUSÃO SEM CSRF (para botão funcionar via fetch POST)
@app.route('/delete/<filename>', methods=['POST'])
@csrf.exempt
def delete_file(filename):
    data = load_data()
    to_delete = None
    for sid, meta in data.items():
        if meta['filename'] == filename:
            to_delete = sid
            break
    if not to_delete:
        return jsonify({'status':'error','message':'Arquivo não encontrado.'})

    try:
        os.remove(os.path.join(UPLOAD_FOLDER, filename))
        del data[to_delete]
        save_data(data)
        return jsonify({'status':'success','message':'Arquivo excluído com sucesso.'})
    except Exception as e:
        return jsonify({'status':'error','message':'Erro ao excluir arquivo.'})

# --- Tratamento erros ---
@app.errorhandler(413)
def too_large(e):
    flash('Arquivo muito grande. Máximo 16MB.', 'error')
    return redirect(url_for('index'))

# --- Job scheduler ---
@scheduler.task('interval', id='cleanup_job', seconds=60, misfire_grace_time=10)
def scheduled_cleanup():
    cleanup_files()

# --- Rodar app ---
if __name__ == '__main__':
    scheduler.start()
    app.run(debug=True)
