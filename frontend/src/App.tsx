
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import Login from "./pages/Login";
import Chat from "./pages/Chat";
import GuestChat from "./pages/GuestChat";
import Admin from "./pages/Admin";
import WebSources from "./pages/WebSources";
import NotFound from "./pages/NotFound";
import { AuthCallback } from "./components/auth/AuthCallback";
import { ThemeProvider } from "@/components/theme-provider";
import { useEffect } from "react";

const queryClient = new QueryClient();

// Protected route component (allows guests)
const ProtectedRoute = ({ children, guestAllowed = false }: { children: React.ReactNode, guestAllowed?: boolean }) => {
  const { user, loading, isGuest } = useAuth();

  // Show loading state
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="animate-pulse">Loading...</div>
      </div>
    );
  }

  // Allow access if guest mode is enabled and route allows guests
  if (isGuest && guestAllowed) {
    return <>{children}</>;
  }

  // Redirect to login if not authenticated
  if (!user) {
    return <Navigate to="/login" />;
  }

  return <>{children}</>;
};

const AppRoutes = () => {
  const { user, isGuest } = useAuth();

  return (
    <Routes>
      {/* Default landing page is GuestChat for recruiters */}
      <Route
        path="/"
        element={
          user ? (
            <Navigate to="/chat" />
          ) : (
            <GuestChat />
          )
        }
      />
      {/* Login page for those who want to sign in */}
      <Route
        path="/login"
        element={user ? <Navigate to="/chat" /> : <Login />}
      />
      {/* Protected chat for authenticated users */}
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <Chat />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <Admin />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/web-sources"
        element={
          <ProtectedRoute>
            <WebSources />
          </ProtectedRoute>
        }
      />
      {/* OAuth callback route for handling authentication redirects */}
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
};

// Force dark theme
const DarkThemeEnforcer = ({ children }: { children: React.ReactNode }) => {
  useEffect(() => {
    document.documentElement.classList.add('dark');
  }, []);

  return <>{children}</>;
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider defaultTheme="dark" forcedTheme="dark">
      <DarkThemeEnforcer>
        <AuthProvider>
          <TooltipProvider>
            <Toaster />
            <Sonner />
            <BrowserRouter>
              <AppRoutes />
            </BrowserRouter>
          </TooltipProvider>
        </AuthProvider>
      </DarkThemeEnforcer>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
