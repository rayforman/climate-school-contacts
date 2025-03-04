from app import create_app, db
from app.models import User, Guest, Event, EventAttendance

app = create_app()

@app.shell_context_processor
def make_shell_context():
    """Make objects available in the Flask shell context."""
    return {
        'db': db,
        'User': User, 
        'Guest': Guest, 
        'Event': Event,
        'EventAttendance': EventAttendance
    }

@app.route('/')
def index():
    """Render the home page."""
    from flask import render_template
    return render_template('index.html', title='Home')

if __name__ == '__main__':
    app.run(debug=True)