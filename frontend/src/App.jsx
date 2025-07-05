import { useState, useEffect, useRef } from "react";
import "./App.css";
import ChartBlock from "./components/ChartBlock";
import ClockCard from "./components/ClockCard";
import BloodPressureCard from "./components/BloodPressureCard";
import TemperatureCard from "./components/TemperatureCard";
import ModalBase from "./components/ModalBase";
import SettingsForm from "./components/SettingsForm";
import logoImage from './assets/logo2.png';
import config from './config';

// Update the icon dimensions in VentIcon and PulseOxIcon components
const SettingsIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"></circle>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
  </svg>
);

const VentIcon = () => (
  <svg width="34" height="34" viewBox="0 0 150 150" xmlns="http://www.w3.org/2000/svg">
    {/* Device Body */}
    <rect x="10" y="20" width="100" height="110" rx="8" ry="8" fill="#444" stroke="#222" strokeWidth="2"/>

    {/* Screen */}
    <rect x="20" y="30" width="80" height="40" rx="2" ry="2" fill="#ccc" stroke="#888" strokeWidth="1"/>
    <text x="25" y="55" fontSize="8" fill="#000">Ventilator</text>

    {/* Knob on Side */}
    <circle cx="115" cy="75" r="10" fill="#337ab7" stroke="#222" strokeWidth="1"/>
    <circle cx="115" cy="75" r="4" fill="#fff"/>

    {/* Speaker Grill */}
    <circle cx="30" cy="100" r="6" fill="#222"/>
    <circle cx="30" cy="100" r="2" fill="#555"/>

    {/* Power Button */}
    <circle cx="90" cy="110" r="6" fill="#0a0" stroke="#222" strokeWidth="1"/>
    <text x="87" y="113" fontSize="5" fill="#fff">⏻</text>

    {/* Ports at Bottom */}
    <rect x="50" y="120" width="10" height="5" fill="#888"/>
    <rect x="65" y="120" width="10" height="5" fill="#888"/>
  </svg>
);

const PulseOxIcon = () => (
  <svg width="34" height="34" viewBox="0 0 150 100" xmlns="http://www.w3.org/2000/svg">
    {/* Device Body */}
    <rect x="10" y="10" width="130" height="80" rx="12" ry="12" fill="#333" stroke="#111" strokeWidth="2"/>

    {/* Screen Area */}
    <rect x="25" y="25" width="100" height="40" rx="4" ry="4" fill="#0a0a0a" stroke="#555" strokeWidth="1"/>

    {/* SpO2 Label */}
    <text x="35" y="42" fontSize="8" fill="#0f0">SpO₂</text>

    {/* SpO2 Value */}
    <text x="80" y="42" fontSize="12" fill="#0f0" fontWeight="bold">98%</text>

    {/* BPM Label */}
    <text x="35" y="58" fontSize="8" fill="#0ff">BPM</text>

    {/* BPM Value */}
    <text x="80" y="58" fontSize="12" fill="#0ff" fontWeight="bold">76</text>

    {/* Status Light */}
    <circle cx="125" cy="70" r="5" fill="#0f0" stroke="#222" strokeWidth="1"/>
  </svg>
);

export default function App() {
  // Add state for modal
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  
  // Add state for notification counts
  const [ventNotifications, setVentNotifications] = useState(2); // Example count
  const [pulseOxNotifications, setPulseOxNotifications] = useState(3); // Example count

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

  useEffect(() => {
    console.log(`Connecting to WebSocket at: ${config.wsUrl}`);
    const ws = new WebSocket(config.wsUrl);

    ws.onopen = () => console.log("WebSocket connected");

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "sensor_update" && msg.state) {
        const now = Date.now();

        setSensorValues({
          spo2: msg.state.spo2,
          bpm: msg.state.bpm,
          perfusion: msg.state.perfusion,
          skin_temp: msg.state.skin_temp,
          body_temp: msg.state.body_temp
        });

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

  // Add handler functions
  const handleVentClick = () => {
    setIsPulseOxModalOpen(false);
    setIsSettingsModalOpen(false);
    setIsVentModalOpen(prev => !prev);
    // Clear notifications when clicked
    setVentNotifications(0);
  };

  const handlePulseOxClick = () => {
    setIsVentModalOpen(false);
    setIsSettingsModalOpen(false);
    setIsPulseOxModalOpen(prev => !prev);
    // Clear notifications when clicked
    setPulseOxNotifications(0);
  };

  const handleSettingsClick = () => {
  // Close other modals when opening this one
  setIsVentModalOpen(false);
  setIsPulseOxModalOpen(false);
  
  // Toggle this modal
  setIsSettingsModalOpen(prev => !prev);
};

  return (
    <div className="dashboard-wrapper">
      <div className="header-section">
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
              <VentIcon />
            </button>
            {ventNotifications > 0 && <div className="badge">{ventNotifications}</div>}
          </div>
          
          <div className="icon-wrapper">
            <button 
              className={`menu-button ${isPulseOxModalOpen ? 'active' : ''}`}
              onClick={handlePulseOxClick}
              aria-label="Pulse Oximeter"
            >
              <PulseOxIcon />
            </button>
            {pulseOxNotifications > 0 && <div className="badge">{pulseOxNotifications}</div>}
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

      {/* Ventilator Modal - Example */}
      <ModalBase
        isOpen={isVentModalOpen}
        onClose={() => setIsVentModalOpen(false)}
        title="Ventilator Settings"
      >
        <div>Ventilator settings content here...</div>
      </ModalBase>

      {/* Pulse Oximeter Modal - Example */}
      <ModalBase
        isOpen={isPulseOxModalOpen}
        onClose={() => setIsPulseOxModalOpen(false)}
        title="Pulse Oximeter Settings"
      >
        <div>Pulse oximeter settings content here...</div>
      </ModalBase>
    </div>
  );
}
