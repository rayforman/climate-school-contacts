from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user

from app.models import db
from app.services.import_service import process_guest_import_file

guests_import_bp = Blueprint('guests_import', __name__, url_prefix='/guests/import')

@guests_import_bp.route('/', methods=['GET', 'POST'])
@login_required
def import_guests():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and (file.filename.endswith('.csv') or file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            # Process the guest import file
            result = process_guest_import_file(file, current_user.id)
            
            if result['success']:
                message = f"Successfully added {result['added']} new guests to your database."
                if result['existing'] > 0:
                    message += f" {result['existing']} guests were already in the database and skipped."
                
                flash(message, 'success')
                
                # Display information about rows not imported
                if result['total_rows'] > (result['added'] + result['existing']):
                    skipped_message = f"{result['total_rows'] - (result['added'] + result['existing'])} rows could not be imported."
                    if result.get('skipped_names'):
                        # Show up to 5 skipped names
                        if len(result['skipped_names']) <= 5:
                            skipped_message += " Skipped names: " + ", ".join(result['skipped_names'])
                        else:
                            skipped_message += " Skipped names: " + ", ".join(result['skipped_names'][:5]) + f" and {len(result['skipped_names']) - 5} more"
                    
                    flash(skipped_message, 'warning')
                
                return redirect(url_for('guests.index'))
            else:
                flash(f"Error importing guests: {result.get('message', 'Unknown error')}", 'danger')
        else:
            flash('Invalid file format. Please upload a CSV or Excel file.', 'danger')
    
    return render_template('guests/import.html', title="Import Guests")