from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime
import os

from app.models import db, Event, Guest, EventAttendance
from app.forms.events import EventForm, EventSearchForm, AttendeeForm
from app.services.import_service import process_attendee_file

events_bp = Blueprint('events', __name__, url_prefix='/events')

@events_bp.route('/', methods=['GET'])
@login_required
def index():
    form = EventSearchForm(request.args)
    page = request.args.get('page', 1, type=int)
    
    query = Event.query
    
    # Apply search filters if provided
    if form.search.data:
        search_term = f"%{form.search.data}%"
        query = query.filter(Event.name.ilike(search_term))
    
    # Date filter
    if form.date_from.data:
        query = query.filter(Event.date >= form.date_from.data)
    if form.date_to.data:
        query = query.filter(Event.date <= form.date_to.data)
    
    # Apply sorting
    sort_by = request.args.get('sort_by', 'date')
    sort_direction = request.args.get('sort_direction', 'desc')
    
    if sort_direction == 'desc':
        query = query.order_by(getattr(Event, sort_by).desc())
    else:
        query = query.order_by(getattr(Event, sort_by))
    
    # Paginate the results
    pagination = query.paginate(page=page, per_page=10, error_out=False)
    events = pagination.items
    
    return render_template(
        'events/index.html',
        title='Events',
        events=events,
        pagination=pagination,
        form=form,
        sort_by=sort_by,
        sort_direction=sort_direction
    )

@events_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = EventForm()
    
    if form.validate_on_submit():
        event = Event(
            name=form.name.data,
            date=form.date.data,
            location=form.location.data,
            description=form.description.data,
            eventbrite_id=form.eventbrite_id.data
        )
        
        db.session.add(event)
        db.session.commit()  # Commit first to get an event ID
        
        # Handle attendee file upload if provided
        attendee_file = request.files.get('attendee_excel')  # This might be named differently in your form
        if attendee_file and attendee_file.filename:
            # Process the file with our new function
            result = process_attendee_file(attendee_file, event.id)
            
            if result['success']:
                message = f"Event created and {result['added']} attendees added."
                if result['existing'] > 0:
                    message += f" {result['existing']} attendees were already on the list."
                
                flash(message, 'success')
                
                # Display information about names not found
                if result['not_found'] > 0:
                    not_found_message = f"{result['not_found']} names were not found in your database."
                    flash(not_found_message, 'warning')
            else:
                flash(f"Event created but error importing attendees: {result.get('message', 'Unknown error')}", 'warning')
        else:
            flash(f"Event '{event.name}' has been created.", 'success')
        
        return redirect(url_for('events.view', id=event.id))
    
    return render_template('events/create.html', title='Create New Event', form=form)

@events_bp.route('/<int:id>', methods=['GET'])
@login_required
def view(id):
    event = Event.query.get_or_404(id)
    attendees = event.attendances.join(Guest).order_by(Guest.last_name).all()
    
    return render_template(
        'events/view.html',
        title=event.name,
        event=event,
        attendees=attendees
    )

@events_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    event = Event.query.get_or_404(id)
    form = EventForm(obj=event)
    
    if form.validate_on_submit():
        event.name = form.name.data
        event.date = form.date.data
        event.location = form.location.data
        event.description = form.description.data
        event.eventbrite_id = form.eventbrite_id.data
        
        db.session.commit()
        flash(f"Event '{event.name}' has been updated.", 'success')
        return redirect(url_for('events.view', id=event.id))
    
    return render_template('events/edit.html', title=f"Edit {event.name}", form=form, event=event)

@events_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    event = Event.query.get_or_404(id)
    name = event.name
    
    db.session.delete(event)
    db.session.commit()
    
    flash(f"Event '{name}' has been deleted.", 'success')
    return redirect(url_for('events.index'))

@events_bp.route('/<int:id>/attendees/add', methods=['GET', 'POST'])
@login_required
def add_attendee(id):
    event = Event.query.get_or_404(id)
    form = AttendeeForm()
    
    # Get current user's guests to populate the form choices
    # This is likely the issue - the route isn't filtering guests by user_id
    guests = Guest.query.filter_by(user_id=current_user.id).order_by(Guest.last_name, Guest.first_name).all()
    
    # Make sure we have guests before trying to build choices
    if not guests:
        flash("You need to add guests to your database before you can add them to events.", "warning")
        return redirect(url_for('guests.create'))
    
    # Populate guest choices with proper formatting
    form.guest_id.choices = [(g.id, f"{g.full_name} ({g.organization or 'No organization'})") for g in guests]
    
    if form.validate_on_submit():
        guest = Guest.query.get(form.guest_id.data)
        
        # Verify the guest belongs to the current user
        if guest.user_id != current_user.id:
            flash("You can only add your own guests to events.", "danger")
            return redirect(url_for('events.view', id=event.id))
        
        # Check if already attending
        existing = EventAttendance.query.filter_by(
            event_id=event.id, 
            guest_id=guest.id
        ).first()
        
        if existing:
            flash(f"{guest.full_name} is already on the attendee list.", 'warning')
        else:
            attendance = EventAttendance(
                event_id=event.id,
                guest_id=guest.id,
                notes=form.notes.data
            )
            db.session.add(attendance)
            db.session.commit()
            flash(f"{guest.full_name} has been added to the attendee list.", 'success')
        
        return redirect(url_for('events.view', id=event.id))
    
    return render_template(
        'events/add_attendee.html',
        title=f"Add Attendee to {event.name}",
        form=form,
        event=event
    )

@events_bp.route('/<int:event_id>/attendees/<int:attendee_id>/remove', methods=['POST'])
@login_required
def remove_attendee(event_id, attendee_id):
    attendance = EventAttendance.query.get_or_404(attendee_id)
    guest_name = attendance.guest.full_name
    
    db.session.delete(attendance)
    db.session.commit()
    
    flash(f"{guest_name} has been removed from the attendee list.", 'success')
    return redirect(url_for('events.view', id=event_id))

@events_bp.route('/<int:id>/import', methods=['GET', 'POST'])
@login_required
def import_attendees(id):
    event = Event.query.get_or_404(id)
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and (file.filename.endswith('.csv') or file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            # Process the attendee file
            result = process_attendee_file(file, event.id)
            
            if result['success']:
                message = f"Successfully added {result['added']} attendees to the event."
                if result['existing'] > 0:
                    message += f" {result['existing']} attendees were already on the list."
                
                flash(message, 'success')
                
                # Display information about names not found
                if result['not_found'] > 0:
                    not_found_message = f"{result['not_found']} names were not found in your database: "
                    # Show up to 5 names, then summarize the rest
                    if len(result['not_found_names']) <= 5:
                        not_found_message += ", ".join(result['not_found_names'])
                    else:
                        not_found_message += ", ".join(result['not_found_names'][:5]) + f" and {len(result['not_found_names']) - 5} more"
                    flash(not_found_message, 'warning')
                
                return redirect(url_for('events.view', id=event.id))
            else:
                flash(f"Error importing attendees: {result.get('message', 'Unknown error')}", 'danger')
        else:
            flash('Invalid file format. Please upload a CSV or Excel file.', 'danger')
    
    return render_template('events/import.html', title=f"Import Attendees - {event.name}", event=event)