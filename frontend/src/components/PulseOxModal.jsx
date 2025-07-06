import React, { useEffect } from 'react';
import AlertsList from './AlertsList';

const PulseOxModal = ({ 
  onClose,
  alertsCount,
  onAlertsViewed
}) => {

  // Mark alerts as viewed when modal opens
  useEffect(() => {
    if (alertsCount > 0 && onAlertsViewed) {
      onAlertsViewed();
    }
  }, [alertsCount, onAlertsViewed]);

  return (
    <div className="pulse-ox-modal">

      <div className="alerts-container">
        <AlertsList onClose={onClose} />
      </div>
    </div>
  );
};

export default PulseOxModal;
