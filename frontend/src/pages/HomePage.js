import React, { useEffect } from 'react';
import { authService } from '../services/authService';
import { Link } from 'react-router-dom';

const HomePage = () => {
  // const user = authService.getCurrentUser();

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const profile = await authService.fetchCurrentUser();
        if (mounted) console.info('HomePage fetched async profile:', profile);
      } catch (e) {
        if (mounted) console.error('HomePage: error fetching current user profile', e);
      }
    })();
    return () => { mounted = false; };
  }, []);

  const features = [
    {
      to: '/chat',
      emoji: '💬',
      title: 'Chat',
      description: 'Get instant AI-powered help with your coding questions and concepts.',
      color: 'primary',
    },
    {
      to: '/planner',
      emoji: '📋',
      title: 'Planner',
      description: 'Create personalized study plans tailored to your learning goals.',
      color: 'olive',
    },
    {
      to: '/quiz',
      emoji: '📝',
      title: 'Quiz',
      description: 'Test your knowledge with AI-generated quizzes and assessments.',
      color: 'sand',
    },
    {
      to: '/codequest',
      emoji: '🚀',
      title: 'CodeQuest',
      description: 'Practice coding with interactive challenges and real-time feedback.',
      color: 'purple',
    },
  ];

  const getColorClasses = (color) => {
    const colors = {
      primary: {
        bg: 'bg-[rgba(83,162,167,0.15)]',
        border: 'hover:border-[#53A2A7]',
        iconBg: 'bg-[rgba(83,162,167,0.2)]',
        text: 'text-[#53A2A7]',
      },
      olive: {
        bg: 'bg-[rgba(166,187,149,0.15)]',
        border: 'hover:border-[#A6BB95]',
        iconBg: 'bg-[rgba(166,187,149,0.2)]',
        text: 'text-[#7A9464]',
      },
      sand: {
        bg: 'bg-[rgba(213,191,133,0.15)]',
        border: 'hover:border-[#DECC9E]',
        iconBg: 'bg-[rgba(213,191,133,0.2)]',
        text: 'text-[#9C7F35]',
      },
      purple: {
        bg: 'bg-[rgba(139,92,246,0.15)]',
        border: 'hover:border-[#8B5CF6]',
        iconBg: 'bg-[rgba(139,92,246,0.2)]',
        text: 'text-[#7C3AED]',
      },
    };
    return colors[color] || colors.primary;
  };

  return (
    <div className="w-[90vw] h-[85vh]  flex flex-col overflow-hidden rounded-2xl shadow-xl bg-white">
      
      {/* Hero Section - Compact */}
      <header className="bg-gradient-to-br from-[#53A2A7] via-[#30838c] to-[#A6BB95] text-white px-4 py-4 text-center flex-shrink-0 rounded-t-2xl">
        {/* Title */}
          <div className="flex items-center justify-center gap-3 mb-3">
            <h3 className="text-2xl sm:text-3xl md:text-4xl font-bold">🎓 Your Local AI Tutoring Platform for Developers</h3>
          </div>
          
          {/* Separator */}
          <div className="flex items-center justify-center gap-4 my-4 max-w-md mx-auto">
            <div className="flex-1 h-px bg-gradient-to-r from-transparent via-white/40 to-transparent"></div>
            <span className="text-white/60 text-sm">✦</span>
            <div className="flex-1 h-px bg-gradient-to-r from-transparent via-white/40 to-transparent"></div>
          </div>

        <div className="max-w-4xl mx-auto">
          {/* Tech Stack Badges - Glassmorphism */}
          <div className="tech-stack-section mb-4">
            <h3 className="text-sm font-semibold text-white/80 mb-2">🛠️ Built with Modern Tools</h3>
            <div className="tech-stack-grid flex justify-center gap-2 sm:gap-3 flex-wrap">
              <div className="tech-stack-item inline-flex items-center gap-1.5 px-3 py-1.5 bg-transparent rounded-full backdrop-blur-xl border border-white/20 text-xs sm:text-sm font-medium shadow-[0_8px_32px_rgba(0,0,0,0.1)] hover:border-white/40 hover:shadow-[0_8px_32px_rgba(255,255,255,0.1)] transition-all duration-300">
                <span>🦙 LlamaIndex</span>
              </div>
              <div className="tech-stack-item inline-flex items-center gap-1.5 px-3 py-1.5 bg-transparent rounded-full backdrop-blur-xl border border-white/20 text-xs sm:text-sm font-medium shadow-[0_8px_32px_rgba(0,0,0,0.1)] hover:border-white/40 hover:shadow-[0_8px_32px_rgba(255,255,255,0.1)] transition-all duration-300">
                <span>🤖 Ollama</span>
              </div>
              <div className="tech-stack-item inline-flex items-center gap-1.5 px-3 py-1.5 bg-transparent rounded-full backdrop-blur-xl border border-white/20 text-xs sm:text-sm font-medium shadow-[0_8px_32px_rgba(0,0,0,0.1)] hover:border-white/40 hover:shadow-[0_8px_32px_rgba(255,255,255,0.1)] transition-all duration-300">
                <span>⚡ Flask</span>
              </div>
              <div className="tech-stack-item inline-flex items-center gap-1.5 px-3 py-1.5 bg-transparent rounded-full backdrop-blur-xl border border-white/20 text-xs sm:text-sm font-medium shadow-[0_8px_32px_rgba(0,0,0,0.1)] hover:border-white/40 hover:shadow-[0_8px_32px_rgba(255,255,255,0.1)] transition-all duration-300">
                <span>⚛️ React</span>
              </div>
              <div className="tech-stack-item inline-flex items-center gap-1.5 px-3 py-1.5 bg-transparent rounded-full backdrop-blur-xl border border-white/20 text-xs sm:text-sm font-medium shadow-[0_8px_32px_rgba(0,0,0,0.1)] hover:border-white/40 hover:shadow-[0_8px_32px_rgba(255,255,255,0.1)] transition-all duration-300">
                <span>🔒 Local First</span>
              </div>
            </div>
          </div>

          
        </div>
      </header>

      {/* Features Section - Grid fills remaining space */}
      <section className="flex-1 flex flex-col justify-center bg-[#F7F7F6]">
        <div className="max-w-5xl mx-auto w-full">
          <h2 className="text-lg sm:text-xl md:text-2xl font-bold text-center text-[#0F1724] mb-4 sm:mb-6">
            ✨ Explore Features
          </h2>
          
          {/* 4-column grid on large screens, 2 columns on medium, 1 on mobile */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-1 sm:gap-4">
            {features.map((feature) => {
              const colorClasses = getColorClasses(feature.color);
              return (
                <Link
                  key={feature.title}
                  to={feature.to}
                  className={`
                    group block p-4 sm:p-5 rounded-xl border border-[#E8E9EB] bg-white
                    transition-all duration-200 ease-out
                    hover:shadow-lg hover:-translate-y-1 ${colorClasses.border}
                  `}
                >
                  <div className={`
                    w-10 h-10 sm:w-12 sm:h-12 rounded-xl flex items-center justify-center mb-3
                    ${colorClasses.iconBg} transition-transform group-hover:scale-110
                  `}>
                    <span className="text-xl sm:text-2xl">{feature.emoji}</span>
                  </div>
                  <h3 className={`text-base sm:text-lg font-semibold mb-1 ${colorClasses.text}`}>
                    {feature.emoji} {feature.title}
                  </h3>
                  <p className="text-xs sm:text-sm text-[#6B7280] leading-relaxed">
                    {feature.description}
                  </p>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {/* Footer - Compact */}
      <footer className="bg-[#0F1724] text-white/80 py-3 px-4 text-center flex-shrink-0">
        <p className="text-xs sm:text-sm">🎯 TAI-tutor-ai • Local AI Tutoring for Developers</p>
      </footer>
    </div>
  );
};

export default HomePage;
