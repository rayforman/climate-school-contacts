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
            
            # Try to get additional fields if available
            athena_id = None
            prospect_manager = None
            prefix = None
            middle_name = None
            nickname = None
            descriptor = None
            
            for a_key in ['Athena ID', 'Athena Id', 'athena_id', 'AthenaID', 'Columbia ID', 'columbia_id']:
                if a_key in row and row[a_key]:
                    athena_id = row[a_key].strip()
                    break
                    
            for pm_key in ['Prospect Manager', 'Manager', 'prospect_manager', 'Development Officer', 'development_officer']:
                if pm_key in row and row[pm_key]:
                    prospect_manager = row[pm_key].strip()
                    break
                    
            for p_key in ['Prefix', 'Title', 'prefix', 'name_prefix']:
                if p_key in row and row[p_key]:
                    prefix = row[p_key].strip()
                    break
                    
            for m_key in ['Middle Name', 'middle_name', 'Middle', 'MiddleName']:
                if m_key in row and row[m_key]:
                    middle_name = row[m_key].strip()
                    break
                    
            for n_key in ['Nickname', 'nickname', 'Preferred Name', 'preferred_name']:
                if n_key in row and row[n_key]:
                    nickname = row[n_key].strip()
                    break
                    
            for d_key in ['Descriptor', 'descriptor', 'Suffix', 'suffix', 'Name Suffix', 'name_suffix']:
                if d_key in row and row[d_key]:
                    descriptor = row[d_key].strip()
                    break
            
            # Skip if missing required fields
            if not first_name or not last_name:
                continue
            
            # Check if guest already exists
            guest = None
            
            # First try to find by Athena ID if available
            if athena_id:
                guest = Guest.query.filter_by(athena_id=athena_id).first()
            
            # Then try email
            if not guest and email:
                guest = Guest.query.filter_by(email=email).first()
            
            # Finally try by name
            if not guest:
                name_query = Guest.query.filter_by(
                    first_name=first_name,
                    last_name=last_name
                )
                
                # If we have middle name, use it for more precise matching
                if middle_name:
                    name_query = name_query.filter_by(middle_name=middle_name)
                    
                guest = name_query.first()
            
            # Create new guest if needed
            if not guest:
                guest = Guest(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    athena_id=athena_id,
                    prospect_manager=prospect_manager,
                    prefix=prefix,
                    middle_name=middle_name,
                    nickname=nickname,
                    descriptor=descriptor,
                    # Set a default user_id to the first admin user or user with ID 1
                    user_id=1  # This should be replaced with an appropriate user_id
                )
                db.session.add(guest)
                db.session.flush()  # Get ID without committing
            else:
                # Update with any new information if we found an existing guest
                if email and not guest.email:
                    guest.email = email
                if athena_id and not guest.athena_id:
                    guest.athena_id = athena_id
                if prospect_manager and not guest.prospect_manager:
                    guest.prospect_manager = prospect_manager
                if prefix and not guest.prefix:
                    guest.prefix = prefix
                if middle_name and not guest.middle_name:
                    guest.middle_name = middle_name
                if nickname and not guest.nickname:
                    guest.nickname = nickname
                if descriptor and not guest.descriptor:
                    guest.descriptor = descriptor
            
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