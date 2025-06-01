# Skydiving Load Organizer - System Instructions

## Project Overview

This is a full-stack skydiving load organizer application built with modern web technologies to help skydiving operations manage their daily activities efficiently. The system handles aircraft scheduling, load organization, instructor assignments, weather monitoring, and jump management.

## MVP Scope

### Core Features
1. **Load Management** - Create, schedule, and track aircraft loads
2. **Aircraft Management** - Manage fleet of aircraft with capacity tracking
3. **Instructor Management** - Handle instructor certifications and assignments
4. **Jump Management** - Track individual jumpers and jump types
5. **Weather Monitoring** - Monitor and assess weather conditions for safety
6. **Dashboard & Analytics** - Real-time operational overview and statistics

### User Types
- **Admin Users** - Full access to all features
- **Load Organizers** - Can create and manage loads, assign instructors
- **Instructors** - Can view their assignments and update jump records
- **Basic Users** - Can view schedules and basic information

## System Architecture

### Technology Stack

#### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with SQLModel ORM
- **Authentication**: JWT tokens
- **API Documentation**: Auto-generated with OpenAPI/Swagger
- **Validation**: Pydantic models with automatic validation
- **Containerization**: Docker with hot-reload for development

#### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite for fast development and builds
- **UI Components**: Chakra UI v3 with custom component library
- **Routing**: TanStack Router for type-safe routing
- **State Management**: TanStack Query for server state management
- **Forms**: React Hook Form with Zod validation
- **API Client**: Auto-generated TypeScript client from OpenAPI spec

#### Infrastructure
- **Proxy**: Traefik for reverse proxy and load balancing
- **Development**: Docker Compose with watch mode
- **Database Admin**: Adminer for database management
- **Email**: MailHog for development email testing
- **Testing**: Pytest (backend), Playwright (frontend)

### Data Models & Domain Entities

#### Core Entities

1. **Aircraft**
   - Registration number (unique identifier)
   - Model/type
   - Passenger capacity (2-50 seats)
   - Active status
   - Relationships: One-to-many with Loads

2. **Instructor**
   - Personal information (name, email)
   - Certifications (tandem_certified, aff_certified)
   - Active status
   - Relationships: One-to-many with Jumps

3. **Load**
   - Aircraft assignment
   - Scheduled departure time
   - Altitude (3,000-18,000 feet)
   - Status (planning → confirmed → boarded → departed → completed/cancelled)
   - Notes
   - Relationships: Many-to-one with Aircraft, One-to-many with Jumps

4. **Jump**
   - Load assignment
   - Jumper details (name, email)
   - Jump type (tandem, AFF, fun_jumper)
   - Exit order (for aircraft safety)
   - Instructor assignment (required for tandem/AFF)
   - AFF level (for student progression)
   - Notes
   - Relationships: Many-to-one with Load and Instructor

5. **Weather Report**
   - Date and time
   - Wind conditions (speed, direction)
   - Visibility
   - Cloud ceiling
   - Overall condition (good/marginal/poor)
   - Suitability flags for different jump types

#### Business Rules

1. **Capacity Management**
   - Loads cannot exceed aircraft capacity
   - Real-time tracking of available seats

2. **Instructor Certification**
   - Tandem jumps require tandem-certified instructors
   - AFF jumps require AFF-certified instructors
   - Fun jumpers don't require instructor assignment

3. **Safety Requirements**
   - Weather conditions must be suitable for jump types
   - Exit order must be managed for safety
   - Load status progression enforces operational workflow

4. **Operational Workflow**
   - Loads progress through defined statuses
   - Jumps can only be assigned to confirmed loads
   - Weather reports influence operational decisions

### API Structure

#### RESTful Endpoints
- `/api/v1/aircraft/` - Aircraft CRUD operations
- `/api/v1/instructors/` - Instructor management with certification filtering
- `/api/v1/loads/` - Load management with status and date filtering
- `/api/v1/jumps/` - Jump management with type and load filtering
- `/api/v1/weather/` - Weather reporting and suitability checking
- `/api/v1/analytics/` - Operational statistics and reporting

#### Authentication
- JWT-based authentication
- Role-based access control
- Secure password hashing
- Token refresh mechanism

### Frontend Architecture

