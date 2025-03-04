import pandas as pd
import io
from werkzeug.utils import secure_filename
from flask import current_app
from app.models import db, Guest, EventAttendance

def process_eventbrite_file(file, event_id):
    """
    Process an Eventbrite attendee CSV file and add guests to the event.
    
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
        content = file.read()
        file.seek(0)  # Reset file pointer for potential future reads
        
        # Try to read with different encodings if needed
        try:
            df = pd.read_csv(io.BytesIO(content))
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(content), encoding='latin1')
        
        # Check for required columns
        required_columns = ['First Name', 'Last Name', 'Email']
        
        # Try different column naming conventions if needed
        if not all(col in df.columns for col in required_columns):
            # Check for alternate column names (Eventbrite sometimes uses different names)
            alternate_first_name = ['First name', 'Attendee First Name', 'first_name', 'firstname']
            alternate_last_name = ['Last name', 'Attendee Last Name', 'last_name', 'lastname', 'surname']
            alternate_email = ['Attendee Email', 'email', 'Email Address', 'email_address']
            
            # Map standard column names to alternates that exist in the file
            column_mapping = {}
            
            for alternatives, standard in [
                (alternate_first_name, 'First Name'),
                (alternate_last_name, 'Last Name'),
                (alternate_email, 'Email')
            ]:
                for alt in alternatives:
                    if alt in df.columns:
                        column_mapping[alt] = standard
                        break
            
            # If we found mappings, rename the columns
            if len(column_mapping) == len(required_columns):
                df = df.rename(columns=column_mapping)
            else:
                missing = [col for col in required_columns if col not in df.columns]
                result['message'] = f"CSV format is not supported. Missing columns: {', '.join(missing)}"
                return result
        
        # Process each row
        for _, row in df.iterrows():
            first_name = row['First Name']
            last_name = row['Last Name']
            email = row['Email']
            
            # Skip empty rows
            if pd.isna(first_name) or pd.isna(last_name):
                continue
            
            # Clean up the data
            first_name = str(first_name).strip()
            last_name = str(last_name).strip()
            email = str(email).strip() if not pd.isna(email) else None
            
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