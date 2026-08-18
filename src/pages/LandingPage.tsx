import { Link } from 'react-router-dom';
import { ArrowRight, ShieldCheck, Database, Zap } from 'lucide-react';
import { Button } from '../components/common/Button';

export function LandingPage() {
  return (
    <div className="min-h-screen bg-indigo-50/50 flex flex-col font-sans overflow-hidden relative selection:bg-purple-500/30">
      
      {/* Dynamic Background Effects - Lavender/Purple themed */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10">
        <div className="absolute -top-[40%] -left-[10%] w-[70%] h-[70%] rounded-full bg-purple-300/30 blur-[120px] animate-pulse" style={{ animationDuration: '8s' }}></div>
        <div className="absolute top-[20%] -right-[20%] w-[60%] h-[60%] rounded-full bg-indigo-300/30 blur-[120px] animate-pulse" style={{ animationDuration: '12s' }}></div>
        <div className="absolute -bottom-[30%] left-[20%] w-[80%] h-[80%] rounded-full bg-fuchsia-300/30 blur-[150px] animate-pulse" style={{ animationDuration: '10s' }}></div>
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 mix-blend-overlay"></div>
      </div>

      <header className="py-6 px-6 sm:px-12 flex items-center justify-between z-10 border-b border-indigo-100 bg-white/60 backdrop-blur-md shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Database className="text-white" size={22} />
          </div>
          <span className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-900 to-purple-800">KnowledgeBase AI</span>
        </div>
        <Link to="/login">
          <Button className="bg-indigo-100 hover:bg-indigo-200 text-indigo-900 font-semibold border-0 transition-all duration-300">Sign In</Button>
        </Link>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center text-center px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto py-24 z-10">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/80 border border-indigo-200 shadow-sm backdrop-blur-md mb-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
          <span className="flex h-2 w-2 rounded-full bg-purple-500 animate-ping absolute"></span>
          <span className="relative flex h-2 w-2 rounded-full bg-purple-500"></span>
          <span className="text-sm font-semibold text-indigo-900 ml-2">System v2.0 is now live</span>
        </div>
        
        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold text-slate-900 tracking-tight mb-8 leading-tight animate-in fade-in slide-in-from-bottom-6 duration-1000">
          Intelligent <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-700 to-indigo-700">Support</span> <br className="hidden sm:block"/>& Proactive <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-700 to-fuchsia-700">Monitoring</span>
        </h1>
        
        <p className="text-lg sm:text-xl text-slate-700 font-medium max-w-3xl mb-12 leading-relaxed animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-150">
          Empower your analytical instrument environment with AI-assisted support querying, automated log analysis, and real-time alerts. Stop issues before they become critical.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-6 mb-24 animate-in fade-in slide-in-from-bottom-10 duration-1000 delay-300">
          <Link to="/login">
            <Button className="w-full sm:w-auto px-8 py-4 text-lg font-semibold rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-xl shadow-indigo-500/30 transition-all duration-300 hover:scale-105 hover:shadow-indigo-500/40 border-0">
              Access Dashboard <ArrowRight className="ml-2" size={20} />
            </Button>
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full text-left animate-in fade-in slide-in-from-bottom-12 duration-1000 delay-500">
          <div className="bg-white/80 backdrop-blur-xl p-8 rounded-3xl border border-indigo-100 shadow-sm hover:shadow-xl hover:border-indigo-300 hover:bg-white transition-all duration-500 group">
            <div className="w-14 h-14 bg-indigo-100 text-indigo-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 group-hover:bg-indigo-600 group-hover:text-white transition-all duration-500">
              <Zap size={28} />
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-3">Instant AI Answers</h3>
            <p className="text-slate-600 font-medium leading-relaxed">Query the knowledge base in natural language and receive grounded, step-by-step resolution plans instantly.</p>
          </div>
          
          <div className="bg-white/80 backdrop-blur-xl p-8 rounded-3xl border border-purple-100 shadow-sm hover:shadow-xl hover:border-purple-300 hover:bg-white transition-all duration-500 group">
            <div className="w-14 h-14 bg-purple-100 text-purple-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 group-hover:bg-purple-600 group-hover:text-white transition-all duration-500">
              <ShieldCheck size={28} />
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-3">Proactive Monitoring</h3>
            <p className="text-slate-600 font-medium leading-relaxed">Analyze machine logs in real-time. Detect anomalies and receive warnings before communication failures halt your work.</p>
          </div>
          
          <div className="bg-white/80 backdrop-blur-xl p-8 rounded-3xl border border-fuchsia-100 shadow-sm hover:shadow-xl hover:border-fuchsia-300 hover:bg-white transition-all duration-500 group">
            <div className="w-14 h-14 bg-fuchsia-100 text-fuchsia-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 group-hover:bg-fuchsia-600 group-hover:text-white transition-all duration-500">
              <Database size={28} />
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-3">Enterprise Traceability</h3>
            <p className="text-slate-600 font-medium leading-relaxed">Every query and analysis is logged and fully traceable, ensuring compliance and operational confidence.</p>
          </div>
        </div>
      </main>

      <footer className="py-8 text-center text-slate-500 font-medium text-sm z-10 border-t border-indigo-100 bg-white/60 backdrop-blur-md">
        <p>&copy; {new Date().getFullYear()} KnowledgeBase AI System. Designed with precision.</p>
      </footer>
    </div>
  );
}
