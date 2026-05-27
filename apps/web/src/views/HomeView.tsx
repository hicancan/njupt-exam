import { CalendarDays, Download, FileText, Search, Shuffle, Trophy, Waypoints } from 'lucide-react';
import { SearchInput } from '@/components/SearchInput';
import { ThemeToggle } from '@/components/ThemeToggle';

const QUICK_SEARCHES: { label: string; query: string; icon: typeof Search }[] = [
    { label: '考试安排', query: '考试安排', icon: CalendarDays },
    { label: '校历', query: '校历', icon: CalendarDays },
    { label: '转专业', query: '转专业', icon: Shuffle },
    { label: '学生表格', query: '学生相关文件及表格', icon: Download },
    { label: '教务系统', query: '教务管理系统', icon: Waypoints },
    { label: '大创', query: '大创', icon: Trophy },
    { label: '规章制度', query: '规章制度', icon: FileText },
];

interface HomeViewProps {
    inputValue: string;
    onQuickSearch: (query: string) => void;
    onInputChange: (value: string) => void;
    onSubmit: (value: string) => void;
}

export function HomeView({
    inputValue,
    onQuickSearch,
    onInputChange,
    onSubmit
}: HomeViewProps) {
    return (
        <main className="flex-1 px-4">
            <div className="max-w-6xl mx-auto pt-5 flex justify-end">
                <ThemeToggle />
            </div>
            <section className="max-w-[680px] mx-auto min-h-[calc(100vh-176px)] flex flex-col items-center justify-center pb-20">
                <img src="/assets/logo.png" alt="" className="w-16 h-16 rounded-2xl" />
                <h1 className="mt-5 text-5xl sm:text-6xl font-normal text-[#202124] dark:text-[#e8eaed] leading-tight">njupt-search</h1>

                <div className="mt-8 w-full">
                    <SearchInput value={inputValue} onChange={onInputChange} onSubmit={onSubmit} />
                </div>

                <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
                    {QUICK_SEARCHES.map(item => {
                        const Icon = item.icon;
                        return (
                            <button
                                key={item.label}
                                type="button"
                                onClick={() => onQuickSearch(item.query)}
                                className="inline-flex items-center gap-2 h-10 px-4 rounded-full border border-[#dadce0] dark:border-[#3c4043] bg-white dark:bg-[#202124] text-sm text-[#3c4043] dark:text-[#e8eaed] hover:border-[#8ab4f8] transition-colors"
                            >
                                <Icon className="w-4 h-4" aria-hidden="true" />
                                {item.label}
                            </button>
                        );
                    })}
                </div>
            </section>
        </main>
    );
}
