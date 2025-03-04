import io
import pandas as pd
import tempfile
import os
import datetime

from flask import current_app
from sqlalchemy import func
from app.models import db, Guest, User, EventAttendance

# Add this debugging function
def debug_column_mapping(df, field_mappings):
    """Debug helper to print column mapping information."""
    print("\n=== DEBUG: COLUMN MAPPING ===")
    print(f"Excel columns: {list(df.columns)}")
    print(f"Mapped fields: {field_mappings}")
    # Check for donor capacity specifically
    donor_cols = [col for col in df.columns if 'donor' in col.lower() or 'capacity' in col.lower()]
    print(f"Potential donor capacity columns: {donor_cols}")
    if donor_cols:
        for col in donor_cols:
            # Print first few values
            print(f"Sample values in '{col}': {df[col].head(3).tolist()}")
    print("=== END DEBUG ===\n")
    return

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
        
        # Find the actual column names in the dataframe
        def find_column(possible_names):
            for name in possible_names:
                # Make matching more flexible - look for partial matches
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
                
        # Add enhanced debugging for donor capacity field
        print("\n=== DEBUG: DONOR CAPACITY MAPPING ===")
        capacity_mapping = column_mapping['donor_capacity']
        print(f"Looking for donor capacity in columns: {capacity_mapping}")
        for name in capacity_mapping:
            matches = [col for col in df.columns if name.lower() in col.lower()]
            if matches:
                print(f"Found potential matches for '{name}': {matches}")
        
        # Additional debugging for the actual Rating column
        if 'Rating' in df.columns:
            print("\n=== DEBUG: RATING COLUMN VALUES ===")
            # Get unique values
            unique_ratings = df['Rating'].dropna().unique()
            print(f"Unique Rating values: {unique_ratings}")
            # Count non-empty values
            non_empty_count = df['Rating'].notna().sum()
            print(f"Records with Rating values: {non_empty_count} out of {len(df)}")
            print("=== END RATING DEBUG ===\n")
        
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
                result['skipped'] += 1
                continue

            # Get email if available
            email = row.get(mapped_columns.get('email', ''), '')
            email = str(email).strip() if pd.notna(email) else ''

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
                            # Print debug info for this specific field
                            print(f"DEBUG: Processing donor_capacity value: '{value}' (type: {type(value)})")
                            
                            # Handle different types
                            if pd.isna(value):
                                print("DEBUG: Value is NaN, setting to TBD")
                                guest_data[field] = 'TBD'
                            else:
                                capacity_str = str(value).strip()
                                print(f"DEBUG: Converted to string: '{capacity_str}'")
                                
                                # Handle different variations of "To Be Determined"
                                if capacity_str == '' or capacity_str.lower() in ['tbd', 'to be determined', 'to be determined (tb)', 'to be determined (tbd)']:
                                    guest_data[field] = 'TBD'
                                    print("DEBUG: Normalized to 'TBD'")
                                else:
                                    guest_data[field] = capacity_str
                                    print(f"DEBUG: Final value set to: '{capacity_str}'")
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
                        
                        # Debug the comparison for donor_capacity specifically
                        if field == 'donor_capacity':
                            print(f"DEBUG UPDATE: donor_capacity comparison")
                            print(f"  - New value: '{value}'")
                            print(f"  - Existing value: '{existing_value}'")
                        
                        # Safe comparison - handle all possible types
                        is_empty = (existing_value is None or 
                                   (isinstance(existing_value, str) and existing_value.strip() == '') or
                                   (isinstance(existing_value, (int, float)) and existing_value == 0))
                        
                        # Extra forcing for donor_capacity field
                        if field == 'donor_capacity':
                            # Always update donor_capacity if we have a value
                            if value:
                                setattr(existing_guest, field, value)
                                updated = True
                                updated_fields.append(field)
                                print(f"DEBUG UPDATE: Forced update of donor_capacity to '{value}'")
                        elif value and is_empty:
                            setattr(existing_guest, field, value)
                            updated = True
                            updated_fields.append(field)
                    except (AttributeError, TypeError):
                        # Skip fields that can't be compared or don't exist
                        continue
                
                if updated:
                    result['updated'] += 1
                    print(f"DEBUG: Updated guest {existing_guest.full_name} with fields: {updated_fields}")
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
                
                # Debug output for new guest
                print(f"DEBUG NEW GUEST: Creating new guest {first_name} {last_name}")
                print(f"  - donor_capacity: '{guest_data.get('donor_capacity', 'NOT SET')}'")
                
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