import React, { createContext, useContext, useState, useEffect } from 'react';

const AdminPatientContext = createContext();

export const useAdminPatient = () => {
  const context = useContext(AdminPatientContext);
  if (!context) {
    throw new Error('useAdminPatient must be used within AdminPatientProvider');
  }
  return context;
};

export const AdminPatientProvider = ({ children }) => {
  const [selectedPatientId, setSelectedPatientId] = useState(() => {
    // Load from session storage on init
    return sessionStorage.getItem('adminSelectedPatientId') || null;
  });

  const setPatientId = (patientId) => {
    setSelectedPatientId(patientId);
    if (patientId) {
      sessionStorage.setItem('adminSelectedPatientId', patientId);
    } else {
      sessionStorage.removeItem('adminSelectedPatientId');
    }
  };

  const value = {
    selectedPatientId,
    setPatientId
  };

  return (
    <AdminPatientContext.Provider value={value}>
      {children}
    </AdminPatientContext.Provider>
  );
};

export default AdminPatientContext;
