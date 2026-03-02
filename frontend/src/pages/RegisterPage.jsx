// frontend/src/pages/RegisterPage.jsx


import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FileText,
  Mail,
  Lock,
  User,
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

export function RegisterPage() {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    full_name: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [serverError, setServerError] = useState("");

  const { register } = useAuth();
  const navigate = useNavigate();

  // Validation functions matching backend requirements
  const validateFullName = (name) => {
    if (!name.trim()) {
      return "Full name is required";
    }
    if (name.trim().length < 2) {
      return "Name must be at least 2 characters";
    }
    if (name.trim().length > 255) {
      return "Name must be at most 255 characters";
    }
    return "";
  };

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

  // Password validation - must match backend requirements exactly:
  // - Minimum 8 characters
  // - At least one uppercase letter
  // - At least one lowercase letter
  // - At least one digit
  const validatePassword = (password) => {
    const errors = [];

    if (!password) {
      return "Password is required";
    }
    if (password.length < 8) {
      errors.push("at least 8 characters");
    }
    if (password.length > 100) {
      errors.push("at most 100 characters");
    }
    if (!/[A-Z]/.test(password)) {
      errors.push("one uppercase letter");
    }
    if (!/[a-z]/.test(password)) {
      errors.push("one lowercase letter");
    }
    if (!/[0-9]/.test(password)) {
      errors.push("one digit");
    }

    if (errors.length > 0) {
      return `Password must contain ${errors.join(", ")}`;
    }
    return "";
  };

  const validateConfirmPassword = (confirmPassword, password) => {
    if (!confirmPassword) {
      return "Please confirm your password";
    }
    if (confirmPassword !== password) {
      return "Passwords do not match";
    }
    return "";
  };

  // Real-time validation
  useEffect(() => {
    const newErrors = {};

    if (touched.full_name) {
      const nameError = validateFullName(formData.full_name);
      if (nameError) newErrors.full_name = nameError;
    }

    if (touched.email) {
      const emailError = validateEmail(formData.email);
      if (emailError) newErrors.email = emailError;
    }

    if (touched.password) {
      const passwordError = validatePassword(formData.password);
      if (passwordError) newErrors.password = passwordError;
    }

    if (touched.confirmPassword) {
      const confirmError = validateConfirmPassword(
        formData.confirmPassword,
        formData.password,
      );
      if (confirmError) newErrors.confirmPassword = confirmError;
    }

    setErrors(newErrors);
  }, [formData, touched]);

  // Handle field blur for showing validation
  const handleBlur = (field) => {
    setTouched({ ...touched, [field]: true });
  };

  // Validate entire form
  const validateForm = () => {
    const nameError = validateFullName(formData.full_name);
    const emailError = validateEmail(formData.email);
    const passwordError = validatePassword(formData.password);
    const confirmError = validateConfirmPassword(
      formData.confirmPassword,
      formData.password,
    );

    const formErrors = {};
    if (nameError) formErrors.full_name = nameError;
    if (emailError) formErrors.email = emailError;
    if (passwordError) formErrors.password = passwordError;
    if (confirmError) formErrors.confirmPassword = confirmError;

    setErrors(formErrors);
    setTouched({
      full_name: true,
      email: true,
      password: true,
      confirmPassword: true,
    });

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
      const success = await register({
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
      });

      if (success) {
        navigate("/login");
      } else {
        setServerError("Registration failed. Please try again.");
      }
    } catch (error) {
      setServerError(error.message || "An error occurred. Please try again.");
    }

    setLoading(false);
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  // Check if form is valid for enabling submit button
  const isFormValid =
    formData.full_name.trim() &&
    formData.email.trim() &&
    formData.password &&
    formData.confirmPassword &&
    !errors.full_name &&
    !errors.email &&
    !errors.password &&
    !errors.confirmPassword;

  // Password strength indicator based on backend requirements
  const getPasswordStrength = (password) => {
    if (!password) return { level: 0, text: "", color: "" };

    let score = 0;
    if (password.length >= 8) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;

    if (score === 0)
      return { level: 1, text: "Too weak", color: "bg-danger-500" };
    if (score === 1) return { level: 1, text: "Weak", color: "bg-danger-500" };
    if (score === 2) return { level: 2, text: "Fair", color: "bg-warning-500" };
    if (score === 3) return { level: 3, text: "Good", color: "bg-warning-400" };
    return { level: 4, text: "Strong", color: "bg-success-500" };
  };

  const passwordStrength = getPasswordStrength(formData.password);

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
            Create your account
          </p>
        </div>

        {/* Register Form - Mobile responsive */}
        <div className="card p-6 sm:p-8 shadow-lg">
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
            {/* Full Name Field */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5 sm:mb-2">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  name="full_name"
                  value={formData.full_name}
                  onChange={handleChange}
                  onBlur={() => handleBlur("full_name")}
                  className={`input pl-10 pr-10 text-base sm:text-sm ${
                    errors.full_name && touched.full_name
                      ? "border-danger-500 focus:ring-danger-500"
                      : touched.full_name &&
                          !errors.full_name &&
                          formData.full_name
                        ? "border-success-500 focus:ring-success-500"
                        : ""
                  }`}
                  placeholder="John Doe"
                  autoComplete="name"
                />
                {touched.full_name && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    {errors.full_name ? (
                      <AlertCircle className="w-5 h-5 text-danger-500" />
                    ) : formData.full_name ? (
                      <CheckCircle className="w-5 h-5 text-success-500" />
                    ) : null}
                  </div>
                )}
              </div>
              {errors.full_name && touched.full_name && (
                <p className="mt-1.5 text-xs sm:text-sm text-danger-500 flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {errors.full_name}
                </p>
              )}
            </div>

            {/* Email Field */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5 sm:mb-2">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  onBlur={() => handleBlur("email")}
                  className={`input pl-10 pr-10 text-base sm:text-sm ${
                    errors.email && touched.email
                      ? "border-danger-500 focus:ring-danger-500"
                      : touched.email && !errors.email && formData.email
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
                    ) : formData.email ? (
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
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  onBlur={() => handleBlur("password")}
                  className={`input pl-10 pr-12 text-base sm:text-sm ${
                    errors.password && touched.password
                      ? "border-danger-500 focus:ring-danger-500"
                      : touched.password &&
                          !errors.password &&
                          formData.password
                        ? "border-success-500 focus:ring-success-500"
                        : ""
                  }`}
                  placeholder="••••••••"
                  autoComplete="new-password"
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
              {/* Password strength indicator */}
              {formData.password && (
                <div className="mt-2">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${passwordStrength.color}`}
                        style={{
                          width: `${(passwordStrength.level / 4) * 100}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs text-gray-500">
                      {passwordStrength.text}
                    </span>
                  </div>
                </div>
              )}
              <p className="mt-1.5 text-xs text-gray-500">
                Min 8 characters, uppercase, lowercase, and number required
              </p>
            </div>

            {/* Confirm Password Field */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5 sm:mb-2">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  onBlur={() => handleBlur("confirmPassword")}
                  className={`input pl-10 pr-12 text-base sm:text-sm ${
                    errors.confirmPassword && touched.confirmPassword
                      ? "border-danger-500 focus:ring-danger-500"
                      : touched.confirmPassword &&
                          !errors.confirmPassword &&
                          formData.confirmPassword
                        ? "border-success-500 focus:ring-success-500"
                        : ""
                  }`}
                  placeholder="••••••••"
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 p-1 touch-manipulation"
                  aria-label={
                    showConfirmPassword ? "Hide password" : "Show password"
                  }
                >
                  {showConfirmPassword ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}
                </button>
              </div>
              {errors.confirmPassword && touched.confirmPassword && (
                <p className="mt-1.5 text-xs sm:text-sm text-danger-500 flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {errors.confirmPassword}
                </p>
              )}
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
                  Creating account...
                </span>
              ) : (
                "Create account"
              )}
            </button>
          </form>

          {/* Login Link */}
          <p className="mt-4 sm:mt-6 text-center text-sm text-gray-600">
            Already have an account?{" "}
            <Link
              to="/login"
              className="text-primary-600 hover:text-primary-700 font-medium touch-manipulation"
            >
              Sign in
            </Link>
          </p>
        </div>

        {/* Footer - Mobile friendly */}
        <p className="mt-4 sm:mt-6 text-center text-xs text-gray-500">
          By creating an account, you agree to our Terms of Service and Privacy
          Policy
        </p>
      </div>
    </div>
  );
}
