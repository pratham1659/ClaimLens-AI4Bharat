// frontend/src/components/layout/Sidebar.jsx
/**
 * Application sidebar navigation.
 */

import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FileText,
  Upload,
  History,
  FileSearch,
  MessageSquare,
  Settings,
  LogOut,
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

export function Sidebar() {
  const { user, logout } = useAuth();

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
            <FileText className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">ClaimLens</h1>
            <p className="text-xs text-gray-500">AI Compliance</p>
            <p className="text-[10px] text-gray-400 mt-0.5">
              ClaimLens AI v1.0.0
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            end={item.end}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-4 py-3 rounded-lg transition-colors",
                isActive
                  ? "bg-primary-50 text-primary-700"
                  : "text-gray-600 hover:bg-gray-50",
              )
            }
          >
            <item.icon className="w-5 h-5" />
            <span className="font-medium">{item.name}</span>
          </NavLink>
        ))}
      </nav>

      {/* User section - compact single row */}
      <div className="p-4 border-t">
        <div className="flex items-center gap-2 px-2 py-2">
          <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-medium text-gray-600">
              {user?.full_name?.charAt(0) || "U"}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-700 truncate">
              {user?.full_name || "User"}
            </p>
          </div>
          <button
            onClick={logout}
            className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0"
            title="Logout"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
