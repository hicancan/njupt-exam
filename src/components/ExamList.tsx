import { APP_CONFIG } from '@/constants';

interface ExamListProps {
    classes: string[];
    onClassClick: (cls: string) => void;
}

export function ExamList({ classes, onClassClick }: ExamListProps) {
    return (
        <div className="fade-in max-w-[652px]">
            <div className="mb-6 px-1">
                <span className="text-[#70757a] dark:text-[#9aa0a6] text-[14px]">
                    找到约 {classes.length} 条相关班级结果
                </span>
            </div>
            <div className="flex flex-col gap-8">
                {classes.slice(0, APP_CONFIG.MAX_CLASS_DISPLAY_COUNT).map(cls => (
                    <div key={cls} className="flex flex-col items-start w-full">
                        <button
                            type="button"
                            onClick={() => onClassClick(cls)}
                            className="group text-left"
                        >
                            <div className="flex items-center gap-2 mb-1.5">
                                <div className="bg-[#f1f3f4] dark:bg-[#303134] rounded-full p-1">
                                    <svg className="w-3 h-3 text-[#5f6368] dark:text-[#bdc1c6]" fill="currentColor" viewBox="0 0 20 20">
                                        <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                                        <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                                    </svg>
                                </div>
                                <span className="text-[14px] text-[#202124] dark:text-[#dadce0] font-normal truncate">
                                    {APP_CONFIG.DOMAIN} <span className="text-[#5f6368] dark:text-[#9aa0a6]">› class › {cls}</span>
                                </span>
                            </div>
                            <h3 className="text-xl text-[var(--color-google-blue)] dark:text-[var(--color-google-blue-dark)] group-hover:underline font-normal mb-1">
                                {cls} - NJUPT 考试日程
                            </h3>
                        </button>
                        <p className="text-[14px] text-[var(--color-google-grey)] dark:text-[var(--color-google-grey-dark)] max-w-[600px] leading-[1.58]">
                            点击查看南京邮电大学 <strong>{cls}</strong> 班级的最新期末考试安排。包含考试时间、考试地点、监考教师等详细信息，支持一键导出至日历软件进行提醒。
                        </p>
                    </div>
                ))}
            </div>
            {classes.length > APP_CONFIG.MAX_CLASS_DISPLAY_COUNT && (
                <p className="text-center text-sm text-[var(--color-google-grey)] dark:text-[var(--color-google-grey-dark)] mt-10 pb-10">
                    为提供最相关的结果，我们省略了部分相似的条目，请继续输入以精确查找。
                </p>
            )}
        </div>
    );
}
