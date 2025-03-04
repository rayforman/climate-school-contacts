from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_file
from flask_login import login_required
import os
import tempfile

from app.models import Event
from app.services.reports import generate_bio_sheet

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/', methods=['GET'])
@login_required
def index():
    events = Event.query.order_by(Event.date.desc()).all()
    return render_template('reports/index.html', title='Reports', events=events)

@reports_bp.route('/bio-sheet/<int:event_id>', methods=['GET'])
@login_required
def bio_sheet(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Generate the bio sheet
    try:
        output_file = generate_bio_sheet(event_id)
        
        # Send the file for download
        return send_file(
            output_file,
            as_attachment=True,
            download_name=f"Bio Sheet - {event.name}.docx",
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        current_app.logger.error(f"Error generating bio sheet: {str(e)}")
        flash(f"Error generating bio sheet: {str(e)}", 'danger')
        return redirect(url_for('reports.index'))