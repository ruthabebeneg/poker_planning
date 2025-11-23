from flask import Flask, render_template, request, redirect, url_for, session
import firebase_admin
from firebase_admin import credentials, firestore
import random, string

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Nécessaire pour utiliser session

# Initialisation Firebase

firebase_key = json.loads(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"))
firebase_admin.initialize_app(cred)
db = firestore.client()

def generate_session_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        organizer = request.form['organizer']
        difficulty = request.form['difficulty']
        rounds = request.form['rounds']
        user_stories = request.form.getlist('userStories')

        session_id = generate_session_id()
        db.collection('sessions').document(session_id).set({
            'organizer': organizer,
            'difficulty': difficulty,
            'rounds': rounds,
            'status': 'waiting',
            'userStories': user_stories
        })

        # Stocker le pseudo dans la session Flask
        session['username'] = organizer
        session['session_id'] = session_id

        return redirect(url_for('waiting', session_id=session_id))
    return render_template('create.html')

@app.route('/join', methods=['GET', 'POST'])
def join():
    if request.method == 'POST':
        code = request.form['code']
        name = request.form['name']
        session_ref = db.collection('sessions').document(code)

        # Vérifier si le code existe
        if not session_ref.get().exists:
            return "Code invalide. Veuillez réessayer."

        # Ajouter le participant
        session_ref.collection('participants').add({'name': name, 'vote': None})

        # Stocker le pseudo dans la session Flask
        session['username'] = name
        session['session_id'] = code

        return redirect(url_for('waiting', session_id=code))
    return render_template('join.html')

@app.route('/waiting/<session_id>')
def waiting(session_id):
    session_ref = db.collection('sessions').document(session_id)
    session_data = session_ref.get().to_dict()
    participants = [p.to_dict() for p in session_ref.collection('participants').stream()]

    return render_template('waiting.html', session_id=session_id, session=session_data, participants=participants, current_user=session.get('username'))

@app.route('/start/<session_id>', methods=['POST'])
def start(session_id):
    # Seul l'organisateur peut lancer la partie
    session_ref = db.collection('sessions').document(session_id)
    session_data = session_ref.get().to_dict()
    if session.get('username') != session_data['organizer']:
        return "Vous n'êtes pas autorisé à lancer la partie."

    session_ref.update({'status': 'started'})
    return redirect(url_for('vote', session_id=session_id))

@app.route('/vote/<session_id>', methods=['GET', 'POST'])
def vote(session_id):
    session_ref = db.collection('sessions').document(session_id)
    session_data = session_ref.get().to_dict()

    if request.method == 'POST':
        vote_value = request.form['vote']
        username = session.get('username')

        # Mettre à jour le vote du participant
        participants_ref = session_ref.collection('participants')
        for p in participants_ref.stream():
            if p.to_dict()['name'] == username:
                p.reference.update({'vote': vote_value})

        return redirect(url_for('vote', session_id=session_id))

    participants = [p.to_dict() for p in session_ref.collection('participants').stream()]
    return render_template('vote.html', session=session_data, participants=participants)

if __name__ == '__main__':
    app.run(debug=True)

