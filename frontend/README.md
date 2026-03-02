# 🏢 Employee Portal - Frontend

Modern, responsive React application for Employee Leave Management with role-based dashboards.

![React](https://img.shields.io/badge/React-19-blue.svg)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Components](#-components)
- [State Management](#-state-management)
- [API Integration](#-api-integration)
- [Styling](#-styling)
- [Testing](#-testing)
- [Build & Deploy](#-build--deploy)

## ✨ Features

### 🔐 Authentication
- Secure cookie-based authentication
- Auto-refresh of access tokens
- Session timeout handling
- Protected routes with role-based access

### 👨‍💼 Admin Dashboard
- **Leave Requests Management**: View, approve, or reject employee leave requests
- **Employee Management**: Create, update, and manage employee accounts
- **Direct Leave Issuance**: Issue leave directly to employees
- **Balance Adjustments**: Manually adjust employee leave balances
- **FY Transitions**: Process fiscal year transitions (Lapse & Carry Forward)
- **Accrual Processing**: Run monthly/annual accrual calculations
- **Audit Trail**: View complete audit log of all administrative actions
- **Analytics Dashboard**: Visual insights with charts and statistics

### 👨‍💻 Employee Dashboard
- **Leave Application**: Apply for various leave types with date picker
- **Leave Balance**: View current leave balances by type
- **Request Tracking**: Track status of submitted leave requests
- **Accrual Summary**: View accrual history and projections
- **Personal History**: View personal leave history and activities
- **Leave Cancellation**: Cancel pending leave requests

### 🎨 UI/UX
- Responsive design for all screen sizes
- Dark/Light mode support (configurable)
- Smooth animations with Framer Motion
- Toast notifications for user feedback
- Loading states and error handling
- Accessible components

## 🛠 Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19 | UI Library |
| React Router | 7 | Client-side Routing |
| TanStack Query | 5 | Server State Management |
| Axios | Latest | HTTP Client |
| Tailwind CSS | 3 | Utility-first CSS |
| React Hook Form | 7 | Form Management |
| Yup | Latest | Form Validation |
| Recharts | 3 | Data Visualization |
| Zustand | 5 | Global State Management |
| Framer Motion | Latest | Animations |
| date-fns | 4 | Date Utilities |
| React Hot Toast | 2 | Toast Notifications |
| Lucide React | Latest | Icons |
| React Datepicker | 8 | Date Selection |

## 📁 Project Structure

```
frontend/
├── public/
│   ├── index.html           # HTML template
│   ├── favicon.ico          # App favicon
│   ├── manifest.json        # PWA manifest
│   └── robots.txt           # Robots file
│
├── src/
│   ├── api/                 # API client layer
│   │   ├── axios.js         # Axios instance configuration
│   │   ├── auth.js          # Authentication API
│   │   ├── admin.js         # Admin API endpoints
│   │   ├── employee.js      # Employee API endpoints
│   │   └── accrual.js       # Accrual API endpoints
│   │
│   ├── components/          # Reusable components
│   │   ├── admin/           # Admin-specific components
│   │   │   ├── AccrualManagement.jsx
│   │   │   ├── ApprovalModal.jsx
│   │   │   ├── AuditTrailTable.jsx
│   │   │   ├── BalanceAdjustmentForm.jsx
│   │   │   ├── DirectLeaveIssueForm.jsx
│   │   │   ├── EmployeeManagement.jsx
│   │   │   ├── FYTransitionPanel.jsx
│   │   │   ├── LeaveRequestsTable.jsx
│   │   │   └── RejectionModal.jsx
│   │   │
│   │   ├── auth/            # Authentication components
│   │   │   ├── LoginForm.jsx
│   │   │   └── ProtectedRoute.jsx
│   │   │
│   │   ├── common/          # Shared/reusable components
│   │   │   ├── Alert.jsx
│   │   │   ├── Badge.jsx
│   │   │   ├── Button.jsx
│   │   │   ├── Card.jsx
│   │   │   ├── ConfirmModal.jsx
│   │   │   ├── ErrorBoundary.jsx
│   │   │   ├── Input.jsx
│   │   │   ├── Modal.jsx
│   │   │   ├── Spinner.jsx
│   │   │   ├── Table.jsx
│   │   │   └── ToastContainer.jsx
│   │   │
│   │   ├── dashboard/       # Dashboard components
│   │   │   ├── DashboardStats.jsx
│   │   │   └── StatCard.jsx
│   │   │
│   │   ├── employee/        # Employee-specific components
│   │   │   ├── AccrualSummary.jsx
│   │   │   ├── CustomLeaveTypeSelect.jsx
│   │   │   ├── LeaveApplicationForm.jsx
│   │   │   ├── LeaveBalanceCard.jsx
│   │   │   ├── LeaveConfirmationModal.jsx
│   │   │   ├── MyHistoryTable.jsx
│   │   │   └── MyLeaveRequests.jsx
│   │   │
│   │   ├── layout/          # Layout components
│   │   │   ├── Layout.jsx
│   │   │   ├── Navbar.jsx
│   │   │   └── Sidebar.jsx
│   │   │
│   │   └── leaves/          # Leave-related components
│   │       ├── LeaveCard.jsx
│   │       ├── LeaveFilters.jsx
│   │       ├── LeaveForm.jsx
│   │       └── LeaveList.jsx
│   │
│   ├── context/             # React Context providers
│   │   ├── AuthContext.jsx  # Authentication context
│   │   └── ToastContext.jsx # Toast notification context
│   │
│   ├── hooks/               # Custom React hooks
│   │   ├── useApi.js        # API call hook
│   │   ├── useAuth.js       # Authentication hook
│   │   ├── useSessionCheck.js
│   │   └── useToast.js      # Toast notification hook
│   │
│   ├── pages/               # Page components
│   │   ├── Login.jsx        # Login page
│   │   │
│   │   ├── admin/           # Admin pages
│   │   │   ├── AccrualManagement.jsx
│   │   │   ├── AuditTrail.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Employees.jsx
│   │   │   ├── FYTransition.jsx
│   │   │   └── LeaveRequests.jsx
│   │   │
│   │   └── employee/        # Employee pages
│   │       ├── ApplyLeave.jsx
│   │       ├── Dashboard.jsx
│   │       ├── MyHistory.jsx
│   │       └── MyLeaves.jsx
│   │
│   ├── services/            # Business logic services
│   │   ├── attendanceService.js
│   │   ├── authService.js
│   │   ├── leaveService.js
│   │   └── reportService.js
│   │
│   ├── utils/               # Utility functions
│   │   ├── constants.js     # App constants
│   │   └── formatters.js    # Data formatters
│   │
│   ├── App.jsx              # Main App component
│   ├── index.js             # Application entry point
│   ├── index.css            # Global styles
│   └── setupProxy.js        # Development proxy config
│
├── Dockerfile               # Production Dockerfile
├── Dockerfile.dev           # Development Dockerfile
├── nginx.conf               # Nginx configuration
├── package.json             # Dependencies & scripts
├── postcss.config.js        # PostCSS configuration
├── tailwind.config.js       # Tailwind configuration
└── README.md                # This file
```

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# From the project root directory
./docker-manage.sh start

# Or for development mode with hot-reload
./docker-manage.sh start dev
```

### Manual Installation

#### Prerequisites
- Node.js 18+ (LTS recommended)
- npm 9+ or yarn 1.22+

#### Steps

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   # or
   yarn install
   ```

3. **Set up environment variables** (optional)
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start development server**
   ```bash
   npm start
   # or
   yarn start
   ```

5. **Open in browser**
   ```
   http://localhost:3000
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the frontend directory:

```env
# API Configuration
# For local development:
REACT_APP_API_BASE_URL=http://localhost:8000/api/v1

# For production (in .env.production):
# REACT_APP_API_BASE_URL=https://claimlen.com/api/v1

# App Configuration
REACT_APP_NAME=Employee Portal
REACT_APP_VERSION=1.0.0

# Feature Flags (optional)
REACT_APP_ENABLE_DEBUG=false
```

### Proxy Configuration

For development, the app uses a proxy to forward API requests. This is configured in [`src/setupProxy.js`](src/setupProxy.js):

```javascript
const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
    })
  );
};
```

## 🧩 Components

### Common Components

| Component | Description |
|-----------|-------------|
| `Button` | Customizable button with variants |
| `Card` | Container card with optional header/footer |
| `Modal` | Overlay modal with customizable content |
| `Alert` | Alert messages (success, error, warning, info) |
| `Badge` | Status badges with color variants |
| `Input` | Form input with validation support |
| `Table` | Data table with sorting/pagination |
| `Spinner` | Loading spinner indicator |
| `ConfirmModal` | Confirmation dialog |
| `ErrorBoundary` | Error boundary wrapper |

### Usage Example

```jsx
import { Button, Card, Modal } from './components/common';

function MyComponent() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Card title="My Card">
      <Button 
        variant="primary" 
        onClick={() => setIsOpen(true)}
      >
        Open Modal
      </Button>
      
      <Modal 
        isOpen={isOpen} 
        onClose={() => setIsOpen(false)}
        title="My Modal"
      >
        <p>Modal content here</p>
      </Modal>
    </Card>
  );
}
```

## 🔄 State Management

### Authentication State (Context)

```jsx
// Using AuthContext
import { useAuth } from './hooks/useAuth';

