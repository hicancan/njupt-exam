import { Exam } from '@/types';

interface ExamCardProps {
    exam: Exam;
    isSelected: boolean;
    onToggle: () => void;
}

const formatDisplayDate = (isoString?: string | null): string => {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', {
        month: 'short', day: 'numeric', weekday: 'short', hour: '2-digit', minute: '2-digit'
    });
};

export function ExamCard({ exam, isSelected, onToggle }: ExamCardProps) {
    const isValidTime = !!exam.start_timestamp;

    return (
        <label
            className={`
                block p-5 transition-colors cursor-pointer group hover:bg-[#f8f9fa] dark:hover:bg-[#303134]
                ${isSelected ? '' : 'opacity-70 grayscale-[0.5]'}
            `}
        >
            <div className="flex items-start gap-4">
                <div className="pt-1">
                    <input 
                        type="checkbox" 
                        checked={isSelected}
                        onChange={onToggle}
                        className="w-5 h-5 rounded border-[#dadce0] dark:border-[#5f6368] text-[var(--color-google-blue)] focus:ring-[var(--color-google-blue)] dark:bg-[#202124] cursor-pointer"
                    />
                </div>
                
                <div className="flex-1">
                    <div className="flex justify-between items-start mb-1 gap-3">
                        <h3 className={`text-[18px] font-normal leading-snug ${isSelected ? 'text-[var(--color-google-blue)] dark:text-[var(--color-google-blue-dark)] group-hover:underline' : 'text-[#202124] dark:text-[#e8eaed]'}`}>
                            {exam.course_name}
                        </h3>
                        {exam.campus && (
                            <span className="shrink-0 text-[12px] text-[#006621] dark:text-[#81c995] bg-[#e6f4ea] dark:bg-[#1e8e3e]/20 px-2.5 py-0.5 rounded">
                                {exam.campus}
                            </span>
                        )}
                    </div>
                    
                    <div className="text-[14px] text-[#4d5156] dark:text-[#bdc1c6] space-y-1.5 mt-2">
                        {isValidTime ? (
                            <div>
                                <span className="font-medium text-[#202124] dark:text-[#e8eaed]">{formatDisplayDate(exam.start_timestamp)}</span> 
                                <span className="mx-1">至</span> 
                                <span>{formatDisplayDate(exam.end_timestamp)}</span>
                                <span className="ml-2 text-[12px] px-1.5 py-0.5 bg-[#f1f3f4] dark:bg-[#3c4043] rounded text-[#5f6368] dark:text-[#9aa0a6]">
                                    {exam.duration_minutes} 分钟
                                </span>
                            </div>
                        ) : (
                            <div className="text-[#d93025] dark:text-[#f28b82]">
                                <span className="font-medium">时间待定:</span> {exam.raw_time || '未发布'}
                            </div>
                        )}
                        
                        <div>
                            <span className="text-[#70757a] dark:text-[#9aa0a6]">地点：</span>
                            <span className="font-medium text-[#202124] dark:text-[#e8eaed]">{exam.location || '待定'}</span>
                        </div>
                        
                        <div className="flex flex-wrap gap-x-4 gap-y-1 pt-1 text-[13px] text-[#70757a] dark:text-[#9aa0a6]">
                            <span><span className="mr-1">课程代码:</span>{exam.course_code || '无'}</span>
                            <span><span className="mr-1">教师:</span>{exam.teacher || '未知'}</span>
                            <span><span className="mr-1">人数:</span>{exam.count ?? '-'}</span>
                            {exam.notes && <span className="italic">注: {exam.notes}</span>}
                        </div>
                    </div>
                </div>
            </div>
        </label>
    );
}

