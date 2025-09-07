import React, { useEffect } from 'react';
import AlertsList from './AlertsList';
import ModalBase from './ModalBase';

const PulseOxModal = ({ 
  onClose,
  alertsCount,
  onAlertsViewed,
  onAlertAcknowledged // Add onAlertAcknowledged to props
}) => {

  // Mark alerts as viewed when modal opens
  useEffect(() => {
    if (alertsCount > 0 && onAlertsViewed) {
      onAlertsViewed();
    }
  }, [alertsCount, onAlertsViewed]);

  // Add a function to handle alert acknowledgment
  const handleAlertAcknowledge = (alertId) => {
    // Your existing acknowledgment code...
    
    // After successful acknowledgment, inform the parent component
    onAlertAcknowledged(alertId);
  };

  return (
    <ModalBase isOpen={true} onClose={onClose} title="Alerts">
      <div className="alerts-container">
        <AlertsList onClose={onClose} onAlertAcknowledge={handleAlertAcknowledge} />
      </div>
    </ModalBase>
  );
};

export default PulseOxModal;
