from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and access control."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    guests = db.relationship('Guest', back_populates='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

# Update to app/models.py - Guest class
class Guest(db.Model):
    """Guest model to store contact information and bio details."""
    id = db.Column(db.Integer, primary_key=True)
    # Original fields
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True)
    phone = db.Column(db.String(20))
    organization = db.Column(db.String(128))
    title = db.Column(db.String(128))
    bio = db.Column(db.Text)
    photo_filename = db.Column(db.String(128))
    donor_capacity = db.Column(db.String(64))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='guests')
    
    
    # New fields
    athena_id = db.Column(db.String(64), index=True)
    prospect_manager = db.Column(db.String(128))
    nickname = db.Column(db.String(64))
    prefix = db.Column(db.String(20))
    middle_name = db.Column(db.String(64))
    descriptor = db.Column(db.String(256))
    
    # Relationships
    event_attendances = db.relationship('EventAttendance', back_populates='guest', lazy='dynamic')
    
    @property
    def full_name(self):
        """Return the full formatted name of the guest."""
        components = []
        if self.prefix:
            components.append(self.prefix)
        components.append(self.first_name)
        if self.middle_name:
            components.append(self.middle_name)
        components.append(self.last_name)
        
        full = " ".join(components)
        if self.descriptor:
            full += f" ({self.descriptor})"
        return full
    
    @property
    def display_name(self):
        """Return a display name that includes nickname if available."""
        name = self.first_name
        if self.nickname:
            name += f' "{self.nickname}"'
        name += f" {self.last_name}"
        return name
    
    @property
    def photo_url(self):
        if self.photo_filename:
            return f"/static/photos/{self.photo_filename}"
        return "/static/photos/default.png"
    
    def __repr__(self):
        return f'<Guest {self.full_name}>'

class Event(db.Model):
    """Event model to track organized events."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(256))
    description = db.Column(db.Text)
    eventbrite_id = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attendances = db.relationship('EventAttendance', back_populates='event', lazy='dynamic', cascade="all, delete-orphan")
    
    @property
    def attendee_count(self):
        return self.attendances.count()
    
    def __repr__(self):
        return f'<Event {self.name} on {self.date}>'

class EventAttendance(db.Model):
    """Association model between guests and events."""
    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guest.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    attended = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    
    # Relationships
    guest = db.relationship('Guest', back_populates='event_attendances')
    event = db.relationship('Event', back_populates='attendances')
    
    __table_args__ = (
        db.UniqueConstraint('guest_id', 'event_id', name='_guest_event_uc'),
    )
    
    def __repr__(self):
        return f'<Attendance: {self.guest.full_name} at {self.event.name}>'