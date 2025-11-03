# Cloud File Exchange System

A secure cloud-based file exchange system with user authentication, file versioning, and comprehensive activity logging.

## Features
- User registration and authentication
- Secure file upload/download
- File versioning control
- Activity logging (LogBook)
- Responsive web interface

## Technologies
- Python Flask
- SQLAlchemy (SQLite database)
- Bootstrap 5
- Flask-Login for authentication

## Setup Instructions

### Prerequisites
- Python 3.8+
- pip

### Installation

1. Clone the repository:
git clone https://github.com/YOUR-USERNAME/cloud-file-exchange.git
cd cloud-file-exchange
2. Create virtual environment:
python3 -m venv venv
source venv/bin/activate
3. Install dependencies:
pip install -r requirements.txt
4. Run the application:
python app.py
5. Open browser to: http://127.0.0.1:5000

## Default Login
- Username: admin
- Password: admin123

## Project Structure
cloud-file-exchange/
├── app.py # Main application
├── models.py # Database models
├── config.py # Configuration
├── requirements.txt # Dependencies
├── templates/ # HTML templates
├── static/ # CSS, JS, images
├── uploads/ # User uploaded files
└── logs/ # Application logs
## Team Members
- Valeriia Balatska
- Vladyslav Dubenchuk
- Szymon Mela
- Marcin Kaczmarek
- Mateusz Mrowicki

## License
Educational project for Cloud Computing Systems course.
