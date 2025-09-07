import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import logoImage from '../../assets/logo2.png';
import './Layout.css';

const Layout = ({ children }) => {
  const location = useLocation();
  const isAdminRoute = location.pathname.startsWith('/admin');
  
  return (
    <div className="layout">
      {isAdminRoute && (
        <nav className="admin-nav">
          <div className="admin-nav-header">
            <Link to="/" className="logo-link">
              <img src={logoImage} alt="SHH Logo" className="nav-logo" />
              <span className="nav-title">Smart Home Health</span>
            </Link>
          </div>
          
          <div className="admin-nav-links">
            <Link 
              to="/admin" 
              className={`nav-link ${location.pathname === '/admin' ? 'active' : ''}`}
            >
              Dashboard
            </Link>
            <Link 
              to="/admin/medications" 
              className={`nav-link ${location.pathname === '/admin/medications' ? 'active' : ''}`}
            >
              Medications
            </Link>
            <Link 
              to="/admin/care-tasks" 
              className={`nav-link ${location.pathname === '/admin/care-tasks' ? 'active' : ''}`}
            >
              Care Tasks
            </Link>
            <Link 
              to="/admin/equipment" 
              className={`nav-link ${location.pathname === '/admin/equipment' ? 'active' : ''}`}
            >
              Equipment
            </Link>
            <Link 
              to="/admin/monitoring" 
              className={`nav-link ${location.pathname === '/admin/monitoring' ? 'active' : ''}`}
            >
              Monitoring
            </Link>
            <Link 
              to="/admin/settings" 
              className={`nav-link ${location.pathname === '/admin/settings' ? 'active' : ''}`}
            >
              Settings
            </Link>
          </div>
          
          <div className="admin-nav-footer">
            <Link to="/" className="back-to-dashboard">
              ← Back to Touch Dashboard
            </Link>
          </div>
        </nav>
      )}
      
      <main className={`main-content ${isAdminRoute ? 'with-nav' : ''}`}>
        {children}
      </main>
    </div>
  );
};

export default Layout;
