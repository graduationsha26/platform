/**
 * T043: Create TopBar component with user info and logout button
 * Top Navigation Bar Component
 */

import React from 'react';
import { Menu, LogOut } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import Button from '../common/Button';

const TopBar = ({ onMenuToggle }) => {
  const { user, logout } = useAuth();

  // T051: Logout button click handler
  const handleLogout = () => {
    logout();
  };

  return (
    <div className="bg-white border-b border-neutral-200 px-4 py-3 flex items-center justify-between">
      {/* Left: Hamburger Menu (mobile only) */}
      <div className="flex items-center">
        <button
          onClick={onMenuToggle}
          className="md:hidden p-2 rounded-lg hover:bg-neutral-100 transition-colors duration-200"
          aria-label="Toggle menu"
        >
          <Menu className="w-6 h-6 text-neutral-700" />
        </button>

        <div className="hidden md:block">
          <h2 className="text-xl font-bold text-neutral-900">TremoAI</h2>
        </div>
      </div>

      {/* Right: User Info and Logout */}
      <div className="flex items-center gap-4">
        {/* User Info */}
        <div className="text-right hidden sm:block">
          <p className="text-sm font-medium text-neutral-900">{user?.name}</p>
          <p className="text-xs text-neutral-500 capitalize">{user?.role}</p>
        </div>

        {/* Logout Button */}
        <Button
          variant="secondary"
          onClick={handleLogout}
          className="flex items-center gap-2"
        >
          <LogOut className="w-4 h-4" />
          <span className="hidden sm:inline">Logout</span>
        </Button>
      </div>
    </div>
  );
};

export default TopBar;
