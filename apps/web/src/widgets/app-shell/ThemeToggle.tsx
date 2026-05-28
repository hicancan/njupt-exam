import { useState, useEffect } from 'react';
import { Moon, Sun } from 'lucide-react';

export function ThemeToggle() {
    const [isDark, setIsDark] = useState<boolean>(() => {
        // Initialize state from local storage or system preference
        if (typeof window === 'undefined') return false;
        const saved = localStorage.getItem('theme');
        const preferDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        return saved === 'dark' || (!saved && preferDark);
    });

    useEffect(() => {
        // Sync state to DOM and local storage
        if (isDark) {
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
        }
    }, [isDark]);

    const toggleTheme = () => {
        setIsDark(prev => !prev);
    };

    return (
        <button
            type="button"
            onClick={toggleTheme}
            className="p-2 rounded-full transition-colors bg-transparent text-[#5f6368] dark:text-[#bdc1c6] hover:bg-[#f1f3f4] dark:hover:bg-[#303134]"
            title={isDark ? "切换到亮色模式" : "切换到暗黑模式"}
        >
            {isDark ? (
                <Sun className="w-5 h-5" aria-hidden="true" />
            ) : (
                <Moon className="w-5 h-5" aria-hidden="true" />
            )}
        </button>
    );
}

