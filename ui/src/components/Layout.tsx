import { NavLink, Outlet } from "react-router-dom";
import { Activity, LayoutDashboard, ListTodo, BookOpen } from "lucide-react";

const NAV = [
  { to: "/",         label: "Dashboard",  icon: LayoutDashboard },
  { to: "/tasks",    label: "Tasks",       icon: ListTodo },
  { to: "/knowledge",label: "Knowledge",   icon: BookOpen },
];

export function Layout() {
  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="w-60 bg-gray-900 text-gray-300 flex flex-col shrink-0">
        <div className="px-5 py-5 border-b border-gray-800">
          <div className="flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-indigo-400" />
            <span className="font-bold text-white text-sm leading-tight">
              Self-Healing<br />
              <span className="font-normal text-gray-400 text-xs">Multi-Agent Framework</span>
            </span>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-600 text-white"
                    : "text-gray-400 hover:bg-gray-800 hover:text-white"
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-5 py-4 border-t border-gray-800">
          <p className="text-xs text-gray-600">API: localhost:8000</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
