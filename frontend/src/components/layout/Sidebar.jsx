/**
 * T044: Create Sidebar component with role-based menu items
 * T052: Implement menu item navigation
 * T053: Add active route highlighting
 * Sidebar Navigation Component (Desktop)
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { getMenuItems } from '../../utils/roleHelpers';

const Sidebar = () => {
  const { user } = useAuth();
  const location = useLocation();

  // Get menu items for current user role
  const menuItems = getMenuItems(user?.role);

  return (
    <div className="hidden md:flex md:flex-col md:w-64 bg-white border-r border-neutral-200 h-full">
      {/* Logo/Brand */}
      <div className="p-6 border-b border-neutral-200">
        <h1 className="text-2xl font-bold text-primary-600">TremoAI</h1>
        <p className="text-sm text-neutral-600 mt-1">Tremor Monitoring</p>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 p-4 space-y-2">
        {menuItems.map((item) => {
          const Icon = item.icon;
          // T053: Active route highlighting — use startsWith for parent routes
          // (e.g., /doctor/patients stays active on /doctor/patients/1/edit)
          const isActive =
            location.pathname === item.path ||
            (item.path !== '/' && location.pathname.startsWith(item.path + '/'));

          return (
            <Link
              key={item.path}
              to={item.path}
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

      {/* Footer Info */}
      <div className="p-4 border-t border-neutral-200">
        <div className="bg-neutral-50 rounded-lg p-3">
          <p className="text-xs text-neutral-600">Logged in as</p>
          <p className="text-sm font-medium text-neutral-900 mt-1">{user?.name}</p>
          <p className="text-xs text-neutral-500 capitalize">{user?.role}</p>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
