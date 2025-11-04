# FastAPI URL Shortener

A modern, fast URL shortener built with FastAPI, HTMX, and Tailwind CSS.

## Features

- **User Authentication**: Secure registration and login with httpOnly cookies
- **Dashboard**: Manage all your shortened links at `/d/`
- **Link Analytics**: Track clicks with IP addresses, referrer, and user agent data
- **Custom Short Codes**: Create memorable custom links or use auto-generated ones
- **Fast Redirects**: Root-level redirects (e.g., `example.com/my-link`)
- **Modern UI**: Clean, responsive interface with HTMX for dynamic updates

## Tech Stack

- **Backend**: Python 3.13, FastAPI
- **Database**: SQLite with cursor-based queries (no ORM)
- **Frontend**: HTMX, Tailwind CSS (via CDN)
- **Auth**: pwdlib (Argon2) for password hashing
- **Testing**: pytest with 38 comprehensive tests

## Project Structure

```
fastapi-link-shortener/
├── app/
│   ├── db/
│   │   ├── schema.py          # Database schema and initialization
│   │   └── database.py        # Cursor-based database utilities
│   ├── routers/
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── dashboard.py      # Dashboard API
│   │   └── redirect.py       # Link redirection
│   ├── utils/
│   │   ├── auth.py           # Authentication utilities
│   │   └── short_code.py     # Short code generation
│   └── main.py               # FastAPI application
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── dashboard.html
│   └── partials/
│       ├── link_row.html
│       └── link_stats.html
├── tests/
│   ├── conftest.py           # Test fixtures
│   ├── test_api.py           # API endpoint tests
│   ├── test_auth.py          # Authentication tests
│   ├── test_database.py      # Database tests
│   └── test_short_code.py    # Short code tests
├── static/
│   ├── css/
│   └── js/
├── requirements.txt
└── README.md
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd fastapi-link-shortener
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database**:
   ```bash
   python -m app.db.schema
   ```

## Running the Application

**Development server**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Production server**:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The application will be available at `http://localhost:8000`

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_api.py -v
```

All 38 tests should pass.

## Usage

### 1. Register/Login
- Visit the homepage at `/`
- Register a new account or login with existing credentials

### 2. Create Short Links
- Access your dashboard at `/d/`
- Enter the original URL
- Optionally provide a custom short code (3-50 characters, alphanumeric, hyphens, underscores)
- Click "Create Link"

### 3. Use Short Links
- Share your short link: `yourdomain.com/short-code`
- Anyone clicking the link will be redirected to the original URL
- Clicks are tracked with IP address, timestamp, referrer, and user agent

### 4. View Analytics
- In the dashboard, click "Stats" next to any link
- View total clicks, creation date, and detailed click history

### 5. Manage Links
- Copy link URLs with the copy button
- Delete links you no longer need

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `POST /auth/logout` - Logout user

### Dashboard
- `GET /d/` - Dashboard page
- `POST /d/links` - Create new short link
- `DELETE /d/links/{link_id}` - Delete link
- `GET /d/links/{link_id}/stats` - View link statistics

### Redirection
- `GET /{short_code}` - Redirect to original URL (tracks click)

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Links Table
```sql
CREATE TABLE links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    short_code TEXT UNIQUE NOT NULL,
    original_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    clicks INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
```

### Clicks Table
```sql
CREATE TABLE clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id INTEGER NOT NULL,
    ip_address TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    referrer TEXT,
    user_agent TEXT,
    FOREIGN KEY (link_id) REFERENCES links(id) ON DELETE CASCADE
)
```

## Security Features

- **Password Hashing**: Argon2 via pwdlib (recommended algorithm)
- **Secure Cookies**: httpOnly, secure, SameSite=Lax
- **Token-based Auth**: 30-day expiring tokens
- **SQL Injection Protection**: Parameterized queries throughout
- **Input Validation**: Email, password, URL, and short code validation

## Development Guidelines

### Using Cursor-based Queries

Always use the cursor-based utilities from `app/db/database.py`:

```python
from app.db.database import execute_query, get_cursor

# Simple query
user = execute_query(
    "SELECT * FROM users WHERE email = ?",
    (email,),
    fetch_one=True
)

# Complex transaction
with get_cursor() as cursor:
    cursor.execute("INSERT INTO links (...) VALUES (?)", (data,))
    link_id = cursor.lastrowid
    cursor.execute("INSERT INTO clicks (...) VALUES (?)", (link_id,))
```

### Writing Tests

- Place tests in `tests/` directory
- Use fixtures from `conftest.py`
- Test critical functionality: auth, database ops, API endpoints
- Run tests before committing

## Future Enhancements

- [ ] QR code generation for links
- [ ] Link expiration dates
- [ ] Bulk link import/export
- [ ] Advanced analytics dashboard
- [ ] Custom domains support
- [ ] Rate limiting
- [ ] API key authentication for programmatic access

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Submit a pull request
