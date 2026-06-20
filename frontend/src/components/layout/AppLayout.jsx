/**
 * T046-T048: Create AppLayout component integrating TopBar, Sidebar, MobileMenu
 * Application Layout Shell Component
 */

import React, { useState } from 'react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import MobileMenu from './MobileMenu';

const AppLayout = ({ children }) => {
  // T046: State management for mobile menu
  // T047: Hamburger menu toggle functionality
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(prev => !prev);
  };

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* T044: Sidebar (Desktop) - T048: Responsive classes */}
      <Sidebar />

      {/* T045: Mobile Menu (Mobile) - T048: Responsive classes */}
      <MobileMenu isOpen={isMobileMenuOpen} onClose={closeMobileMenu} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* T043: TopBar */}
        <TopBar onMenuToggle={toggleMobileMenu} />

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
