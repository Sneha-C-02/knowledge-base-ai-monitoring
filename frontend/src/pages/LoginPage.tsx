import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { Database, Lock, KeyRound, ArrowLeft, CheckCircle2, Copy, Check, AlertCircle, ShieldCheck, RefreshCw } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useSystem } from '../context/SystemContext';
import { Card, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { TextInput } from '../components/common/TextInput';
import { api } from '../api/client';

interface LoginPageProps {
  initialMode?: 'login' | 'forgot' | 'reset';
}

export function LoginPage({ initialMode = 'login' }: LoginPageProps) {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { login } = useAuth();
  const { addActivity } = useSystem();

  // Mode state: 'login' | 'forgot' | 'reset'
  const [mode, setMode] = useState<'login' | 'forgot' | 'reset'>(() => {
    const urlMode = searchParams.get('mode');
    if (urlMode === 'forgot' || urlMode === 'reset') return urlMode;
    return initialMode;
  });

  // Form fields
  const [username, setUsername] = useState(
    searchParams.get('username') || location.state?.username || ''
  );
  const [password, setPassword] = useState('');
  const [resetToken, setResetToken] = useState(
    searchParams.get('token') || location.state?.resetToken || ''
  );
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Verified user from token pre-validation
  const [verifiedUser, setVerifiedUser] = useState<string | null>(
    location.state?.verifiedUser || null
  );
  const [isVerifyingToken, setIsVerifyingToken] = useState(false);

  // Status feedback
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState(
    location.state?.successMessage || ''
  );
  const [infoMessage, setInfoMessage] = useState(
    location.state?.infoMessage || ''
  );
  const [isLoading, setIsLoading] = useState(false);
  const [copiedToken, setCopiedToken] = useState(false);

  const verifyToken = useCallback(async (token: string) => {
    const trimmed = token.trim();
    if (!trimmed) {
      setVerifiedUser(null);
      return;
    }
    setIsVerifyingToken(true);
    try {
      const res = await api.verifyResetToken(trimmed);
      setVerifiedUser(res.username);
      setUsername(res.username);
      setError('');
    } catch (err: any) {
      setVerifiedUser(null);
      setError(err?.message || 'Invalid or expired reset token. Please request a new one.');
    } finally {
      setIsVerifyingToken(false);
    }
  }, []);

  // Sync mode and prefill if query params, location state, or initialMode change
  useEffect(() => {
    const urlToken = searchParams.get('token') || location.state?.resetToken;
    const urlMode = searchParams.get('mode');
    const urlUsername = searchParams.get('username') || location.state?.username;

    if (urlUsername) {
      setUsername(urlUsername);
    }

    if (urlToken) {
      setResetToken(urlToken);
      setMode('reset');
      verifyToken(urlToken);
    } else if (urlMode === 'forgot' || initialMode === 'forgot') {
      setMode('forgot');
    } else if (urlMode === 'reset' || initialMode === 'reset') {
      setMode('reset');
    } else {
      setMode('login');
    }

    if (location.state?.infoMessage) {
      setInfoMessage(location.state.infoMessage);
    }
    if (location.state?.successMessage) {
      setSuccessMessage(location.state.successMessage);
    }
  }, [searchParams, location.state, initialMode, verifyToken]);

  const switchMode = (newMode: 'login' | 'forgot' | 'reset') => {
    setMode(newMode);
    setError('');
    setSuccessMessage('');
    setInfoMessage('');
    setPassword('');
    setNewPassword('');
    setConfirmPassword('');
    const targetPath =
      newMode === 'login'
        ? '/login'
        : newMode === 'forgot'
        ? '/forgot-password'
        : '/reset-password';
    navigate(targetPath, { replace: true, state: { username } });
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');
    setIsLoading(true);

    const success = await login(username, password);
    if (success) {
      addActivity({
        type: 'system',
        message: 'USER_LOGIN',
        user: username,
      });
      navigate('/dashboard');
    } else {
      setError('Invalid username or password. (Hint: admin / admin123)');
      setIsLoading(false);
    }
  };

  const handleForgotPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');
    setInfoMessage('');

    if (!username.trim()) {
      setError('Please enter your username.');
      return;
    }

    setIsLoading(true);
    try {
      const response = await api.forgotPassword(username.trim());
      setResetToken(response.reset_token);
      setVerifiedUser(response.username);
      setMode('reset');
      const message = `Reset token generated successfully! Valid for ${response.expires_in_minutes} minutes. We have prefilled it below.`;
      setInfoMessage(message);
      navigate('/reset-password', {
        replace: true,
        state: {
          resetToken: response.reset_token,
          username: response.username,
          verifiedUser: response.username,
          infoMessage: message,
        },
      });
    } catch (err: any) {
      setError(err?.message || 'Failed to request password reset. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');

    if (!resetToken.trim()) {
      setError('Reset token is required.');
      return;
    }

    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('New password and confirmation password do not match.');
      return;
    }

    setIsLoading(true);
    try {
      const targetUser = verifiedUser || username.trim() || undefined;
      const response = await api.resetPassword(
        resetToken.trim(),
        newPassword,
        targetUser
      );

      // Successfully reset password
      const successText =
        response.message || 'Password has been reset successfully! Please sign in with your new password.';
      setResetToken('');
      setNewPassword('');
      setConfirmPassword('');
      setPassword('');
      setVerifiedUser(null);
      setError('');
      setInfoMessage('');
      setSuccessMessage(successText);
      setMode('login');
      navigate('/login', {
        replace: true,
        state: {
          username: targetUser,
          successMessage: successText,
        },
      });
    } catch (err: any) {
      setError(err?.message || 'Failed to reset password. Please verify your token.');
    } finally {
      setIsLoading(false);
    }
  };

  const copyTokenToClipboard = async () => {
    if (!resetToken) return;
    try {
      await navigator.clipboard.writeText(resetToken);
      setCopiedToken(true);
      setTimeout(() => setCopiedToken(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md flex flex-col items-center">
        <Database className="text-primary-600 mb-4" size={48} />
        <h2 className="text-center text-3xl font-extrabold text-slate-900">
          {mode === 'login' && 'Sign in to your account'}
          {mode === 'forgot' && 'Forgot Password'}
          {mode === 'reset' && 'Reset Your Password'}
        </h2>
        <p className="mt-2 text-center text-sm text-slate-600">
          {mode === 'login' && 'Knowledge Base AI Support'}
          {mode === 'forgot' && 'User Management & Recovery'}
          {mode === 'reset' && 'Create a new secure password'}
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <Card>
          <CardContent className="p-8">
            {/* Global Error Banner */}
            {error && (
              <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm flex items-start gap-2">
                <AlertCircle size={18} className="mt-0.5 shrink-0 text-red-500" />
                <span>{error}</span>
              </div>
            )}

            {/* Success Banner */}
            {successMessage && (
              <div className="mb-6 bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-md text-sm flex items-start gap-2">
                <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-emerald-600" />
                <span>{successMessage}</span>
              </div>
            )}

            {/* Info Banner */}
            {infoMessage && (
              <div className="mb-6 bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-md text-sm flex items-start gap-2">
                <ShieldCheck size={18} className="mt-0.5 shrink-0 text-blue-600" />
                <span>{infoMessage}</span>
              </div>
            )}

            {/* --- Mode 1: LOGIN FORM --- */}
            {mode === 'login' && (
              <form className="space-y-6" onSubmit={handleLoginSubmit}>
                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-slate-700 mb-1">
                    Username
                  </label>
                  <TextInput
                    id="username"
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="admin"
                    disabled={isLoading}
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label htmlFor="password" className="block text-sm font-medium text-slate-700">
                      Password
                    </label>
                    <button
                      type="button"
                      onClick={() => switchMode('forgot')}
                      className="text-xs font-semibold text-primary-600 hover:text-primary-700 transition-colors focus:outline-none focus:underline"
                    >
                      Forgot password?
                    </button>
                  </div>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <Lock size={18} />
                    </div>
                    <TextInput
                      id="password"
                      type="password"
                      className="pl-10"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      disabled={isLoading}
                    />
                  </div>
                </div>

                <Button type="submit" className="w-full" isLoading={isLoading}>
                  Sign in
                </Button>
              </form>
            )}

            {/* --- Mode 2: FORGOT PASSWORD FORM --- */}
            {mode === 'forgot' && (
              <form className="space-y-6" onSubmit={handleForgotPasswordSubmit}>
                <div className="text-sm text-slate-600">
                  Enter your username below to request a secure password reset token.
                </div>

                <div>
                  <label htmlFor="forgot-username" className="block text-sm font-medium text-slate-700 mb-1">
                    Username
                  </label>
                  <TextInput
                    id="forgot-username"
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter your username (e.g. admin)"
                    disabled={isLoading}
                  />
                </div>

                <Button type="submit" className="w-full" isLoading={isLoading}>
                  Request Reset Token
                </Button>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                  <button
                    type="button"
                    onClick={() => switchMode('login')}
                    className="inline-flex items-center gap-1 font-medium text-slate-600 hover:text-slate-900 transition-colors"
                  >
                    <ArrowLeft size={14} /> Back to Sign in
                  </button>
                  <button
                    type="button"
                    onClick={() => switchMode('reset')}
                    className="font-medium text-primary-600 hover:text-primary-700 transition-colors"
                  >
                    Already have a token?
                  </button>
                </div>
              </form>
            )}

            {/* --- Mode 3: RESET PASSWORD FORM --- */}
            {mode === 'reset' && (
              <form className="space-y-6" onSubmit={handleResetPasswordSubmit}>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label htmlFor="reset-token" className="block text-sm font-medium text-slate-700">
                      Reset Token
                    </label>
                    {resetToken && (
                      <button
                        type="button"
                        onClick={copyTokenToClipboard}
                        className="inline-flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700"
                        title="Copy token to clipboard"
                      >
                        {copiedToken ? (
                          <>
                            <Check size={12} className="text-emerald-600" />
                            <span className="text-emerald-600">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy size={12} />
                            <span>Copy token</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <KeyRound size={18} />
                    </div>
                    <TextInput
                      id="reset-token"
                      type="text"
                      className="pl-10 font-mono text-xs"
                      required
                      value={resetToken}
                      onChange={(e) => {
                        setResetToken(e.target.value);
                        setVerifiedUser(null);
                      }}
                      onBlur={() => {
                        if (resetToken.trim().length > 10 && !verifiedUser) {
                          verifyToken(resetToken);
                        }
                      }}
                      placeholder="Paste your reset token here"
                      disabled={isLoading}
                    />
                  </div>
                  {isVerifyingToken && (
                    <div className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
                      <RefreshCw size={12} className="animate-spin text-primary-600" />
                      <span>Verifying token validity...</span>
                    </div>
                  )}
                  {verifiedUser && (
                    <div className="mt-1 flex items-center gap-1.5 text-xs text-emerald-700 font-medium">
                      <CheckCircle2 size={13} className="text-emerald-600 shrink-0" />
                      <span>
                        Verified token for account: <strong className="font-semibold">{verifiedUser}</strong>
                      </span>
                    </div>
                  )}
                </div>

                <div>
                  <label htmlFor="new-password" className="block text-sm font-medium text-slate-700 mb-1">
                    New Password
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <Lock size={18} />
                    </div>
                    <TextInput
                      id="new-password"
                      type="password"
                      className="pl-10"
                      required
                      minLength={6}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="At least 6 characters"
                      disabled={isLoading}
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="confirm-password" className="block text-sm font-medium text-slate-700 mb-1">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <Lock size={18} />
                    </div>
                    <TextInput
                      id="confirm-password"
                      type="password"
                      className="pl-10"
                      required
                      minLength={6}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Re-enter your new password"
                      disabled={isLoading}
                    />
                  </div>
                </div>

                <Button type="submit" className="w-full" isLoading={isLoading}>
                  Reset Password
                </Button>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                  <button
                    type="button"
                    onClick={() => switchMode('login')}
                    className="inline-flex items-center gap-1 font-medium text-slate-600 hover:text-slate-900 transition-colors"
                  >
                    <ArrowLeft size={14} /> Back to Sign in
                  </button>
                  <button
                    type="button"
                    onClick={() => switchMode('forgot')}
                    className="font-medium text-primary-600 hover:text-primary-700 transition-colors"
                  >
                    Need a token?
                  </button>
                </div>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
