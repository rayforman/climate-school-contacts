import io
import csv
from flask import current_app
from app.models import db, Guest, EventAttendance

def process_attendee_file(file, event_id):
    """
    Process a CSV file with 'First Name' and 'Last Name' columns and add matching guests to the event.
    
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
        'not_found': 0,
        'not_found_names': []
    }
    
    try:
        # Read the CSV file
        content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content))
        
        # Check if required columns exist
        headers = [h for h in csv_reader.fieldnames]
        if 'First Name' not in headers or 'Last Name' not in headers:
            result['message'] = "CSV file must contain 'First Name' and 'Last Name' columns"
            return result
        
        # Process each row
        for row in csv_reader:
            first_name = row['First Name'].strip()
            last_name = row['Last Name'].strip()
            
            # Skip if either name is empty
            if not first_name or not last_name:
                continue
            
            # Look for exact match on first and last name
            guest = Guest.query.filter(
                db.func.lower(Guest.first_name) == first_name.lower(),
                db.func.lower(Guest.last_name) == last_name.lower()
            ).first()
            
            # If guest is not found, add to not found list
            if not guest:
                result['not_found'] += 1
                result['not_found_names'].append(f"{first_name} {last_name}")
                continue
            
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
        current_app.logger.error(f"Error processing attendee file: {str(e)}")
        result['message'] = str(e)
        return result