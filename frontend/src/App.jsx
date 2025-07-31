import { useState, useEffect, useRef } from "react";
import "./App.css";
import ChartBlock from "./components/ChartBlock";
import ClockCard from "./components/ClockCard";
import BloodPressureCard from "./components/BloodPressureCard";
import TemperatureCard from "./components/TemperatureCard";
import ModalBase from "./components/ModalBase";
import SettingsForm from "./components/SettingsForm";
import VitalsForm from "./components/VitalsForm";
// Import the minimalist icons from the file
import { 
  SettingsIcon, 
  MinimalistVentIcon, 
  MinimalistPulseOxIcon, 
  ClipboardIcon, 
  HistoryIcon,
  MedicationIcon
} from "./components/Icons";
import logoImage from './assets/logo2.png';
import config from './config';
import AlertsList from "./components/AlertsList";
// Import the PulseOxModal component
import PulseOxModal from "./components/PulseOxModal";
import EquipmentModal from "./components/EquipmentModal";
import HistoryModal from "./components/HistoryModal";
import MedicationModal from "./components/MedicationModal";

export default function App() {
  // Add state for modal
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  
  // Add state for notification counts
  const [ventNotifications, setVentNotifications] = useState(2); // Example count
  const [pulseOxNotifications, setPulseOxNotifications] = useState(3); // Example count
  const [pulseOxAlerts, setPulseOxAlerts] = useState(0);
  const [equipmentDueCount, setEquipmentDueCount] = useState(0);

  const [sensorValues, setSensorValues] = useState({
    spo2: null,
    bpm: null,
    perfusion: null,
    skin_temp: null,
    body_temp: null
  });

  const [datasets, setDatasets] = useState({
    spo2: [],
    bpm: [],
    perfusion: []
  });

  const [bpHistory, setBpHistory] = useState([]);
  const [tempHistory, setTempHistory] = useState([]);

  const initialDataReceived = useRef(false);
  const prevAlarmActive = useRef(false);

  useEffect(() => {
    console.log(`Connecting to WebSocket at: ${config.wsUrl}`);
    const ws = new WebSocket(config.wsUrl);

    ws.onopen = () => console.log("WebSocket connected");

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "sensor_update" && msg.state) {
        const alarmActive = !!msg.state.alarm;

        // Only trigger blink if alarm transitions from false to true
        if (!prevAlarmActive.current && alarmActive) {
          setIsAlarmBlinking(true);
          setTimeout(() => setIsAlarmBlinking(false), 100); // .1 sec on
        }
        setIsAlarmActive(alarmActive);
        prevAlarmActive.current = alarmActive;

        setSensorValues({
          spo2: msg.state.spo2,
          bpm: msg.state.bpm,
          perfusion: msg.state.perfusion,
          skin_temp: msg.state.skin_temp,
          body_temp: msg.state.body_temp
        });

        const now = Date.now();

        if (msg.state.bp) {
          const bpData = msg.state.bp
            .filter(reading => 
              (reading.systolic_bp !== null && reading.systolic_bp !== 0) || 
              (reading.diastolic_bp !== null && reading.diastolic_bp !== 0) || 
              (reading.map_bp !== null && reading.map_bp !== 0)
            )
            .map(reading => ({
              datetime: reading.datetime || Date.now().toString(),
              systolic: reading.systolic_bp,
              diastolic: reading.diastolic_bp,
              map: reading.map_bp
            }));
          
          setBpHistory(bpData);
        }

        if (msg.state.temp) {
          const tempData = msg.state.temp
            .filter(reading => 
              (reading.skin_temp !== null && reading.skin_temp !== 0) || 
              (reading.body_temp !== null && reading.body_temp !== 0)
            )
            .map(reading => ({
              datetime: reading.datetime || Date.now().toString(),
              skin: reading.skin_temp,
              body: reading.body_temp
            }));
          
          setTempHistory(tempData);
        }

        setDatasets(prev => {
          const newState = { ...prev };
          let hasValidUpdate = false;

          if (msg.state.spo2 !== null && msg.state.spo2 !== undefined) {
            newState.spo2 = [...prev.spo2, { x: now, y: msg.state.spo2 }].slice(-1800);
            hasValidUpdate = true;
          }

          if (msg.state.bpm !== null && msg.state.bpm !== undefined) {
            newState.bpm = [...prev.bpm, { x: now, y: msg.state.bpm }].slice(-1800);
            hasValidUpdate = true;
          }

          if (msg.state.perfusion !== null && msg.state.perfusion !== undefined) {
            newState.perfusion = [...prev.perfusion, { x: now, y: msg.state.perfusion }].slice(-1800);
            hasValidUpdate = true;
          }

          if (hasValidUpdate && !initialDataReceived.current) {
            initialDataReceived.current = true;
            setBpHistory(prev => [...prev]);
            setTempHistory(prev => [...prev]);
          }

          return newState;
        });

        // Handle alerts count - only update if it's specifically included in the message
        if (msg.state.alerts_count !== undefined) {
          setPulseOxAlerts(msg.state.alerts_count);
        }
        
        // Similarly for vent notifications if the server sends them
        if (msg.state.vent_notifications !== undefined) {
          setVentNotifications(msg.state.vent_notifications);
        }
        // Update equipment due count from websocket
        if (msg.state.equipment_due_count !== undefined) {
          setEquipmentDueCount(msg.state.equipment_due_count);
        }
      }
      
      // Handle explicit alert acknowledgment messages if your server sends them
      else if (msg.type === "alert_acknowledged") {
        // Update alerts count based on server response
        if (msg.alerts_count !== undefined) {
          setPulseOxAlerts(msg.alerts_count);
        }
      }
    };

    ws.onclose = () => console.log("WebSocket disconnected");

    return () => ws.close();
  }, []);

  const calculateAvg = (data) => {
    if (data.length === 0) return 0;
    return data.reduce((sum, item) => sum + item.y, 0) / data.length;
  };

  const calculateMin = (data) => {
    if (data.length === 0) return 0;
    return Math.min(...data.map(item => item.y));
  };

  const calculateMax = (data) => {
    if (data.length === 0) return 0;
    return Math.max(...data.map(item => item.y));
  };

  // Add these state hooks and handlers
  const [isVentModalOpen, setIsVentModalOpen] = useState(false);
  const [isPulseOxModalOpen, setIsPulseOxModalOpen] = useState(false);
  const [isVitalsModalOpen, setIsVitalsModalOpen] = useState(false);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [isMedicationModalOpen, setIsMedicationModalOpen] = useState(false);
  const [isAlarmActive, setIsAlarmActive] = useState(false);
  const [isAlarmBlinking, setIsAlarmBlinking] = useState(false);
  const alarmBlinkInterval = useRef(null);

  // Continuous blinking effect for alarm
  useEffect(() => {
    if (isAlarmActive) {
      // Start interval to toggle blinking
      if (!alarmBlinkInterval.current) {
        alarmBlinkInterval.current = setInterval(() => {
          setIsAlarmBlinking(prev => !prev);
        }, 500); // 500ms blink interval
      }
    } else {
      // Stop blinking and clear interval
      if (alarmBlinkInterval.current) {
        clearInterval(alarmBlinkInterval.current);
        alarmBlinkInterval.current = null;
      }
      setIsAlarmBlinking(false);
    }
    // Cleanup on unmount
    return () => {
      if (alarmBlinkInterval.current) {
        clearInterval(alarmBlinkInterval.current);
        alarmBlinkInterval.current = null;
      }
      setIsAlarmBlinking(false);
    };
  }, [isAlarmActive]);

  // Close all modals function for reuse
  const closeAllModals = () => {
    setIsVentModalOpen(false);
    setIsPulseOxModalOpen(false);
    setIsSettingsModalOpen(false);
    setIsVitalsModalOpen(false);
    setIsHistoryModalOpen(false);
    setIsMedicationModalOpen(false);
  };

  // Add handler functions
  const handleVentClick = () => {
    if (isVentModalOpen) {
      // If already open, just close it
      setIsVentModalOpen(false);
    } else {
      // Close all then open this one
      closeAllModals();
      setIsVentModalOpen(true);
    }
    // DON'T clear notifications when clicked
    // setVentNotifications(0); - Remove this line
  };

  const handlePulseOxClick = () => {
    if (isPulseOxModalOpen) {
      // If already open, just close it
      setIsPulseOxModalOpen(false);
    } else {
      // Close all then open this one
      closeAllModals();
      setIsPulseOxModalOpen(true);
    }
    // DON'T clear notifications when clicked - wait for acknowledgment instead
  };

  const handleSettingsClick = () => {
    if (isSettingsModalOpen) {
      // If already open, just close it
      setIsSettingsModalOpen(false);
    } else {
      // Close all then open this one
      closeAllModals();
      setIsSettingsModalOpen(true);
    }
  };

  const handleVitalsClick = () => {
    if (isVitalsModalOpen) {
      // If already open, just close it
      setIsVitalsModalOpen(false);
    } else {
      // Close all then open this one
      closeAllModals();
      setIsVitalsModalOpen(true);
    }
  };

  const handleHistoryClick = () => {
    if (isHistoryModalOpen) {
      setIsHistoryModalOpen(false);
    } else {
      closeAllModals();
      setIsHistoryModalOpen(true);
    }
  };

  const handleMedicationClick = () => {
    if (isMedicationModalOpen) {
      setIsMedicationModalOpen(false);
    } else {
      closeAllModals();
      setIsMedicationModalOpen(true);
    }
  };

  // Add this function to handle alert acknowledgment
  const handleAlertAcknowledged = (alertId) => {
    // Fetch updated alert count from server
    fetch(`${config.apiUrl}/api/monitoring/alerts/count`)
      .then(response => response.json())
      .then(data => {
        if (data && data.count !== undefined) {
          setPulseOxAlerts(data.count);
        }
      })
      .catch(err => console.error('Error fetching updated alert count:', err));
  };

  // Add function to acknowledge all alerts
  const [acknowledgeAllLoading, setAcknowledgeAllLoading] = useState(false);

  const acknowledgeAllAlerts = async () => {
    setAcknowledgeAllLoading(true);
    try {
      // Get all unacknowledged alerts
      const response = await fetch(`${config.apiUrl}/api/monitoring/alerts?include_acknowledged=false`);
      if (!response.ok) throw new Error('Failed to fetch alerts');
      const alerts = await response.json();
      // Acknowledge each alert
      await Promise.all(alerts.map(alert =>
        fetch(`${config.apiUrl}/api/monitoring/alerts/${alert.id}/acknowledge`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
      ));
      // Optionally refresh alerts count/state
      // setPulseOxAlerts(0); // or refetch count
      // Optionally show a success message
      alert('All open alerts acknowledged!');
    } catch (err) {
      console.error('Error acknowledging all alerts:', err);
      alert('Failed to acknowledge all alerts.');
    } finally {
      setAcknowledgeAllLoading(false);
    }
  };

  // Track if alerts viewed POST has been sent for this open
  const [alertsViewedSent, setAlertsViewedSent] = useState(false);

  // Only call handlePulseOxAlertsViewed once when modal is opened
  useEffect(() => {
    if (isPulseOxModalOpen && !alertsViewedSent) {
      // handlePulseOxAlertsViewed();
      setAlertsViewedSent(true);
    }
    if (!isPulseOxModalOpen) {
      setAlertsViewedSent(false);
    }
  }, [isPulseOxModalOpen, alertsViewedSent]);

  return (
    <div className="dashboard-wrapper">
      <div className={`header-section${isAlarmBlinking ? ' alarm-blink' : ''}${isAlarmActive ? ' alarm-active' : ''}`}>
        <div className="logo-container">
          <img src={logoImage} alt="Logo" className="header-logo" />
          <div className="logo-text">Smart Home Health</div>
        </div>
        
        <div className="menu-container">
          <div className="icon-wrapper">
            <button 
              className={`menu-button ${isVentModalOpen ? 'active' : ''}`}
              onClick={handleVentClick}
              aria-label="Ventilator"
            >
              <MinimalistVentIcon />
            </button>
            {equipmentDueCount > 0 && <div className="badge">{equipmentDueCount}</div>}
          </div>
          
          <div className="icon-wrapper">
            <button 
              className={`menu-button ${isPulseOxModalOpen ? 'active' : ''}`}
              onClick={handlePulseOxClick}
              aria-label="Pulse Oximeter"
            >
              <MinimalistPulseOxIcon />
              {pulseOxAlerts > 0 && <div className="badge">{pulseOxAlerts}</div>}
            </button>
          </div>
          
          <div className="icon-wrapper">
            <button 
              className={`menu-button ${isVitalsModalOpen ? 'active' : ''}`}
              onClick={handleVitalsClick}
              aria-label="Manual Vitals Entry"
            >
              <ClipboardIcon />
            </button>
          </div>
          
          <div className="icon-wrapper">
            <button 
              className={`menu-button ${isMedicationModalOpen ? 'active' : ''}`}
              onClick={handleMedicationClick}
              aria-label="Medication Tracker"
            >
              <MedicationIcon />
            </button>
          </div>
          
          <div className="icon-wrapper">
            <button 
              className={`menu-button ${isHistoryModalOpen ? 'active' : ''}`}
              onClick={handleHistoryClick}
              aria-label="History"
            >
              <HistoryIcon />
            </button>
          </div>
          <div className="icon-wrapper">
            <button 
              className={`menu-button ${isSettingsModalOpen ? 'active' : ''}`}
              onClick={handleSettingsClick}
              aria-label="Settings"
            >
              <SettingsIcon />
            </button>
          </div>
        </div>
        
        <div className="datetime-container">
          <ClockCard />
        </div>
      </div>
      
      <div className="dashboard-container">
        <div className="values-column">
          <div className="value-display spo2">
            <h3 className="value-title">SpO₂</h3>
            <div className="value-content">
              <div className="value">{sensorValues.spo2 ?? "--"}</div>
              <div className="unit">%</div>
            </div>
            <div className="value-stats">
              {datasets.spo2.length > 0 ? (
                <>
                  <span>
                    Avg: {calculateAvg(datasets.spo2.filter(item => item.y !== 0)).toFixed(1)}%
                  </span>
                  <span>
                    Min: {calculateMin(datasets.spo2.filter(item => item.y !== 0)).toFixed(0)}%
                  </span>
                  <span>
                    Max: {calculateMax(datasets.spo2.filter(item => item.y !== 0)).toFixed(0)}%
                  </span>
                </>
              ) : (
                <span>No data available</span>
              )}
            </div>
          </div>
          
          <div className="value-display bpm">
            <h3 className="value-title">Heart Rate</h3>
            <div className="value-content">
              <div className="value">{sensorValues.bpm ?? "--"}</div>
              <div className="unit">BPM</div>
            </div>
            <div className="value-stats">
              {datasets.bpm.length > 0 ? (
                <>
                  <span>
                    Avg: {calculateAvg(datasets.bpm.filter(item => item.y !== 0)).toFixed(0)}
                  </span>
                  <span>
                    Min: {calculateMin(datasets.bpm.filter(item => item.y !== 0)).toFixed(0)}
                  </span>
                  <span>
                    Max: {calculateMax(datasets.bpm.filter(item => item.y !== 0)).toFixed(0)}
                  </span>
                </>
              ) : (
                <span>No data available</span>
              )}
            </div>
          </div>
          
          <div className="value-display perfusion">
            <h3 className="value-title">Perfusion</h3>
            <div className="value-content">
              <div className="value">{sensorValues.perfusion ?? "--"}</div>
              <div className="unit">%</div>
            </div>
            <div className="value-stats">
              {datasets.perfusion.length > 0 ? (
                <>
                  <span>
                    Avg: {calculateAvg(datasets.perfusion.filter(item => item.y !== 0)).toFixed(1)}
                  </span>
                  <span>
                    Min: {calculateMin(datasets.perfusion.filter(item => item.y !== 0)).toFixed(1)}
                  </span>
                  <span>
                    Max: {calculateMax(datasets.perfusion.filter(item => item.y !== 0)).toFixed(1)}
                  </span>
                </>
              ) : (
                <span>No data available</span>
              )}
            </div>
          </div>
        </div>

        <div className="charts-column">
          <div className="chart-block">
            <div className="chart-inner">
              <ChartBlock
                title="SpO₂ Monitor"
                yLabel="SpO2"
                yMin={40}
                yMax={100}
                color="blue"
                dataset={datasets.spo2}
                showXaxis={false}
                showYaxis={true}
              />
            </div>
          </div>

          <div className="chart-block">
            <div className="chart-inner">
              <ChartBlock
                title="BPM"
                yLabel="BPM"
                yMin={40}
                yMax={160}
                color="green"
                dataset={datasets.bpm}
                showXaxis={false}
                showYaxis={true}
              />
            </div>
          </div>

          <div className="chart-block">
            <div className="chart-inner">
              <ChartBlock
                title="Perfusion Monitor"
                yLabel="PAI (%)"
                yMin={40}
                yMax={160}
                color="orange"
                dataset={datasets.perfusion}
                showXaxis={true}
                showYaxis={true}
              />
            </div>
          </div>
        </div>

        <div className="right-column">
          <div className="bp-container">
            <BloodPressureCard bpHistory={bpHistory} />
          </div>

          <div className="temp-container">
            <TemperatureCard tempHistory={tempHistory} />
          </div>
        </div>
      </div>

      {/* Settings Modal */}
      <ModalBase
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
        title="Settings"
      >
        <SettingsForm />
      </ModalBase>

      {/* Equipment Modal - fills entire modal space, no inner modal */}
      <ModalBase
        isOpen={isVentModalOpen}
        onClose={() => setIsVentModalOpen(false)}
        title="Equipment Tracker"
      >
        <div className="equipment-tracker-full">
          {/* Render only the inner equipment tracker UI, not the modal shell */}
          <EquipmentModal isOpen={true} noModal={true} onClose={() => {}} equipmentDueCount={equipmentDueCount} />
        </div>
      </ModalBase>

      {/* Pulse Oximeter Modal - Example */}
      {isPulseOxModalOpen && (
        <PulseOxModal
          onClose={() => setIsPulseOxModalOpen(false)}
          alertsCount={pulseOxAlerts}
          onAlertAcknowledged={handleAlertAcknowledged}
        />
      )}

      {/* Manual Vitals Entry Modal */}
      <ModalBase
        isOpen={isVitalsModalOpen}
        onClose={() => setIsVitalsModalOpen(false)}
        title="Manual Vitals Entry"
      >
        <VitalsForm 
          onSave={(data) => {
            console.log("Vitals saved:", data);
            // Potentially update any state here as needed
          }}
          onClose={() => setIsVitalsModalOpen(false)}
        />
      </ModalBase>

      {/* History Modal */}
      {isHistoryModalOpen && (
        <HistoryModal onClose={() => setIsHistoryModalOpen(false)} />
      )}

      {/* Medication Modal */}
      {isMedicationModalOpen && (
        <MedicationModal onClose={() => setIsMedicationModalOpen(false)} />
      )}
    </div>
  );
}
