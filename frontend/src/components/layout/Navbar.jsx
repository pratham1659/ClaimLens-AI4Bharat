import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import Button from "../common/Button";
import Modal from "../common/Modal";
import { adminAPI } from "../../api/admin";

// LocalStorage key for read notification IDs
const READ_NOTIFICATIONS_KEY = "admin_read_notifications";

/**
 * Navbar Component - ALMS-style
 * Top fixed navigation bar with user dropdown menu and notifications
 */
const Navbar = () => {
  const navigate = useNavigate();
  const { user, logout, isAdmin } = useAuth();
  const [loggingOut, setLoggingOut] = useState(false);
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [showNotificationModal, setShowNotificationModal] = useState(false);
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowUserDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Get read notification IDs from localStorage
  const getReadNotificationIds = () => {
    try {
      const stored = localStorage.getItem(READ_NOTIFICATIONS_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  };

  // Save read notification IDs to localStorage
  const saveReadNotificationIds = (ids) => {
    try {
      localStorage.setItem(READ_NOTIFICATIONS_KEY, JSON.stringify(ids));
    } catch (error) {
      console.error("Failed to save read notifications:", error);
    }
  };

  // Fetch notifications (pending leave requests for admin)
  useEffect(() => {
    if (isAdmin) {
      fetchNotifications();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin]);

  const fetchNotifications = async () => {
    try {
      const leaveRequests = await adminAPI.getLeaveRequests();
      const pendingRequests = leaveRequests.filter(
        (req) => req.status === "PENDING",
      );
      const readIds = getReadNotificationIds();

      const notificationsList = pendingRequests.map((req) => ({
        id: req.id,
        type: "leave_request",
        title: "Leave Request",
        message: `${req.employee_name || req.user_name || "Employee"} requested ${req.total_days} days of ${req.leave_type_name}`,
        date: req.created_at || req.start_date,
        read: readIds.includes(req.id),
      }));

      setNotifications(notificationsList);
      setUnreadCount(notificationsList.filter((n) => !n.read).length);
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
    }
  };

  const handleLogoutClick = () => {
    setShowUserDropdown(false);
    setShowLogoutModal(true);
  };

  const handleLogoutConfirm = async () => {
    setLoggingOut(true);
    setShowLogoutModal(false);

    try {
      await logout();
      navigate("/login", { replace: true });
    } catch (error) {
      console.error("Logout error:", error);
      navigate("/login", { replace: true });
    } finally {
      setLoggingOut(false);
    }
  };

  const handleNotificationClick = () => {
    setShowNotificationModal(true);
  };

  const handleViewAllNotifications = () => {
    setShowNotificationModal(false);
    navigate("/admin/leave-requests");
  };

  const markAllAsRead = () => {
    const allIds = notifications.map((n) => n.id);
    saveReadNotificationIds(allIds);
    setNotifications(notifications.map((n) => ({ ...n, read: true })));
    setUnreadCount(0);
  };

  // Format role to capitalize first letter
  const formatRole = (role) => {
    if (!role) return "";
    return role.charAt(0).toUpperCase() + role.slice(1).toLowerCase();
  };

  // Get user initials for avatar
  const getUserInitials = (fullName) => {
    if (!fullName) return "U";
    const names = fullName.split(" ");
    if (names.length === 1) return names[0].charAt(0).toUpperCase();
    return (
      names[0].charAt(0) + names[names.length - 1].charAt(0)
    ).toUpperCase();
  };

  // Format date for notifications
  const formatNotificationDate = (dateString) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  // Toggle mobile sidebar
  const toggleMobileMenu = () => {
    setMobileMenuOpen(!mobileMenuOpen);
    window.dispatchEvent(new CustomEvent("toggleMobileSidebar"));
  };

  return (
    <>
      {/* Fixed navbar */}
      <nav className="bg-white border-b border-gray-200 fixed top-0 right-0 left-0 lg:left-64 z-10">
        <div className="mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Left side - Mobile menu button */}
            <div className="flex items-center">
              <button
                type="button"
                className="inline-flex items-center justify-center rounded-md p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 lg:hidden"
                onClick={toggleMobileMenu}
              >
                <span className="sr-only">Open sidebar</span>
                <svg
                  className="h-6 w-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
              </button>
            </div>

            {/* Right side - Notifications and User dropdown */}
            <div className="flex items-center space-x-4">
              {/* Notification Bell */}
              {isAdmin && (
                <button
                  type="button"
                  className="relative p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500"
                  onClick={handleNotificationClick}
                >
                  <span className="sr-only">View notifications</span>
                  <svg
                    className="h-6 w-6"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                    />
                  </svg>
                  {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 flex items-center justify-center w-5 h-5 text-xs font-medium text-red-600 bg-red-100 rounded-full">
                      {unreadCount}
                    </span>
                  )}
                </button>
              )}

              {/* User Dropdown Menu */}
              <div className="relative" ref={dropdownRef}>
                <button
                  type="button"
                  className="flex items-center space-x-3 rounded-full bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  onClick={() => setShowUserDropdown(!showUserDropdown)}
                >
                  <span className="sr-only">Open user menu</span>
                  <div className="flex items-center space-x-3">
                    <div className="hidden md:block text-right">
                      <p className="text-sm font-medium text-gray-700">
                        {user?.full_name || "User"}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatRole(user?.role)}
                      </p>
                    </div>
                    <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-semibold">
                      {getUserInitials(user?.full_name)}
                    </div>
                    {/* Dropdown arrow */}
                    <svg
                      className={`hidden md:block h-5 w-5 text-gray-400 transition-transform ${
                        showUserDropdown ? "rotate-180" : ""
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </div>
                </button>

                {/* Dropdown Menu */}
                {showUserDropdown && (
                  <div className="absolute right-0 z-20 mt-2 w-48 origin-top-right rounded-md bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                    {/* User info on mobile */}
                    <div className="px-4 py-2 border-b border-gray-100 md:hidden">
                      <p className="text-sm font-medium text-gray-900">
                        {user?.full_name || "User"}
                      </p>
                      <p className="text-xs text-gray-500">{user?.email}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {formatRole(user?.role)}
                      </p>
                    </div>

                    {/* Settings option */}
                    <button
                      onClick={() => {
                        setShowUserDropdown(false);
                        // Navigate to settings based on user role
                        const settingsPath = isAdmin
                          ? "/admin/settings"
                          : "/employee/settings";
                        navigate(settingsPath);
                      }}
                      className="flex w-full items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <svg
                        className="mr-3 h-5 w-5 text-gray-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                        />
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                        />
                      </svg>
                      Settings
                    </button>

                    {/* Sign out option */}
                    <button
                      onClick={handleLogoutClick}
                      className="flex w-full items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <svg
                        className="mr-3 h-5 w-5 text-gray-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                        />
                      </svg>
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Logout Confirmation Modal */}
      <Modal
        isOpen={showLogoutModal}
        onClose={() => setShowLogoutModal(false)}
        title="Confirm Sign Out"
        size="sm"
      >
        <div className="space-y-4">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <svg
                className="h-6 w-6 text-yellow-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <p className="text-sm text-gray-700">
              Are you sure you want to sign out? You will need to log in again
              to access the system.
            </p>
          </div>
          <div className="flex justify-end space-x-3 pt-4">
            <Button
              variant="secondary"
              onClick={() => setShowLogoutModal(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleLogoutConfirm}
              loading={loggingOut}
            >
              Sign Out
            </Button>
          </div>
        </div>
      </Modal>

      {/* Notifications Modal */}
      <Modal
        isOpen={showNotificationModal}
        onClose={() => setShowNotificationModal(false)}
        title="Notifications"
        size="md"
      >
        <div className="space-y-4">
          {/* Header with mark all as read */}
          {notifications.length > 0 && unreadCount > 0 && (
            <div className="flex justify-between items-center pb-2 border-b border-gray-200">
              <span className="text-sm text-gray-500">
                {unreadCount} unread notification{unreadCount !== 1 ? "s" : ""}
              </span>
              <button
                onClick={markAllAsRead}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                Mark all as read
              </button>
            </div>
          )}

          {/* Notifications List */}
          {notifications.length === 0 ? (
            <div className="text-center py-8">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
                <svg
                  className="w-6 h-6 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                  />
                </svg>
              </div>
              <p className="text-gray-500">No notifications</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`p-3 rounded-lg border transition-colors cursor-pointer ${
                    notification.read
                      ? "bg-white border-gray-200 hover:bg-gray-50"
                      : "bg-blue-50 border-blue-200 hover:bg-blue-100"
                  }`}
                  onClick={() => {
                    setShowNotificationModal(false);
                    navigate("/admin/leave-requests");
                  }}
                >
                  <div className="flex items-start space-x-3">
                    <div
                      className={`p-2 rounded-full ${
                        notification.read ? "bg-gray-100" : "bg-blue-100"
                      }`}
                    >
                      <svg
                        className={`w-4 h-4 ${
                          notification.read ? "text-gray-500" : "text-blue-600"
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                        />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p
                        className={`text-sm font-medium ${
                          notification.read ? "text-gray-700" : "text-gray-900"
                        }`}
                      >
                        {notification.title}
                      </p>
                      <p className="text-sm text-gray-500 truncate">
                        {notification.message}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {formatNotificationDate(notification.date)}
                      </p>
                    </div>
                    {!notification.read && (
                      <div className="w-2 h-2 bg-blue-600 rounded-full mt-2"></div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="pt-3 border-t border-gray-200">
              <Button
                variant="outline"
                className="w-full"
                onClick={handleViewAllNotifications}
              >
                View All Leave Requests
              </Button>
            </div>
          )}
        </div>
      </Modal>
    </>
  );
};

export default Navbar;
