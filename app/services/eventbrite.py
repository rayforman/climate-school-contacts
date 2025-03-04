import io
import csv
from werkzeug.utils import secure_filename
from flask import current_app
from app.models import db, Guest, EventAttendance

def process_eventbrite_file(file, event_id):
    """
    Process an Eventbrite attendee CSV file and add guests to the event.
    Simplified version without pandas.
    
    Args:
        file: FileStorage object containing the CSV file
        event_id: ID of the event to add attendees to
        
    Returns:
        dict: Results of the import operation
    """
    result = {
        'success': False,
        'added': 0,
        'existing': 0,
        'message': ''
    }
    
    try:
        # Read the CSV file
        content = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        
        # Process each row
        for row in reader:
            # Try to get the necessary fields
            first_name = None
            last_name = None
            email = None
            
            # Check various possible column names
            for fn_key in ['First Name', 'First name', 'Attendee First Name', 'first_name', 'firstname']:
                if fn_key in row:
                    first_name = row[fn_key].strip()
                    break
                    
            for ln_key in ['Last Name', 'Last name', 'Attendee Last Name', 'last_name', 'lastname', 'surname']:
                if ln_key in row:
                    last_name = row[ln_key].strip()
                    break
                    
            for e_key in ['Email', 'Attendee Email', 'email', 'Email Address', 'email_address']:
                if e_key in row:
                    email = row[e_key].strip()
                    break
            
            # Skip if missing required fields
            if not first_name or not last_name:
                continue
            
            # Check if guest already exists
            guest = None
            if email:
                guest = Guest.query.filter_by(email=email).first()
            
            if not guest:
                # Try to find by name
                guest = Guest.query.filter_by(
                    first_name=first_name,
                    last_name=last_name
                ).first()
            
            # Create new guest if needed
            if not guest:
                guest = Guest(
                    first_name=first_name,
                    last_name=last_name,
                    email=email
                )
                db.session.add(guest)
                db.session.flush()  # Get ID without committing
            
            # Check if already attending this event
            attendance = EventAttendance.query.filter_by(
                event_id=event_id,
                guest_id=guest.id
            ).first()
            
            if attendance:
                result['existing'] += 1
            else:
                # Add to event
                attendance = EventAttendance(
                    event_id=event_id,
                    guest_id=guest.id
                )
                db.session.add(attendance)
                result['added'] += 1
        
        # Commit all changes
        db.session.commit()
        
        result['success'] = True
        return result
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing Eventbrite file: {str(e)}")
        result['message'] = str(e)
        return result