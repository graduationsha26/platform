/**
 * T045: Create MobileMenu component (overlay menu for mobile)
 * Mobile Navigation Menu Component
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { X } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { getMenuItems } from '../../utils/roleHelpers';

const MobileMenu = ({ isOpen, onClose }) => {
  const { user } = useAuth();
  const location = useLocation();

  // Get menu items for current user role
  const menuItems = getMenuItems(user?.role);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden animate-fade-in"
        onClick={onClose}
      />

      {/* Menu Panel */}
      <div className="fixed inset-y-0 left-0 w-64 bg-white shadow-xl z-50 md:hidden animate-slide-in-left">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-200">
          <div>
            <h1 className="text-xl font-bold text-primary-600">TremoAI</h1>
            <p className="text-xs text-neutral-600">Tremor Monitoring</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-neutral-100 transition-colors duration-200"
            aria-label="Close menu"
          >
            <X className="w-6 h-6 text-neutral-700" />
          </button>
        </div>

        {/* User Info */}
        <div className="p-4 border-b border-neutral-200">
          <div className="bg-neutral-50 rounded-lg p-3">
            <p className="text-xs text-neutral-600">Logged in as</p>
            <p className="text-sm font-medium text-neutral-900 mt-1">{user?.name}</p>
            <p className="text-xs text-neutral-500 capitalize">{user?.role}</p>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="p-4 space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-lg transition-colors duration-200
                  ${isActive
                    ? 'bg-primary-50 text-primary-700 font-medium'
                    : 'text-neutral-700 hover:bg-neutral-50'
                  }
                `}
              >
                <Icon className={`w-5 h-5 ${isActive ? 'text-primary-700' : 'text-neutral-500'}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </>
  );
};

export default MobileMenu;
