import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

/**
 * Reusable modal component that can display various content
 */
const ModalBase = ({ isOpen, onClose, title, children }) => {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    
    // Prevent body scroll when modal is open on mobile
    if (isOpen && isMobile) {
      document.body.style.overflow = 'hidden';
    }
    
    return () => {
      window.removeEventListener('resize', checkMobile);
      document.body.style.overflow = 'auto';
    };
  }, [isOpen, isMobile]);

  if (!isOpen) return null;

  const handleClose = () => {
    if (onClose) {
      onClose();
    }
  };

  return (
    <div className={`modal-overlay ${isMobile ? 'mobile' : ''}`} onClick={!isMobile ? handleClose : undefined}>
      <div className={`modal-container ${isMobile ? 'mobile' : ''}`} onClick={e => e.stopPropagation()}>
        <div className={`modal-header ${isMobile ? 'mobile' : ''}`}>
          {isMobile && (
            <button className="modal-back-button" onClick={handleClose}>
              ← Back
            </button>
          )}
          <h2 className="modal-title">{title}</h2>
          {!isMobile && (
            <button className="modal-close" onClick={handleClose}>×</button>
          )}
        </div>
        <div className={`modal-body ${isMobile ? 'mobile' : ''}`}>
          {children}
        </div>
      </div>
    </div>
  );
};

ModalBase.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  title: PropTypes.oneOfType([PropTypes.string, PropTypes.node]).isRequired,
  children: PropTypes.node.isRequired
};

export default ModalBase;