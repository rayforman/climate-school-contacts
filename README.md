## Project Architecture
event-guest-manager/
├── app/
│   ├── __init__.py         # Flask application factory
│   ├── config.py           # Configuration settings
│   ├── models.py           # Database models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py         # Authentication routes
│   │   ├── guests.py       # Guest management
│   │   ├── events.py       # Event management
│   │   └── reports.py      # Report generation
│   ├── services/
│   │   ├── __init__.py
│   │   ├── eventbrite.py   # Eventbrite processing
│   │   ├── photo.py        # Photo handling
│   │   └── reports.py      # Report generation
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── photos/         # Guest photos storage
│   └── templates/
│       ├── auth/
│       ├── guests/
│       ├── events/
│       ├── reports/
│       ├── base.html
│       └── index.html
├── migrations/             # Database migrations
├── tests/
├── .env                    # Environment variables
├── .gitignore
├── README.md
├── requirements.txt
└── run.py                  # Application entry point