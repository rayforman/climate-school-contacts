from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename
import os
import uuid

from app.models import db, Guest
from app.forms.guests import GuestForm, GuestSearchForm
from app.services.photo import save_photo, delete_photo

guests_bp = Blueprint('guests', __name__, url_prefix='/guests')

@guests_bp.route('/', methods=['GET'])
@login_required
def index():
    form = GuestSearchForm(request.args)
    page = request.args.get('page', 1, type=int)
    
    query = Guest.query
    
    # Apply search filters if provided
    if form.search.data:
        search_term = f"%{form.search.data}%"
        query = query.filter(
            (Guest.first_name.ilike(search_term)) |
            (Guest.last_name.ilike(search_term)) |
            (Guest.email.ilike(search_term)) |
            (Guest.organization.ilike(search_term))
        )
    
    # Apply sorting
    sort_by = request.args.get('sort_by', 'last_name')
    sort_direction = request.args.get('sort_direction', 'asc')
    
    if sort_direction == 'desc':
        query = query.order_by(getattr(Guest, sort_by).desc())
    else:
        query = query.order_by(getattr(Guest, sort_by))
    
    # Paginate the results
    pagination = query.paginate(page=page, per_page=20, error_out=False)
    guests = pagination.items
    
    return render_template(
        'guests/index.html',
        title='Guest Directory',
        guests=guests,
        pagination=pagination,
        form=form,
        sort_by=sort_by,
        sort_direction=sort_direction
    )

@guests_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = GuestForm()
    
    if form.validate_on_submit():
        guest = Guest(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            organization=form.organization.data,
            title=form.title.data,
            bio=form.bio.data,
            donor_capacity=form.donor_capacity.data,
            notes=form.notes.data
        )
        
        # Handle photo upload
        if form.photo.data:
            filename = save_photo(form.photo.data)
            if filename:
                guest.photo_filename = filename
        
        db.session.add(guest)
        db.session.commit()
        
        flash(f"Guest {guest.full_name} has been created.", 'success')
        return redirect(url_for('guests.view', id=guest.id))
    
    return render_template('guests/create.html', title='Add New Guest', form=form)

@guests_bp.route('/<int:id>', methods=['GET'])
@login_required
def view(id):
    guest = Guest.query.get_or_404(id)
    return render_template('guests/view.html', title=guest.full_name, guest=guest)

@guests_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    guest = Guest.query.get_or_404(id)
    form = GuestForm(obj=guest)
    
    if form.validate_on_submit():
        # Update basic information
        guest.first_name = form.first_name.data
        guest.last_name = form.last_name.data
        guest.email = form.email.data
        guest.phone = form.phone.data
        guest.organization = form.organization.data
        guest.title = form.title.data
        guest.bio = form.bio.data
        guest.donor_capacity = form.donor_capacity.data
        guest.notes = form.notes.data
        
        # Handle photo upload if new photo provided
        if form.photo.data:
            if guest.photo_filename:
                delete_photo(guest.photo_filename)
            
            filename = save_photo(form.photo.data)
            if filename:
                guest.photo_filename = filename
        
        db.session.commit()
        flash(f"Guest {guest.full_name} has been updated.", 'success')
        return redirect(url_for('guests.view', id=guest.id))
    
    return render_template('guests/edit.html', title=f"Edit {guest.full_name}", form=form, guest=guest)

@guests_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    guest = Guest.query.get_or_404(id)
    name = guest.full_name
    
    # Delete photo if exists
    if guest.photo_filename:
        delete_photo(guest.photo_filename)
    
    db.session.delete(guest)
    db.session.commit()
    
    flash(f"Guest {name} has been deleted.", 'success')
    return redirect(url_for('guests.index'))