function MyComponent() {
  const { user, isAuthenticated, login, logout } = useAuth();
  
  if (!isAuthenticated) {
    return <Login />;
  }
  
  return <Dashboard user={user} />;
}
```

### Server State (TanStack Query)

```jsx
// Using React Query for server state
import { useQuery, useMutation } from '@tanstack/react-query';
import { getLeaveRequests, applyLeave } from './api/employee';

function LeaveRequests() {
  // Fetch data
  const { data, isLoading, error } = useQuery({
    queryKey: ['leaveRequests'],
    queryFn: getLeaveRequests
  });

  // Mutate data
  const mutation = useMutation({
    mutationFn: applyLeave,
    onSuccess: () => {
      queryClient.invalidateQueries(['leaveRequests']);
    }
  });

  return (/* ... */);
}
```

### Global State (Zustand)

```jsx
// Using Zustand for global UI state
import { create } from 'zustand';

const useStore = create((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ 
    sidebarOpen: !state.sidebarOpen 
  })),
}));
```

## 🌐 API Integration

### Axios Configuration

The app uses a configured Axios instance with:
- Base URL configuration
- Request/Response interceptors
- Automatic token refresh
- Error handling

```javascript
// src/api/axios.js
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL,
  withCredentials: true, // Include cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Handle token refresh or logout
    }
    return Promise.reject(error);
  }
);

