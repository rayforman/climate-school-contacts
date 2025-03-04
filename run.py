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

if __name__ == '__main__':
    app.run(debug=True)