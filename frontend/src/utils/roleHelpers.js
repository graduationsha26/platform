/**
 * T042: Implement role helpers utility (getMenuItems, getDashboardPath)
 * Role-Based Navigation Helpers
 */

import { LayoutDashboard, Users, BarChart3, FileText, Settings } from 'lucide-react';

/**
 * Get menu items for a specific role
 * @param {string} role - User role ('doctor' or 'patient')
 * @returns {Array} Array of menu item objects
 */
export const getMenuItems = (role) => {
  if (role === 'doctor') {
    return [
      {
        label: 'Dashboard',
        path: '/doctor/dashboard',
        icon: LayoutDashboard,
      },
      {
        label: 'Patients',
        path: '/doctor/patients',
        icon: Users,
      },
      {
        label: 'Analytics',
        path: '/doctor/analytics',
        icon: BarChart3,
      },
      {
        label: 'Reports',
        path: '/doctor/reports',
        icon: FileText,
      },
      {
        label: 'Settings',
        path: '/doctor/settings',
        icon: Settings,
      },
    ];
  }

  if (role === 'admin') {
    return getMenuItems('doctor');
  }

  return [];
};

/**
 * Get dashboard path for a specific role
 * @param {string} role - User role ('doctor' or 'patient')
 * @returns {string} Dashboard path
 */
export const getDashboardPath = (role) => {
  return '/doctor/dashboard';
};

/**
 * Check if a user role has access to a specific route
 * @param {string} role - User role ('doctor' or 'patient')
 * @param {string} route - Route path
 * @returns {boolean} True if user has access
 */
export const hasAccess = (role, route) => {
  const menuItems = getMenuItems(role);
  return menuItems.some(item => item.path === route);
};