#### Component Structure
```
src/
├── components/
│   ├── Common/          # Shared UI components
│   ├── Forms/           # Form components (LoadForm, etc.)
│   ├── ui/              # Chakra UI custom components
│   └── UserSettings/    # User preference components
├── routes/
│   └── _layout/         # Application routes with layouts
├── client/              # Auto-generated API client
├── lib/                 # Utility functions and configurations
└── hooks/               # Custom React hooks
```

#### State Management Strategy
- **Server State**: TanStack Query for caching and synchronization
- **Form State**: React Hook Form for complex forms with validation
- **UI State**: React built-in state and context for local UI state
- **Authentication**: Context provider for user authentication state

#### Type Safety
- **End-to-End TypeScript**: From database models to frontend components
- **Auto-Generated Types**: API client and types generated from OpenAPI spec
- **Runtime Validation**: Zod schemas for form validation and data integrity

### Development Workflow

#### Code Generation
- API client and TypeScript types auto-generated from backend OpenAPI spec
- Ensures type safety across the full stack
- Regenerated automatically when backend models change

#### Development Environment
- Hot-reload for both frontend and backend
- Database persistence across container restarts
- Integrated email testing with MailHog
- Live API documentation at `/docs`

#### Testing Strategy
- **Backend**: Unit tests with Pytest, database testing with SQLModel
- **Frontend**: Component testing with React Testing Library
- **E2E**: Playwright for full application testing
- **API**: Automatic testing via OpenAPI spec validation

### Security Considerations

#### Authentication & Authorization
- JWT tokens with secure secret key generation
- Password hashing with bcrypt
- Role-based access control for different user types
- Secure session management

#### Data Protection
- Input validation at multiple layers (frontend, backend, database)
- SQL injection protection via SQLModel ORM
- XSS protection via React's built-in escaping
- CORS configuration for secure cross-origin requests

#### Operational Security
- Environment variable management for secrets
- Database connection security
- HTTPS enforcement in production
- Secure container configurations

### Scalability & Performance

#### Database Optimization
- Indexed foreign keys and commonly queried fields
- Efficient relationship queries with SQLModel
- Connection pooling for concurrent access
- Database migration management

#### Frontend Performance
- Code splitting with Vite
- Lazy loading of routes and components
- Efficient re-rendering with React Query caching
- Optimized bundle sizes

#### Caching Strategy
- TanStack Query for intelligent server state caching
- Automatic cache invalidation on data mutations
- Background refetching for real-time data updates

### Operational Features

#### Dashboard Analytics
- Real-time load statistics
- Aircraft utilization tracking
- Instructor workload monitoring
- Revenue estimation
- Weather impact analysis

#### Business Intelligence
- Daily capacity utilization
- Jump type distribution analysis
- Instructor schedule optimization
- Weather pattern impact on operations

### Deployment & Infrastructure

#### Production Deployment
- Docker containerization for consistency
- Multi-stage builds for optimized images
- Environment-specific configurations
- Database migration automation

#### Monitoring & Logging
- Application health monitoring
- Performance metrics collection
- Error tracking and reporting
- Audit logging for operational changes

### Future Enhancements

#### Phase 2 Features
- Customer booking portal
- Payment processing integration
- Automated scheduling optimization
- Mobile application for instructors
- Advanced weather integration with external APIs
- Maintenance tracking for aircraft
- Certification renewal reminders

#### Technical Improvements
- Real-time notifications with WebSockets
- Advanced caching with Redis
- Microservices architecture for scaling
- Machine learning for capacity optimization
- API rate limiting and throttling
- Advanced monitoring with APM tools

## Development Guidelines

### Code Quality Standards
- TypeScript strict mode enabled
- ESLint and Prettier for code formatting
- Pre-commit hooks for code quality
- Comprehensive error handling
- Consistent naming conventions

### Testing Requirements
- Unit test coverage for business logic
- Integration tests for API endpoints
- E2E tests for critical user workflows
- Performance testing for high-load scenarios

### Documentation Standards
- API documentation auto-generated and maintained
- Code comments for complex business logic
- README files for setup and development
- Architecture decision records (ADRs) for major changes

This system provides a robust foundation for skydiving operations management while maintaining flexibility for future enhancements and scaling requirements.
