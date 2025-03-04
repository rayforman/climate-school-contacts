# Event Guest Management System

A database system for the Columbia Climate School to track event attendees, manage contact information, and generate bio sheets. This system replaces the previous Excel-based approach with a more efficient web-based solution.

## Features

- **Guest Management**
  - Store comprehensive guest profiles with photos and bios
  - Enhanced contact details including prefix, middle name, nickname, and descriptor
  - Columbia-specific fields (Athena ID, Prospect Manager, Donor Capacity)
  - Search, filter, and sort functionality

- **Event Management**
  - Create and manage event details
  - Track event attendance
  - Import attendees from Eventbrite CSV exports

- **Bio Sheet Generation**
  - Automatically generate formatted Word documents with guest bios
  - Include photos and formatted contact information
  - Generate documents for specific events

- **User Management**
  - Secure authentication system
  - User-specific guest lists

## Project Architecture

```
event-guest-manager/
├── app/
│   ├── __init__.py         # Flask application factory
│   ├── config.py           # Configuration settings
│   ├── models.py           # Database models with enhanced Guest model
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py         # Authentication routes
│   │   ├── guests.py       # Guest management with extended attributes
│   │   ├── events.py       # Event management
│   │   └── reports.py      # Report generation
│   ├── forms/
│   │   ├── __init__.py
│   │   ├── auth.py         # Login and registration forms
│   │   ├── guests.py       # Guest forms with enhanced fields
│   │   └── events.py       # Event forms
│   ├── services/
│   │   ├── __init__.py
│   │   ├── eventbrite.py   # Eventbrite CSV processing
│   │   ├── photo.py        # Photo handling
│   │   └── reports.py      # Bio sheet generation
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── photos/         # Guest photos storage
│   └── templates/
│       ├── auth/           # Login, registration templates
│       ├── guests/         # Guest management templates
│       ├── events/         # Event management templates
│       ├── reports/        # Report generation templates
│       ├── errors/         # Error page templates
│       ├── base.html
│       └── index.html
├── instance/               # Instance-specific files
│   └── app.db              # SQLite database file
├── migrations/             # Database migrations
├── venv/                   # Python virtual environment
├── .env                    # Environment variables
├── .gitignore
├── README.md
├── requirements.txt
└── run.py                  # Application entry point
```

## Guest Model Details

The enhanced guest model now includes the following fields:

- Basic Information
  - First Name, Last Name
  - Prefix (Dr., Mr., Ms., etc.)
  - Middle Name
  - Nickname(s)
  - Descriptor (suffixes, qualifiers, etc.)

- Contact Information
  - Email, Phone

- Professional Information
  - Organization, Title

- Columbia-Specific Information
  - Athena ID (Columbia University internal ID)
  - Prospect Manager (development officer)
  - Donor Capacity
  
- Other Details
  - Bio
  - Photo
  - Notes

## Setup

1. Clone the repository:
```
git clone https://github.com/your-username/climate-school-contacts.git
cd climate-school-contacts
```

2. Create and activate a virtual environment:
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Set up the database:
```
flask db upgrade
```

5. Run the application:
```
flask run
```

## Usage

1. Register a new user account at `/auth/register`
2. Add guests to the system with their details and photos
3. Create events and add attendees
4. Import attendees from Eventbrite CSV exports
5. Generate bio sheets for events

## Development

- Database migrations: `flask db migrate -m "message"` followed by `flask db upgrade`
- Flask shell: `flask shell`