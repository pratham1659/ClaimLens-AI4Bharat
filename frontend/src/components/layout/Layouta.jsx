import React, { useEffect } from "react";
import { useAuth } from "../../hooks/useAuth";
import { useSessionCheck } from "../../hooks/useSessionCheck";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";

/**
 * Layout Component - ALMS-style
 * Main application layout wrapper with fixed sidebar and navbar
 */
const Layout = ({ children }) => {
  const { user, checkAuth } = useAuth();
  useSessionCheck(5); // Check every 5 minutes

  useEffect(() => {
    // Verify session is still valid when layout mounts
    const verifySession = async () => {
      if (!user) {
        await checkAuth();
      }
    };

    verifySession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content area */}
      <div className="lg:pl-64 flex flex-col min-h-screen">
        {/* Navbar */}
        <Navbar />

        {/* Page content - Add padding-top to account for fixed navbar (h-16 = 64px) */}
        <main className="flex-1 pt-16">
          <div className="py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
