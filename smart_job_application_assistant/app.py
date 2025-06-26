from flask import Flask, request, render_template, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.secret_key = 'your_secret_key_here'  # Replace with a real secret key

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('signup'))
    elif 'logged_in' not in session:
        return redirect(url_for('login'))
    elif 'resume_uploaded' not in session:
        return redirect(url_for('upload_page'))
    else:
        return redirect(url_for('browse'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Here you would typically process the signup form and create a new user
        session['user'] = request.form.get('email')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Here you would typically verify the user's credentials
        if request.form.get('email') == session.get('user'):
            session['logged_in'] = True
            return redirect(url_for('upload_page'))
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/upload_page')
def upload_page():
    if 'user' not in session or 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('upload_page.html')

@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'user' not in session or 'logged_in' not in session:
        return jsonify({'error': 'User not logged in'})
    
    if 'resume' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        session['resume_uploaded'] = True
        return jsonify({'success': f'File {filename} uploaded successfully!'})

@app.route('/browse')
def browse():
    if 'user' not in session or 'logged_in' not in session:
        return redirect(url_for('login'))
    if 'resume_uploaded' not in session:
        return redirect(url_for('upload_page'))
    return render_template('browse.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('signup'))

if __name__ == '__main__':
    app.run(debug=True)