export default api;
```

### API Modules

```javascript
// src/api/auth.js
export const login = (credentials) => api.post('/auth/login', credentials);
export const logout = () => api.post('/auth/logout');
export const getMe = () => api.get('/auth/me');

// src/api/employee.js
export const getLeaveBalance = () => api.get('/employee/leave-balance');
export const applyLeave = (data) => api.post('/employee/leave-requests', data);
```

## 🎨 Styling

### Tailwind CSS

The project uses Tailwind CSS for styling. Configuration is in `tailwind.config.js`:

```javascript
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          500: '#3b82f6',
          600: '#2563eb',
          // ...
        },
      },
    },
  },
  plugins: [],
};
```

### Component Styling Example

```jsx
function Button({ variant = 'primary', children, ...props }) {
  const variants = {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white',
    secondary: 'bg-gray-200 hover:bg-gray-300 text-gray-800',
    danger: 'bg-red-600 hover:bg-red-700 text-white',
  };

  return (
    <button
      className={`px-4 py-2 rounded-md font-medium transition-colors ${variants[variant]}`}
      {...props}
    >
      {children}
    </button>
  );
}
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage

# Run specific test file
npm test -- src/components/Button.test.js
```

### Testing Libraries

- **Jest** - Test runner
- **React Testing Library** - Component testing
- **Testing Library User Event** - User interaction simulation

### Example Test

```jsx
// src/components/Button.test.js
import { render, screen, fireEvent } from '@testing-library/react';
import Button from './Button';

describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

## 📦 Build & Deploy

### Production Build

```bash
# Create production build
npm run build

# Build output is in the 'build' directory
```

### Docker Build

```bash
# Build Docker image
docker build -t employee-portal-frontend .

# Run container
docker run -p 3000:80 employee-portal-frontend
```

### Nginx Configuration

For production, the app is served via Nginx. Configuration is in `nginx.conf`:

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Serve static files
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy (optional)
    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Health check
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
```

## 📝 Available Scripts

| Script | Description |
|--------|-------------|
| `npm start` | Start development server |
| `npm test` | Run tests |
| `npm run build` | Create production build |
| `npm run eject` | Eject from Create React App |

## 🔧 Troubleshooting

### Common Issues

#### API Connection Errors
```
Error: Network Error
```
**Solution**: Ensure the backend is running at the correct URL specified in `REACT_APP_API_BASE_URL`.

#### Cookie Not Set
```
Authentication failed
```
**Solution**: Ensure `withCredentials: true` is set in Axios and CORS is properly configured on the backend.

#### Build Failures
```
Module not found
```
**Solution**: Delete `node_modules` and `package-lock.json`, then run `npm install` again.

### Debug Mode

Enable debug mode by setting in `.env`:
```env
REACT_APP_ENABLE_DEBUG=true
```

This will show the AuthDebug component with authentication state information.

---

Built with ❤️ using React and Tailwind CSS
