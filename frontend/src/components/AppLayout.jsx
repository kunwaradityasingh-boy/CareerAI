import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";

const navItems = [
  {
    path: "/dashboard",
    label: "Dashboard",
    icon: "⌂",
    badge: null,
  },
  {
    path: "/resume-analyzer",
    label: "Resume Analyzer",
    icon: "⚡",
    badge: "AI Powered",
  },
  {
    path: "/skill-gap",
    label: "Skill Gap Analysis",
    icon: "🎯",
    badge: null,
  },
  {
    path: "/roadmap",
    label: "Career Roadmap",
    icon: "🗺️",
    badge: null,
  },
  {
    path: "/profile",
    label: "My Profile",
    icon: "👤",
    badge: null,
  },
];

function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  function handleLogout() {
    logout();
    navigate("/", { replace: true });
  }

  const userInitial = (user?.name || "S").trim().charAt(0).toUpperCase();

  return (
    <div className="dashboard-shell">
      {/* Mobile Backdrop */}
      {mobileMenuOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Main Persistent Sidebar */}
      <aside className={`dashboard-sidebar ${mobileMenuOpen ? "open" : ""}`}>
        <div className="dashboard-brand">
          <span className="dashboard-brand-mark">✦</span>
          <span>CareerAI</span>
          <button
            type="button"
            className="mobile-close-btn"
            onClick={() => setMobileMenuOpen(false)}
            aria-label="Close navigation"
          >
            ✕
          </button>
        </div>

        <div className="sidebar-label">WORKSPACE</div>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/dashboard"}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? "active" : ""}`
              }
              onClick={() => setMobileMenuOpen(false)}
            >
              <span className="sidebar-link-icon">{item.icon}</span>
              <span className="sidebar-link-text">{item.label}</span>
              {item.badge && <span className="sidebar-badge">{item.badge}</span>}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-user">
            <div className="user-avatar">{userInitial}</div>
            <div className="sidebar-user-info">
              <strong>{user?.name || "Student"}</strong>
              <span>{user?.email || "Registered Student"}</span>
            </div>
          </div>

          <button
            type="button"
            className="logout-button"
            onClick={handleLogout}
          >
            <span>↪</span>
            Sign out
          </button>
        </div>
      </aside>

      {/* Main Workspace Area */}
      <main className="dashboard-main">
        {/* Top Header Bar */}
        <header className="dashboard-topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="mobile-menu-trigger"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open navigation menu"
            >
              ☰
            </button>
            <div>
              <span className="topbar-label">CAREER INTELLIGENCE PLATFORM</span>
              <p className="topbar-title">Student Workspace</p>
            </div>
          </div>

          <div className="topbar-right">
            <div className="topbar-account">
              <span className="account-status"></span>
              Account active
            </div>
            <div className="topbar-avatar" title={user?.name || "Student"}>
              {userInitial}
            </div>
          </div>
        </header>

        {/* Dynamic Nested Content */}
        <div className="dashboard-content">
          <Outlet />

          <footer className="dashboard-footer">
            CareerAI · AI-Powered Career & Placement Intelligence Platform
          </footer>
        </div>
      </main>
    </div>
  );
}

export default AppLayout;
