import { useState } from 'react';
import { Exam } from '@/types';
import { generateICSContent } from '@/utils/icsGenerator';
import { ExamCard } from './ExamCard';
import { ReminderSettings } from './ReminderSettings';


interface ExamDetailProps {
    className: string;
    exams: Exam[];
    selectedIds: Set<string>;
    onToggleSelection: (id: string) => void;
    reminders: number[];
    onRemindersChange: (reminders: number[]) => void;
    sourceUrl?: string | null;
    sourceTitle?: string | null;
}

export function ExamDetail({
    className,
    exams,
    selectedIds,
    onToggleSelection,
    reminders,
    onRemindersChange,
    sourceUrl,
    sourceTitle
}: ExamDetailProps) {
    const [copyState, setCopyState] = useState<boolean>(false);

    const copyShareLink = () => {
        const url = window.location.href;
        navigator.clipboard.writeText(url).then(() => {
            setCopyState(true);
            setTimeout(() => setCopyState(false), 2000);
        });
    };

    const downloadICS = () => {
        const selectedExams = exams.filter(e => selectedIds.has(e.id));
        const validExams = selectedExams.filter(e => e.start_timestamp);

        if (validExams.length === 0) {
            alert('请至少勾选一门包含有效时间的考试');
            return;
        }

        try {
            const content = generateICSContent(validExams, className, reminders);
            const blob = new Blob([content], { type: 'text/calendar;charset=utf-8' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `NJUPT_Exams_${className}.ics`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (err) {
            console.error('ICS generation failed:', err);
            alert('日历文件生成失败，请稍后重试或联系开发者');
        }
    };

    return (
        <div className="fade-in w-full pb-10">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-6">
                <div>
                    <h2 className="text-[28px] font-normal text-[#202124] dark:text-[#e8eaed] leading-tight mb-2">
                        {className} 期末考试安排
                    </h2>
                    <div className="flex items-center gap-3 text-[14px] text-[#70757a] dark:text-[#9aa0a6]">
                        <span>已选 {selectedIds.size} / {exams.length} 门考试</span>
                        <span>•</span>
                        <button
                            onClick={copyShareLink}
                            type="button"
                            className={`flex items-center gap-1 hover:underline transition-colors ${copyState ? 'text-[#34A853]' : 'text-[var(--color-google-blue)] dark:text-[var(--color-google-blue-dark)]'}`}
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"></path>
                            </svg>
                            {copyState ? '链接已复制' : '分享此页面'}
                        </button>
                    </div>
                </div>
                <button
                    onClick={downloadICS}
                    disabled={selectedIds.size === 0}
                    className={`
                        inline-flex items-center justify-center gap-2 px-6 py-2 rounded-full text-[14px] font-medium transition-all shrink-0
                        ${selectedIds.size > 0
                            ? 'bg-[var(--color-google-blue)] hover:bg-[#3b78e7] text-white shadow-sm'
                            : 'bg-[#f8f9fa] dark:bg-[#303134] text-[#9aa0a6] cursor-not-allowed border border-[#dadce0] dark:border-[#3c4043]'}
                    `}
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                    </svg>
                    导出日历 (.ics)
                </button>
            </div>

            <div className="mb-6 bg-[#f8f9fa] dark:bg-[#202124] border border-[#dadce0] dark:border-[#3c4043] rounded-lg p-4">
                <ReminderSettings selected={reminders} onChange={onRemindersChange} />
            </div>

            <div className="space-y-0 border border-[#dadce0] dark:border-[#3c4043] rounded-lg overflow-hidden bg-white dark:bg-[#202124]">
                {exams.map((exam, idx) => (
                    <div key={exam.id || idx} className={idx !== exams.length - 1 ? "border-b border-[#dadce0] dark:border-[#3c4043]" : ""}>
                        <ExamCard
                            exam={exam}
                            isSelected={selectedIds.has(exam.id)}
                            onToggle={() => onToggleSelection(exam.id)}
                        />
                    </div>
                ))}
            </div>

            <div className="mt-6 text-[12px] text-[#70757a] dark:text-[#9aa0a6] flex items-start gap-2">
                <svg className="w-4 h-4 shrink-0 mt-0.5 text-[#fbbc05]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                <p className="leading-relaxed">
                    免责声明：本页考试信息提取自教务处发布的
                    {sourceUrl ? (
                        <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="text-[var(--color-google-blue)] dark:text-[var(--color-google-blue-dark)] hover:underline mx-1">
                            《{sourceTitle || '最新通知'}》
                        </a>
                    ) : (
                        <span> 教务处通知 </span>
                    )}
                    ，由程序每 6 小时自动同步并解析生成。虽有严格数据校验，但无法绝对保证 100% 无误，开发者不对因依赖本工具而导致的任何考试延误或缺考等后果承担责任。
                </p>
            </div>
        </div>
    );
}
