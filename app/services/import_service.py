import io
import csv
from flask import current_app
from sqlalchemy import func
from app.models import db, Guest, EventAttendance

def process_attendee_file(file, event_id):
    """
    Process an Excel or CSV file with attendee information.
    Handles multiple file formats and encodings.
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
        # Save the uploaded file to a temporary location
        import tempfile
        import pandas as pd
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp:
            file.save(temp.name)
            temp_path = temp.name
        
        # Try to determine file type from extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        try:
            # Read based on file type
            if file_ext in ['.xlsx', '.xls']:
                print(f"Reading as Excel file: {file.filename}")
                df = pd.read_excel(temp_path, engine='openpyxl')
            else:
                # Try multiple encodings for CSV
                encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
                df = None
                
                for encoding in encodings:
                    try:
                        print(f"Trying CSV with encoding: {encoding}")
                        df = pd.read_csv(temp_path, encoding=encoding, sep=None, engine='python')
                        print(f"Successfully read with encoding: {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                    
                if df is None:
                    raise Exception("Could not decode the file with any supported encoding")
        
            print(f"Columns found: {df.columns.tolist()}")
            
        except Exception as read_error:
            print(f"Error reading file: {str(read_error)}")
            result['message'] = f"Error reading file: {str(read_error)}"
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return result
        
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        
        # Check if dataframe is empty
        if df.empty:
            result['message'] = "The uploaded file contains no data"
            return result
        
        # Check for required columns
        if 'First Name' not in df.columns or 'Last Name' not in df.columns:
            result['message'] = f"Required columns 'First Name' and 'Last Name' not found. Available columns: {df.columns.tolist()}"
            return result
        
        # Process each row in the dataframe
        for _, row in df.iterrows():
            first_name = str(row['First Name']).strip() if pd.notna(row['First Name']) else ''
            last_name = str(row['Last Name']).strip() if pd.notna(row['Last Name']) else ''
            
            # Skip if either name is empty
            if not first_name or not last_name or first_name.lower() == 'nan' or last_name.lower() == 'nan':
                print(f"Skipping row with empty name: {first_name} {last_name}")
                continue
                
            print(f"Processing: {first_name} {last_name}")
                
            # Find matching guest
            guest = Guest.query.filter(
                Guest.first_name.ilike(first_name),
                Guest.last_name.ilike(last_name)
            ).first()
            
            if not guest:
                result['not_found'] += 1
                result['not_found_names'].append(f"{first_name} {last_name}")
                print(f"Guest not found: {first_name} {last_name}")
                continue
            
            print(f"Found guest: {guest.full_name}")    
                
            # Check if already attending
            attendance = EventAttendance.query.filter_by(
                event_id=event_id,
                guest_id=guest.id
            ).first()
            
            if attendance:
                result['existing'] += 1
                print(f"Guest already attending: {first_name} {last_name}")
            else:
                # Add to event
                attendance = EventAttendance(
                    event_id=event_id,
                    guest_id=guest.id
                )
                db.session.add(attendance)
                result['added'] += 1
                print(f"Added guest to event: {first_name} {last_name}")
        
        # Commit all changes
        db.session.commit()
        
        result['success'] = True
        print(f"Import complete: {result['added']} added, {result['existing']} existing, {result['not_found']} not found")
        return result
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: {str(e)}")
        result['message'] = str(e)
        return result
    

import io
import pandas as pd
import tempfile
import os

from flask import current_app
from sqlalchemy import func
from app.models import db, Guest, User

def process_guest_import_file(file, user_id):
    """
    Process an Excel file to import new guests to the database.
    
    Args:
        file: File object from the upload
        user_id: ID of the current user to associate guests with
    
    Returns:
        dict: Import results with details about the import process
    """
    result = {
        'success': False,
        'added': 0,
        'existing': 0,
        'total_rows': 0,
        'message': '',
        'skipped_names': []
    }
    
    try:
        # Save the uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp:
            file.save(temp.name)
            temp_path = temp.name
        
        # Try to determine file type from extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        try:
            # Read based on file type
            if file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(temp_path, engine='openpyxl')
            else:
                # Try multiple encodings for CSV
                encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
                df = None
                
                for encoding in encodings:
                    try:
                        df = pd.read_csv(temp_path, encoding=encoding, sep=None, engine='python')
                        break
                    except UnicodeDecodeError:
                        continue
                    
                if df is None:
                    raise Exception("Could not decode the file with any supported encoding")
            
        except Exception as read_error:
            result['message'] = f"Error reading file: {str(read_error)}"
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return result
        
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        
        # Check if dataframe is empty
        if df.empty:
            result['message'] = "The uploaded file contains no data"
            return result
        
        # Mapping of likely column names to model attributes
        column_mapping = {
            'first_name': ['first name', 'firstname', 'fname'],
            'last_name': ['last name', 'lastname', 'lname'],
            'email': ['email', 'e-mail', 'email address'],
            'prefix': ['prefix', 'title'],
            'middle_name': ['middle name', 'middlename'],
            'nickname': ['nickname', 'nicknames', 'other names'],
            'descriptor': ['descriptor', 'suffix'],
            'phone': ['phone', 'phone number', 'mobile', 'contact number'],
            'organization': ['organization', 'company', 'org'],
            'title': ['job title', 'position', 'role'],
            'athena_id': ['athena id', 'columbia id', 'university id'],
            'prospect_manager': ['prospect manager', 'development officer'],
            'donor_capacity': ['donor capacity', 'giving level', 'capacity'],
            'bio': ['bio', 'biography', 'description'],
            'notes': ['notes', 'additional info', 'comments']
        }
        
        # Find the actual column names in the dataframe
        def find_column(possible_names):
            for name in possible_names:
                col = [col for col in df.columns if name.lower() in col.lower()]
                if col:
                    return col[0]
            return None
        
        # Map columns to our expected fields
        mapped_columns = {}
        for model_field, possible_names in column_mapping.items():
            matched_col = find_column(possible_names)
            if matched_col:
                mapped_columns[model_field] = matched_col
        
        # Prepare for import
        result['total_rows'] = len(df)
        
        for _, row in df.iterrows():
            # Skip rows without a first name or last name
            first_name = row.get(mapped_columns.get('first_name', ''), '')
            last_name = row.get(mapped_columns.get('last_name', ''), '')
            
            # Convert to string and strip whitespace
            first_name = str(first_name).strip() if pd.notna(first_name) else ''
            last_name = str(last_name).strip() if pd.notna(last_name) else ''
            
            # Skip if either name is empty
            if not first_name or not last_name or first_name.lower() == 'nan' or last_name.lower() == 'nan':
                result['skipped_names'].append(f"{first_name} {last_name}")
                continue
            
            # Check if guest already exists (case-insensitive)
            existing_guest = Guest.query.filter(
                func.lower(Guest.first_name) == func.lower(first_name),
                func.lower(Guest.last_name) == func.lower(last_name)
            ).first()
            
            if existing_guest:
                result['existing'] += 1
                continue
            
            # Prepare guest data
            guest_data = {
                'first_name': first_name,
                'last_name': last_name,
                'user_id': user_id
            }
            
            # Add optional fields if they exist in the mapping
            optional_fields = [
                'email', 'prefix', 'middle_name', 'nickname', 'descriptor', 
                'phone', 'organization', 'title', 'athena_id', 
                'prospect_manager', 'donor_capacity', 'bio', 'notes'
            ]
            
            for field in optional_fields:
                mapped_col = mapped_columns.get(field)
                if mapped_col:
                    value = row.get(mapped_col)
                    if pd.notna(value):
                        guest_data[field] = str(value).strip()
            
            # Create new guest
            guest = Guest(**guest_data)
            db.session.add(guest)
            result['added'] += 1
        
        # Commit all changes
        db.session.commit()
        
        result['success'] = True
        return result
        
    except Exception as e:
        db.session.rollback()
        result['message'] = str(e)
        return result