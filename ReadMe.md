# Smart Home Health Hub

Smart Home Health is a home care monitoring system designed for families who need to track the health and daily care of a loved one. It provides an easy way to record medications, vitals, equipment, and nutrition in one place, with a focus on being simple to set up and use. Built with a modern web stack (FastAPI + React, backed by PostgreSQL), it's designed to grow with your needs while staying accessible to non-technical users.

## Features

- **Real-time Vital Monitoring**: Track blood pressure, temperature, pulse oximetry (SpO2), and heart rate
- **Medication Management**: Schedule and log medication administration
- **Care Task Tracking**: Manage daily care tasks and equipment usage
- **Nutrition Logging**: Record nutritional intake and dietary information
- **Real-time Alerts**: Get notified when vitals fall outside normal ranges
- **Historical Data**: View trends and history of all health metrics
- **MQTT Integration**: Connect to external devices and home automation systems
- **Serial Device Support**: Interface with medical devices via serial connection
- **Modern Web Interface**: Responsive dashboard accessible from any device

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework for APIs
- **PostgreSQL**: Reliable database for health data storage
- **Alembic**: Database migrations
- **MQTT**: Device communication protocol
- **WebSockets**: Real-time data streaming

### Frontend
- **React**: Modern user interface framework
- **Vite**: Fast development and build tool
- **SciChart**: Advanced charting for vital signs visualization
- **Chart.js**: Additional charting capabilities

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+** (recommended: Python 3.12)
- **Node.js 16+** and npm
- **PostgreSQL 12+**
- **Git**

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/johnrcarty/smart-home-health-hub.git
cd smart-home-health-hub
```

### 2. Backend Setup

#### Create Python Virtual Environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### Configure Environment Variables

```bash
cp example.env .env
```

Edit the `.env` file with your specific configuration:

```env
# MQTT Configuration (if using MQTT devices)
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_TOPIC=medical/spo2
MQTT_CLIENT_ID=spo2_monitor
MQTT_USERNAME=your_mqtt_username
MQTT_PASSWORD=your_mqtt_password

# Vital Signs Thresholds
MIN_SPO2=90
MAX_SPO2=100
MIN_BPM=55
MAX_BPM=155

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/health_hub
```

#### Database Setup

1. Create a PostgreSQL database:
```sql
CREATE DATABASE health_hub;
```

2. Run database migrations:
```bash
alembic upgrade head
```

### 3. Frontend Setup

```bash
cd ../frontend
npm install
```

#### Configure Frontend Environment

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:8000
VITE_CHART_REFRESH_RATE=1000
VITE_CHART_TIMESPAN=5
```

## Running the Application

### Start the Backend Server

```bash
cd backend
source venv/bin/activate  # If not already activated
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: http://localhost:8000
API Documentation: http://localhost:8000/docs

### Start the Frontend Development Server

```bash
cd frontend
npm run dev
```

The web interface will be available at: http://localhost:5173

## Usage

### Initial Setup

1. Open your web browser and navigate to http://localhost:5173
2. The system will initialize with default settings
3. Configure your alert thresholds in the Settings panel
4. Begin recording vitals manually or connect supported devices

### Recording Vitals

- **Manual Entry**: Use the vitals form to manually input blood pressure, temperature, and other measurements
- **Device Integration**: Connect compatible MQTT or serial devices for automatic data collection
- **Real-time Monitoring**: View live data streams on the dashboard

### Medication Management

- Add medications with dosing schedules
- Log when medications are administered
- View medication history and adherence

### Care Tasks

- Create custom care task categories
- Schedule recurring tasks
- Track completion status

## Device Integration

### MQTT Devices

The system supports MQTT-enabled medical devices. Configure your MQTT broker settings in the backend `.env` file and ensure your devices publish to the configured topics.

### Serial Devices

For devices that communicate via serial port, the system includes a serial reader module that can be configured for various protocols.

## Development

### Backend Development

The backend uses FastAPI with the following key modules:

- `main.py`: Main application and API endpoints
- `db.py`: Database models and operations
- `mqtt_handler.py`: MQTT device communication
- `serial_reader.py`: Serial device communication
- `state_manager.py`: Real-time state management
- `sensor_manager.py`: Sensor data processing

### Frontend Development

The React frontend is organized as:

- `src/components/`: Reusable UI components
- `src/services/`: API communication services
- `src/config.js`: Configuration management

### Database Migrations

To create a new migration:

```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Verify PostgreSQL is running
   - Check database credentials in `.env`
   - Ensure database exists

2. **MQTT Connection Issues**
   - Verify MQTT broker is accessible
   - Check MQTT credentials and topics
   - Test MQTT connection independently

3. **Serial Device Issues**
   - Check device permissions
   - Verify correct port and baud rate
   - Test device communication separately

4. **Frontend Build Issues**
   - Clear node_modules and reinstall: `rm -rf node_modules && npm install`
   - Check Node.js version compatibility

### Logs

- Backend logs are available in the terminal running uvicorn
- Frontend logs are available in the browser developer console
- Database logs can be found in PostgreSQL logs

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Commit your changes: `git commit -am 'Add some feature'`
5. Push to the branch: `git push origin feature-name`
6. Submit a pull request

## Support

For support, please:

1. Check the troubleshooting section above
2. Review the API documentation at http://localhost:8000/docs
3. Open an issue on the GitHub repository

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with FastAPI and React
- Charts powered by SciChart and Chart.js
- Database management with PostgreSQL and Alembic
- Real-time communication via WebSockets and MQTT