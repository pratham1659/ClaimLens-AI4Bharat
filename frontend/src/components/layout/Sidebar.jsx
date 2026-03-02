// frontend/src/components/layout/Sidebar.jsx

import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FileText,
  Upload,
  History,
  FileSearch,
  MessageSquare,
  LogOut,
  X,
} from "lucide-react";
import { clsx } from "clsx";
import { useAuth } from "../../context/AuthContext";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard, end: true },
  { name: "New Claim", href: "/claims/new", icon: Upload, end: true },
  { name: "Claims History", href: "/claims", icon: History, end: true },
  { name: "Policy Search", href: "/policies", icon: FileSearch, end: true },
  { name: "Policy Chat", href: "/policy-chat", icon: MessageSquare, end: true },
];

export function Sidebar({ isOpen, onClose }) {
  const { user, logout } = useAuth();

  return (
    <>
      {/* Desktop Sidebar - Always visible on lg+ */}
      <aside className="hidden lg:flex fixed left-0 top-0 h-screen w-64 bg-white border-r border-gray-200 flex-col z-30">
        <SidebarContent user={user} logout={logout} />
      </aside>

      {/* Mobile Sidebar - Slide-in drawer */}
      <aside
        className={clsx(
          "lg:hidden fixed left-0 top-0 h-full w-72 max-w-[85vw] bg-white z-50 flex flex-col",
          "transform transition-transform duration-300 ease-out shadow-2xl",
          isOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg touch-manipulation z-10"
          aria-label="Close menu"
        >
          <X className="w-5 h-5" />
        </button>

        <SidebarContent user={user} logout={logout} onItemClick={onClose} />
      </aside>
    </>
  );
}

// Shared sidebar content component
function SidebarContent({ user, logout, onItemClick }) {
  return (
    <>
      {/* Logo */}
      <div className="p-4 sm:p-6 border-b">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <FileText className="w-6 h-6 text-white" />
          </div>
          <div className="min-w-0">
            <h1 className="text-lg font-bold text-gray-900">ClaimLens</h1>
            <p className="text-xs text-gray-500">AI Compliance</p>
            <p className="text-[10px] text-gray-400 mt-0.5">
              ClaimLens AI v1.0.0
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 sm:p-4 space-y-1 overflow-y-auto">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            end={item.end}
            onClick={onItemClick}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-3 sm:px-4 py-3 rounded-lg transition-colors touch-manipulation",
                isActive
                  ? "bg-primary-50 text-primary-700"
                  : "text-gray-600 hover:bg-gray-50 active:bg-gray-100",
              )
            }
          >
            <item.icon className="w-5 h-5 flex-shrink-0" />
            <span className="font-medium truncate">{item.name}</span>
          </NavLink>
        ))}
      </nav>

      {/* User section */}
      <div className="p-3 sm:p-4 border-t mt-auto">
        <div className="flex items-center gap-2 px-2 py-2">
          <div className="w-9 h-9 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0">
            <span className="text-sm font-medium text-gray-600">
              {user?.full_name?.charAt(0) || "U"}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-700 truncate">
              {user?.full_name || "User"}
            </p>
            <p className="text-xs text-gray-500 truncate">
              {user?.email || ""}
            </p>
          </div>
          <button
            onClick={() => {
              logout();
              onItemClick?.();
            }}
            className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0 touch-manipulation"
            title="Logout"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </div>
    </>
  );
}
