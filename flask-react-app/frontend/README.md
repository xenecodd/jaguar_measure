# Jaguar Interface Frontend

This project contains the frontend interface for the Jaguar robot control system, developed using React.js.

## IMPORTANT!!!

### Debug Mode Configuration

When running either the frontend or backend in debug mode, communication issues with the robot API may occur. To prevent these issues, ensure Flask's `use_reloader` parameter is set to `False`. Maintaining this configuration is essential for stable communication with the robot API.

Common robot API communication errors are typically related to:
- Thread management
- Multiprocessing implementation
- Debug mode configuration

## Installation

1. Clone the project:
```bash
git clone https://github.com/your-repo/jaguar-interface.git
```

2. Navigate to the frontend directory and install dependencies:
```bash
cd jaguar-interface/frontend
npm install
```

3. Start the development server:
```bash
npm run start
```

## Technologies Used

- React.js
- Axios (for API requests)
- React Router (for navigation)

## Main Pages

- **Dashboard:** Displays the robot's general status
- **Debug Panel:** Provides detailed control of the robot

## API Integration

The frontend communicates with the backend through REST API. The API base URL is:
```javascript
export const API_BASE_URL = `http://${DEVICE_IP}:${PORT}`;