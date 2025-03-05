import io
import pandas as pd
import tempfile
import os
import datetime

from flask import current_app
from sqlalchemy import func
from app.models import db, Guest, User, EventAttendance

def process_guest_import_file(file, user_id):
    """
    Process an Excel file to import new guests to the database.
    For existing guests, update their profiles with any new information.
    
    Args:
        file: File object from the upload
        user_id: ID of the current user to associate guests with
    
    Returns:
        dict: Import results with details about the import process
    """
    result = {
        'success': False,
        'added': 0,
        'updated': 0,  # Track updated guests
        'skipped': 0,  # No changes needed
        'total_rows': 0,
        'message': '',
        'skipped_names': []
    }
    
    try:
        # Save the uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp:
            file.save(temp.name)
            temp_path = temp.name
        
        try:
            # Read based on file type
            file_ext = os.path.splitext(file.filename)[1].lower()
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
            'first_name': ['first name', 'firstname', 'fname', 'first'],
            'last_name': ['last name', 'lastname', 'lname', 'last'],
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
            'donor_capacity': ['donor capacity', 'giving level', 'capacity', 'rating', 'donor', 'level'],
            'bio': ['bio', 'biography', 'description'],
            'notes': ['notes', 'additional info', 'comments', 'note']
        }
        
        # Find the actual column names in the dataframe - only string types
        def find_column(possible_names):
            """
            Find a column in the DataFrame that matches any of the possible names.
            Only considers string-type column headers, ignoring dates and other types.
            """
            # Filter out non-string column headers to avoid type errors
            string_columns = [col for col in df.columns if isinstance(col, str)]
            
            for name in possible_names:
                # Skip non-string names in possible_names
                if not isinstance(name, str):
                    continue
                
                # Convert name to lowercase for case-insensitive matching
                name_str = name.lower().strip()
                
                # Look for partial matches in string columns only
                for col in string_columns:
                    col_str = col.lower().strip()
                    if name_str in col_str:
                        return col
                        
            # No match found
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
            first_name_col = mapped_columns.get('first_name', '')
            last_name_col = mapped_columns.get('last_name', '')
            
            if not first_name_col or not last_name_col:
                # Can't process data without first and last name columns
                result['message'] = "Required name columns not found in the file"
                return result
                
            first_name = row.get(first_name_col, '')
            last_name = row.get(last_name_col, '')
            
            # Convert to string and strip whitespace
            first_name = str(first_name).strip() if pd.notna(first_name) else ''
            last_name = str(last_name).strip() if pd.notna(last_name) else ''
            
            # Skip if either name is empty
            if not first_name or not last_name or first_name.lower() == 'nan' or last_name.lower() == 'nan':
                result['skipped_names'].append(f"{first_name} {last_name}")
                result['skipped'] += 1
                continue

            # Get email if available
            email = ''
            if 'email' in mapped_columns:
                email_val = row.get(mapped_columns['email'], '')
                email = str(email_val).strip() if pd.notna(email_val) else ''

            # Check for existing guest by name or email using safer comparison
            query_conditions = [
                db.and_(
                    Guest.user_id == user_id,
                    Guest.first_name.ilike(first_name),
                    Guest.last_name.ilike(last_name)
                )
            ]
            
            # Add email condition if email exists
            if email:
                query_conditions.append(
                    db.and_(
                        Guest.user_id == user_id,
                        Guest.email.isnot(None),
                        Guest.email.isnot(''),
                        Guest.email.ilike(email)
                    )
                )
                
            # Execute the query with the conditions
            existing_guest = Guest.query.filter(
                db.or_(*query_conditions)
            ).first()
            
            # Prepare guest data
            guest_data = {}
            
            # Get all field values from the row
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
                        # Special handling for athena_id to convert to integer
                        if field == 'athena_id':
                            try:
                                # Convert float to int, then to string (removes decimal part)
                                if isinstance(value, float):
                                    guest_data[field] = str(int(value))
                                else:
                                    # Try to convert string that might contain a float
                                    guest_data[field] = str(int(float(str(value).strip())))
                            except (ValueError, TypeError):
                                # If conversion fails, keep original value as string
                                guest_data[field] = str(value).strip()
                        # Special handling for donor_capacity
                        elif field == 'donor_capacity':
                            # Handle different types
                            if pd.isna(value):
                                guest_data[field] = 'TBD'
                            else:
                                capacity_str = str(value).strip()
                                
                                # Handle different variations of "To Be Determined"
                                if capacity_str == '' or capacity_str.lower() in ['tbd', 'to be determined', 'to be determined (tb)', 'to be determined (tbd)']:
                                    guest_data[field] = 'TBD'
                                else:
                                    guest_data[field] = capacity_str
                        else:
                            guest_data[field] = str(value).strip()
            
            if existing_guest:
                # Update existing guest with any new information
                updated = False
                updated_fields = []
                
                # Check each field - only update if the field has a value and the existing field is empty
                for field, value in guest_data.items():
                    # Skip known non-string fields that shouldn't be compared this way
                    if field in ['created_at', 'updated_at', 'id', 'user_id']:
                        continue
                        
                    try:
                        existing_value = getattr(existing_guest, field)
                        
                        # Safe comparison - handle all possible types
                        is_empty = (existing_value is None or 
                                   (isinstance(existing_value, str) and existing_value.strip() == '') or
                                   (isinstance(existing_value, (int, float)) and existing_value == 0))
                        
                        # Extra handling for donor_capacity field
                        if field == 'donor_capacity':
                            # Always update donor_capacity if we have a value
                            if value:
                                setattr(existing_guest, field, value)
                                updated = True
                                updated_fields.append(field)
                        elif value and is_empty:
                            setattr(existing_guest, field, value)
                            updated = True
                            updated_fields.append(field)
                    except (AttributeError, TypeError):
                        # Skip fields that can't be compared or don't exist
                        continue
                
                if updated:
                    result['updated'] += 1
                else:
                    result['skipped'] += 1
            else:
                # Create new guest
                guest_data['first_name'] = first_name
                guest_data['last_name'] = last_name
                guest_data['user_id'] = user_id
                
                # Set default value for donor_capacity if not provided
                if 'donor_capacity' not in guest_data or not guest_data['donor_capacity']:
                    guest_data['donor_capacity'] = 'TBD'
                
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
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp:
            file.save(temp.name)
            temp_path = temp.name
        
        try:
            # Read based on file type
            file_ext = os.path.splitext(file.filename)[1].lower()
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
        
        # Filter string-only column headers
        string_columns = [col for col in df.columns if isinstance(col, str)]
        
        # Check for required columns in string columns only
        first_name_col = None
        last_name_col = None
        
        for col in string_columns:
            col_lower = col.lower()
            if 'first' in col_lower and 'name' in col_lower:
                first_name_col = col
            elif 'last' in col_lower and 'name' in col_lower:
                last_name_col = col
        
        if not first_name_col or not last_name_col:
            result['message'] = f"Required columns 'First Name' and 'Last Name' not found. Available string columns: {string_columns}"
            return result
        
        # Process each row in the dataframe
        for _, row in df.iterrows():
            first_name = str(row[first_name_col]).strip() if pd.notna(row[first_name_col]) else ''
            last_name = str(row[last_name_col]).strip() if pd.notna(row[last_name_col]) else ''
            
            # Skip if either name is empty
            if not first_name or not last_name or first_name.lower() == 'nan' or last_name.lower() == 'nan':
                continue
                
            # Find matching guest
            guest = Guest.query.filter(
                Guest.first_name.ilike(first_name),
                Guest.last_name.ilike(last_name)
            ).first()
            
            if not guest:
                result['not_found'] += 1
                result['not_found_names'].append(f"{first_name} {last_name}")
                continue
                
            # Check if already attending
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
        result['message'] = str(e)
        return result