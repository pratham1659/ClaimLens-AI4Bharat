// frontend/src/pages/LoginPage.jsx


import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FileText,
  Mail,
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [serverError, setServerError] = useState("");

  const { login } = useAuth();
  const navigate = useNavigate();

  // Validate email format
  const validateEmail = (email) => {
    if (!email.trim()) {
      return "Email is required";
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return "Please enter a valid email address";
    }
    return "";
  };

  // Validate password - REDUCED STRICTNESS: only require minimum 4 characters
  const validatePassword = (password) => {
    if (!password) {
      return "Password is required";
    }
    if (password.length < 4) {
      return "Password must be at least 4 characters";
    }
    return "";
  };

  // Real-time validation
  useEffect(() => {
    const newErrors = {};

    if (touched.email) {
      const emailError = validateEmail(email);
      if (emailError) newErrors.email = emailError;
    }

    if (touched.password) {
      const passwordError = validatePassword(password);
      if (passwordError) newErrors.password = passwordError;
    }

    setErrors(newErrors);
  }, [email, password, touched]);

  // Handle field blur for showing validation
  const handleBlur = (field) => {
    setTouched({ ...touched, [field]: true });
  };

  // Validate entire form
  const validateForm = () => {
    const emailError = validateEmail(email);
    const passwordError = validatePassword(password);

    const formErrors = {};
    if (emailError) formErrors.email = emailError;
    if (passwordError) formErrors.password = passwordError;

    setErrors(formErrors);
    setTouched({ email: true, password: true });

    return Object.keys(formErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError("");

    // Validate form before making API call
    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      const success = await login(email, password);
      if (success) {
        navigate("/dashboard");
      } else {
        setServerError("Invalid email or password. Please try again.");
      }
    } catch (error) {
      setServerError(error.message || "An error occurred. Please try again.");
    }

    setLoading(false);
  };

  // Check if form is valid for enabling submit button
  const isFormValid =
    email.trim() && password && !errors.email && !errors.password;

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="w-full max-w-md">
        {/* Logo - Responsive sizing */}
        <div className="text-center mb-6 sm:mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 sm:w-16 sm:h-16 bg-primary-600 rounded-xl sm:rounded-2xl mb-3 sm:mb-4 shadow-lg">
            <FileText className="w-7 h-7 sm:w-8 sm:h-8 text-white" />
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
            ClaimLens AI
          </h1>
          <p className="text-sm sm:text-base text-gray-600 mt-1">
            Medical Insurance Compliance Platform
          </p>
        </div>

        {/* Login Form - Mobile responsive */}
        <div className="card p-6 sm:p-8 shadow-lg">
          <h2 className="text-lg sm:text-xl font-semibold text-gray-900 mb-4 sm:mb-6">
            Welcome back
          </h2>

          {/* Server Error Alert */}
          {serverError && (
            <div className="mb-4 p-3 sm:p-4 bg-danger-50 border border-danger-200 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-danger-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-danger-700">{serverError}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
            {/* Email Field */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5 sm:mb-2">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onBlur={() => handleBlur("email")}
                  className={`input pl-10 pr-10 text-base sm:text-sm ${
                    errors.email && touched.email
                      ? "border-danger-500 focus:ring-danger-500"
                      : touched.email && !errors.email && email
                        ? "border-success-500 focus:ring-success-500"
                        : ""
                  }`}
                  placeholder="you@example.com"
                  autoComplete="email"
                  inputMode="email"
                />
                {touched.email && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    {errors.email ? (
                      <AlertCircle className="w-5 h-5 text-danger-500" />
                    ) : email ? (
                      <CheckCircle className="w-5 h-5 text-success-500" />
                    ) : null}
                  </div>
                )}
              </div>
              {errors.email && touched.email && (
                <p className="mt-1.5 text-xs sm:text-sm text-danger-500 flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {errors.email}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5 sm:mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onBlur={() => handleBlur("password")}
                  className={`input pl-10 pr-12 text-base sm:text-sm ${
                    errors.password && touched.password
                      ? "border-danger-500 focus:ring-danger-500"
                      : touched.password && !errors.password && password
                        ? "border-success-500 focus:ring-success-500"
                        : ""
                  }`}
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 p-1 touch-manipulation"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}
                </button>
              </div>
              {errors.password && touched.password && (
                <p className="mt-1.5 text-xs sm:text-sm text-danger-500 flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {errors.password}
                </p>
              )}
              <p className="mt-1.5 text-xs text-gray-500">
                Minimum 4 characters
              </p>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !isFormValid}
              className={`btn-primary w-full py-3 text-base sm:text-sm font-medium touch-manipulation ${
                !isFormValid && !loading ? "opacity-60 cursor-not-allowed" : ""
              }`}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Signing in...
                </span>
              ) : (
                "Sign in"
              )}
            </button>
          </form>

          {/* Register Link */}
          <p className="mt-4 sm:mt-6 text-center text-sm text-gray-600">
            Don't have an account?{" "}
            <Link
              to="/register"
              className="text-primary-600 hover:text-primary-700 font-medium touch-manipulation"
            >
              Sign up
            </Link>
          </p>
        </div>

        {/* Footer - Mobile friendly */}
        <p className="mt-4 sm:mt-6 text-center text-xs text-gray-500">
          By signing in, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>
    </div>
  );
}
