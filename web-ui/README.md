# GKL League Analytics Web Interface

A full-stack web application for exploring and analyzing fantasy baseball transaction data from the GKL league.

## Architecture

### Backend (Node.js/Express)
- **API Server**: Express server with SQLite database connection
- **Transaction Service**: Advanced filtering, pagination, and search functionality
- **RESTful Endpoints**: Comprehensive API for transaction data access
- **Analytics Placeholders**: Ready for future analytics features

### Frontend (React)
- **Modern React**: Hooks-based architecture with functional components
- **Tailwind CSS**: Utility-first CSS framework for responsive design
- **React Router**: Client-side routing for seamless navigation
- **Custom Hooks**: Reusable logic for data fetching and state management

## Features

### Current Implementation
- **Transaction Explorer**: Browse and search all fantasy transactions
- **Advanced Filtering**: Filter by player, team, position, transaction type, date range
- **Pagination**: Efficient handling of large datasets
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Search Functionality**: Real-time player search with debouncing

### Planned Features
- **Analytics Dashboard**: Transaction trends and insights
- **Manager Analysis**: Individual manager performance metrics
- **Data Visualization**: Charts and graphs for transaction patterns
- **Export Functionality**: CSV/Excel export capabilities

## Getting Started

### Prerequisites
- Node.js 14+ and npm
- SQLite database with transaction data

### Installation

1. **Backend Setup**:
   ```bash
   cd web-ui/backend
   npm install
   npm start
   ```
   Backend will run on http://localhost:3001

2. **Frontend Setup**:
   ```bash
   cd web-ui/frontend
   npm install
   npm start
   ```
   Frontend will run on http://localhost:3000

### Environment Configuration

Create `.env` files for environment-specific settings:

**Backend (.env)**:
```
NODE_ENV=development
PORT=3001
CORS_ORIGIN=http://localhost:3000
DB_PATH=../../database.db
```

**Frontend (.env)**:
```
REACT_APP_API_URL=http://localhost:3001
```

## Project Structure

```
web-ui/
├── backend/
│   ├── app.js                 # Express server setup
│   ├── routes/
│   │   ├── transactions.js    # Transaction API endpoints
│   │   └── analytics.js       # Analytics API endpoints
│   └── services/
│       ├── database.js        # Database connection
│       └── transactionService.js # Business logic
├── frontend/
│   ├── src/
│   │   ├── components/        # Reusable UI components
│   │   ├── pages/             # Page components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── services/          # API service layer
│   │   └── App.js             # Main application
│   ├── public/
│   └── package.json
└── README.md
```

## API Endpoints

### Transactions
- `GET /api/transactions` - Get transactions with filtering and pagination
- `GET /api/transactions/stats` - Get transaction statistics
- `GET /api/transactions/filters` - Get available filter options
- `GET /api/transactions/players/search` - Search players

### Analytics (Planned)
- `GET /api/analytics/summary` - Dashboard summary
- `GET /api/analytics/managers` - Manager analytics

## Development

### Code Style
- **Backend**: CommonJS modules, async/await patterns
- **Frontend**: ES6 modules, React hooks, functional components
- **Styling**: Tailwind utility classes with custom component styles

### Database Schema
The application expects SQLite tables:
- `transactions_production`: Main transaction data
- `transactions_test`: Test transaction data

Required fields: `date`, `league_key`, `transaction_id`, `transaction_type`, `player_id`, `player_name`, `player_position`, `player_team`, `movement_type`, `source_team_name`, `destination_team_name`, etc.

## Future Enhancements

1. **Real-time Updates**: WebSocket integration for live transaction feeds
2. **Advanced Analytics**: Machine learning insights and predictions
3. **Data Export**: Multiple format support (CSV, Excel, JSON)
4. **User Authentication**: Role-based access control
5. **Mobile App**: React Native companion application
6. **Caching**: Redis integration for improved performance