import io
import csv
from flask import current_app
from sqlalchemy import func
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
        'not_found_names': [],
        'message': ''
    }
    
    try:
        # Read the CSV file
        content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content))
        
        # Detailed column logging
        current_app.logger.info(f"CSV Column names: {csv_reader.fieldnames}")
        
        # Find First Name and Last Name columns (case-insensitive and handle potential duplicates)
        first_name_cols = [col for col in csv_reader.fieldnames if 'first name' in col.lower()]
        last_name_cols = [col for col in csv_reader.fieldnames if 'last name' in col.lower()]
        
        # Validate columns
        if not first_name_cols or not last_name_cols:
            result['message'] = f"CSV must contain 'First Name' columns. Found: {csv_reader.fieldnames}"
            current_app.logger.error(result['message'])
            return result
        
        # Use the first matching column
        first_name_col = first_name_cols[0]
        last_name_col = last_name_cols[0]
        
        current_app.logger.info(f"Using columns: {first_name_col} for First Name, {last_name_col} for Last Name")
        
        # Log all guests in the database for debugging
        all_guests = Guest.query.all()
        current_app.logger.info("Database guests:")
        for guest in all_guests:
            current_app.logger.info(f"Guest: {guest.first_name} {guest.last_name}")
        
        # Process each row
        for row in csv_reader:
            first_name = str(row[first_name_col]).strip()
            last_name = str(row[last_name_col]).strip()
            
            # Skip if either name is empty
            if not first_name or not last_name or first_name == 'nan' or last_name == 'nan':
                continue
            
            current_app.logger.info(f"Processing attendee: '{first_name}' '{last_name}'")
            
            # Look for guest with exact case-insensitive first and last name match
            # Use a more flexible query that handles potential extra whitespace
            guest = Guest.query.filter(
                func.lower(func.trim(Guest.first_name)) == func.lower(first_name),
                func.lower(func.trim(Guest.last_name)) == func.lower(last_name)
            ).first()
            
            # If guest is not found, add to not found list
            if not guest:
                result['not_found'] += 1
                result['not_found_names'].append(f"{first_name} {last_name}")
                current_app.logger.warning(f"Guest not found: '{first_name}' '{last_name}'")
                continue
            
            # Check if already attending this event
            attendance = EventAttendance.query.filter_by(
                event_id=event_id,
                guest_id=guest.id
            ).first()
            
            if attendance:
                result['existing'] += 1
                current_app.logger.info(f"Guest {first_name} {last_name} already on the attendee list")
            else:
                # Add to event
                attendance = EventAttendance(
                    event_id=event_id,
                    guest_id=guest.id
                )
                db.session.add(attendance)
                result['added'] += 1
                current_app.logger.info(f"Added guest {first_name} {last_name} to event")
        
        # Commit all changes
        db.session.commit()
        
        result['success'] = True
        return result
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing attendee file: {str(e)}")
        result['message'] = str(e)
        return result