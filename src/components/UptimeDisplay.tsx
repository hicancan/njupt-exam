import { useState, useEffect } from 'react';
import { APP_CONFIG } from '@/constants';

interface UptimeDisplayProps {
    startTime?: string;
    sourceUrl?: string | null;
    sourceTitle?: string | null;
}

export function UptimeDisplay({
    startTime = APP_CONFIG.START_TIME_DEFAULT,
    sourceUrl,
    sourceTitle
}: UptimeDisplayProps) {
    const [uptime, setUptime] = useState<string>('');

    useEffect(() => {
        const start = new Date(startTime);
        const updateTimer = () => {
            const diff = new Date().getTime() - start.getTime();
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);
            setUptime(`${days}天 ${hours}小时 ${minutes}分 ${seconds}秒`);
        };
        const timer = setInterval(updateTimer, 1000);
        updateTimer();
        return () => clearInterval(timer);
    }, [startTime]);

    return (
        <div className="flex flex-col lg:flex-row items-start lg:items-center gap-y-3 lg:gap-x-6 w-full lg:w-auto">
            {sourceUrl && (
                <div className="flex flex-col sm:flex-row sm:items-center gap-1 max-w-full overflow-hidden">
                    <span className="whitespace-nowrap flex-shrink-0">当前数据来源:</span>
                    <a
                        href={sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[var(--color-google-blue)] dark:text-[var(--color-google-blue-dark)] hover:underline font-medium truncate block"
                        title={sourceTitle || '点击查看教务处原始通知'}
                    >
                        {sourceTitle || '教务处通知'}
                    </a>
                </div>
            )}

            <span className="hidden lg:inline text-[#dadce0] dark:text-[#3c4043]">|</span>

            <div>
                数据同步 · 每6小时
            </div>

            <span className="hidden lg:inline text-[#dadce0] dark:text-[#3c4043]">|</span>

            <div className="flex flex-wrap items-center gap-3">
                <span className="whitespace-nowrap">
                    已运行 <span className="font-mono text-[var(--color-google-blue)] dark:text-[var(--color-google-blue-dark)]">{uptime}</span>
                </span>
                <span className="hidden lg:inline text-[#dadce0] dark:text-[#3c4043]">|</span>
                <img
                    src={APP_CONFIG.VISITOR_BADGE_URL}
                    className="h-4 w-auto opacity-80 hover:opacity-100 transition-opacity grayscale hover:grayscale-0"
                    alt="visitor count"
                    loading="lazy"
                />
            </div>
        </div>
    );
}
