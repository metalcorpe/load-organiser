# Organiser - Full Stack FastAPI Application

A modern full-stack web application built using the FastAPI full-stack template.

## Technology Stack

- **Backend**: FastAPI with Python
- **Frontend**: React with TypeScript and Vite
- **Database**: PostgreSQL
- **ORM**: SQLModel
- **UI Components**: Chakra UI
- **Authentication**: JWT tokens
- **Containerization**: Docker and Docker Compose
- **Proxy**: Traefik
- **Testing**: Pytest (backend) and Playwright (frontend)

## Project Structure

```
organiser/
├── backend/           # FastAPI backend application
├── frontend/          # React frontend application
├── docker-compose.yml # Docker Compose configuration
├── .env              # Environment variables
└── scripts/          # Utility scripts
```

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git installed

### Setup

1. **Clone and navigate to the project**:
   ```bash
   git clone <your-repo-url> organiser
   cd organiser
   ```

2. **Configure environment variables**:
   - The project comes with secure secrets pre-configured
   - Review `.env` file for any additional customizations needed

3. **Start the application**:
   ```bash
   docker compose up --watch
   ```

### Access the Application

Once the services are running, you can access:

- **Frontend**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Database Admin**: [http://localhost:8080](http://localhost:8080)
- **Traefik Dashboard**: [http://localhost:8090](http://localhost:8090)
- **Email Catcher**: [http://localhost:1080](http://localhost:1080)

### Default Login

- **Email**: admin@example.com
- **Password**: Check the `FIRST_SUPERUSER_PASSWORD` in your `.env` file

## Development

### Working with Docker Compose

The project uses Docker Compose with watch mode for development:

```bash
# Start all services in watch mode
docker compose up --watch

# View logs for all services
docker compose logs

# View logs for a specific service
docker compose logs backend

# Stop all services
docker compose down

# Rebuild services
docker compose build
```

### Local Development

You can also run services locally while keeping others in Docker:

#### Backend Development

```bash
# Stop the backend container
docker compose stop backend

# Navigate to backend directory
cd backend

# Install dependencies (first time)
pip install -r requirements.txt

# Run the backend locally
fastapi dev app/main.py
```

#### Frontend Development

```bash
# Stop the frontend container
docker compose stop frontend

# Navigate to frontend directory
cd frontend

# Install dependencies (first time)
npm install

# Run the frontend locally
npm run dev
```

## Environment Variables

Key environment variables (configured in `.env`):

- `PROJECT_NAME`: Name of the project
- `SECRET_KEY`: Secret key for JWT tokens (auto-generated)
- `FIRST_SUPERUSER_PASSWORD`: Password for the initial admin user (auto-generated)
- `POSTGRES_PASSWORD`: Database password (auto-generated)
- `ENVIRONMENT`: Current environment (local/staging/production)

## Database

The application uses PostgreSQL running in Docker. The database is automatically initialized with:

- User management tables
- Authentication schema
- Sample data

You can access the database using:
- **Adminer**: [http://localhost:8080](http://localhost:8080)
- **Direct connection**: `localhost:5432` with credentials from `.env`

## Testing

### Backend Tests

```bash
# Run backend tests
docker compose exec backend pytest

# Run tests with coverage
docker compose exec backend pytest --cov
```

### Frontend Tests

```bash
# Run frontend tests
docker compose exec frontend npm test

# Run E2E tests with Playwright
docker compose run --rm playwright
```

## Deployment

See `deployment.md` for production deployment instructions.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes
4. Run tests to ensure everything works
5. Commit your changes: `git commit -am 'Add new feature'`
6. Push to the branch: `git push origin feature/new-feature`
7. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions and support:
- Check the FastAPI documentation: https://fastapi.tiangolo.com/
- Review the original template: https://github.com/fastapi/full-stack-fastapi-template
- Create an issue in the project repository
