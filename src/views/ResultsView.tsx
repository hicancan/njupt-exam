import { useMemo, useState } from 'react';
import { CalendarDays, Download, ExternalLink, FileText, Filter, GraduationCap } from 'lucide-react';
import { ExamList } from '@/components/ExamList';
import { ExamDetail } from '@/components/ExamDetail';
import { ResultsSkeleton } from '@/components/ResultsSkeleton';
import { RankedSitegraphDocument, SearchResult, SitegraphFacet, SitegraphFullDocument } from '@/types';
import { formatSearchDate } from '@/utils/searchIndex';

type FacetFilter = SitegraphFacet | 'all';

const FACET_LABELS: Record<FacetFilter, string> = {
    all: '全部',
    notice_article: '通知文章',
    policy: '政策制度',
    workflow: '办事流程',
    download: '下载资源',
    system: '系统入口',
    exam: '考试相关',
    news: '教务快讯',
    external: '外部链接'
};

const isExternalUrl = (url: string): boolean => /^https?:\/\//.test(url);

interface SearchResultCardProps {
    document: RankedSitegraphDocument | SitegraphFullDocument;
    onOpenClass: (className: string) => void;
}

function SearchResultCard({ document, onOpenClass }: SearchResultCardProps) {
    const isExamClass = document.record_type === 'utility' && document.title.includes('考试信息查询');
    const recallReason = (document as Partial<RankedSitegraphDocument>).score_reason || '';
    const Wrapper = isExamClass ? 'button' : 'a';
    const wrapperProps = isExamClass
        ? {
            type: 'button' as const,
            onClick: () => onOpenClass(''),
        }
        : {
            href: document.url,
            target: isExternalUrl(document.url) ? '_blank' : undefined,
            rel: isExternalUrl(document.url) ? 'noopener noreferrer' : undefined,
        };

    return (
        <Wrapper {...wrapperProps} className="block w-full text-left py-4 group border-b border-[#e8eaed] dark:border-[#3c4043] last:border-b-0">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-[#70757a] dark:text-[#9aa0a6]">
                <span className="font-medium text-[#3c4043] dark:text-[#bdc1c6]">{FACET_LABELS[document.facet]}</span>
                <span>{document.source}</span>
                <span>›</span>
                <span>{document.nav_path_text || document.section}</span>
                {document.published_at ? (
                    <>
                        <span>›</span>
                        <span>{formatSearchDate(document.published_at)}</span>
                    </>
                ) : null}
            </div>

            <h3 className="mt-1 text-[20px] leading-snug font-medium text-[#1a0dab] dark:text-[#8ab4f8] group-hover:underline break-words">
                {document.title}
            </h3>

            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-[#0b8043] dark:text-[#81c995]">
                <span className="truncate max-w-full">{document.url}</span>
                {document.record_type === 'external' ? (
                    <span className="inline-flex items-center gap-1 text-[#5f6368] dark:text-[#9aa0a6]">
                        <ExternalLink size={13} />
                        只记录入口
                    </span>
                ) : null}
                {document.record_type === 'attachment' ? (
                    <span className="inline-flex items-center gap-1 text-[#5f6368] dark:text-[#9aa0a6]">
                        <Download size={13} />
                        元数据附件
                    </span>
                ) : null}
            </div>

            <p className="mt-2 text-[14px] text-[#4d5156] dark:text-[#bdc1c6] line-clamp-2 break-words">
                {document.summary || document.content}
            </p>

            <div className="mt-2 flex flex-wrap gap-2 text-[12px] text-[#5f6368] dark:text-[#9aa0a6]">
                <span className="inline-flex items-center gap-1 rounded bg-[#f1f3f4] dark:bg-[#303134] px-2 py-1">
                    <Filter size={12} />
                    {document.section}
                </span>
                {document.attachment_count > 0 ? (
                    <span className="inline-flex items-center gap-1 rounded bg-[#e8f0fe] dark:bg-[#263850] px-2 py-1 text-[#1967d2] dark:text-[#8ab4f8]">
                        <FileText size={12} />
                        附件 {document.attachment_count}
                    </span>
                ) : null}
                <span className="rounded bg-[#f1f3f4] dark:bg-[#303134] px-2 py-1">
                    provenance: {document.provenance.site_id}
                    {document.provenance.section_id ? ` / ${document.provenance.section_id}` : ''}
                    {document.provenance.outcome ? ` / ${document.provenance.outcome}` : ''}
                </span>
            </div>

            {document.attachments.length > 0 ? (
                <div className="mt-2 flex flex-wrap gap-1.5">
                    {document.attachments.slice(0, 4).map(attachment => (
                        <span
                            key={`${attachment.attachment_id}-${attachment.url}`}
                            className="inline-flex items-center gap-1 max-w-full h-6 px-2 rounded bg-[#f8fafd] dark:bg-[#2d2f33] text-[12px] text-[#3c4043] dark:text-[#d2d5da]"
                        >
                            <FileText size={12} className="shrink-0" />
                            <span className="truncate">{attachment.name}</span>
                            {attachment.extension ? <span className="uppercase text-[#70757a] dark:text-[#9aa0a6]">{attachment.extension}</span> : null}
                        </span>
                    ))}
                </div>
            ) : null}

            {recallReason ? (
                <div className="mt-1 text-[12px] text-[#70757a] dark:text-[#9aa0a6]">
                    召回依据：{recallReason}
                </div>
            ) : null}
        </Wrapper>
    );
}

interface ResultsViewProps {
    isLoading?: boolean;
    query: string;
    results: RankedSitegraphDocument[];
    resources: SitegraphFullDocument[];
    classMode: SearchResult;
    selectedIds: Set<string>;
    reminders: number[];
    onOpenClass: (className: string) => void;
    onToggleSelection: (id: string) => void;
    onRemindersChange: (reminders: number[]) => void;
    sourceUrl: string | null;
    sourceTitle: string | null;
    generatedAt: string | null;
    totalRecords: number | null;
}

export function ResultsView({
    isLoading,
    query,
    results,
    resources,
    classMode,
    selectedIds,
    reminders,
    onOpenClass,
    onToggleSelection,
    onRemindersChange,
    sourceUrl,
    sourceTitle,
    generatedAt,
    totalRecords
}: ResultsViewProps) {
    const trimmedQuery = query.trim();
    const [activeFacet, setActiveFacet] = useState<FacetFilter>('all');
    const [visibleState, setVisibleState] = useState({ key: '', count: 20 });
    const availableFacets = useMemo(() => {
        const facets = Array.from(new Set(results.map(document => document.facet)));
        const preferred: SitegraphFacet[] = ['notice_article', 'policy', 'workflow', 'download', 'system', 'exam', 'news', 'external'];
        return preferred.filter(facet => facets.includes(facet));
    }, [results]);
    const filteredResults = useMemo(() => {
        return results.filter(document => activeFacet === 'all' || document.facet === activeFacet);
    }, [activeFacet, results]);
    const visibleKey = `${trimmedQuery}\u0000${activeFacet}`;
    const visibleCount = visibleState.key === visibleKey ? visibleState.count : 20;
    const visibleResults = filteredResults.slice(0, visibleCount);

    const hasClassDetail = classMode.mode === 'DETAIL' && classMode.exams.length > 0;
    const showSearchResultsSection = !(hasClassDetail && filteredResults.length === 0);

    return (
        <main className="max-w-6xl w-full mx-auto px-4 py-6">
            {isLoading ? (
                <ResultsSkeleton />
            ) : (
            <div className="w-full">
                {classMode.mode === 'LIST' ? (
                    <section className="mt-6">
                        <ExamList classes={classMode.classes} onClassClick={onOpenClass} />
                    </section>
                ) : null}

                {classMode.mode === 'DETAIL' ? (
                    <section className="mt-6 border-b border-[#dadce0] dark:border-[#3c4043] pb-8">
                        <ExamDetail
                            className={classMode.classes[0] || ''}
                            exams={classMode.exams}
                            selectedIds={selectedIds}
                            onToggleSelection={onToggleSelection}
                            reminders={reminders}
                            onRemindersChange={onRemindersChange}
                            sourceUrl={sourceUrl}
                            sourceTitle={sourceTitle}
                            generatedAt={generatedAt}
                            totalRecords={totalRecords}
                        />
                    </section>
                ) : null}

                {resources.length > 0 ? (
                    <section className="mt-8">
                        <div className="flex items-center gap-2 mb-3">
                            <GraduationCap className="w-5 h-5 text-[#1a73e8]" aria-hidden="true" />
                            <h2 className="text-lg font-semibold text-[#202124] dark:text-[#e8eaed]">相关学习资源</h2>
                        </div>
                        <div className="grid md:grid-cols-2 gap-3">
                            {resources.map(resource => (
                                <SearchResultCard key={resource.id} document={resource} onOpenClass={onOpenClass} />
                            ))}
                        </div>
                    </section>
                ) : null}

                {trimmedQuery === '考试安排' && classMode.mode === 'NOT_FOUND' ? (
                    <section className="mt-8">
                        <div className="border border-[#dadce0] dark:border-[#3c4043] rounded-xl bg-[#f8fafc] dark:bg-[#2d2e30] p-8 text-center max-w-[692px] mx-auto shadow-sm">
                            <div className="mx-auto w-16 h-16 bg-[#e8f0fe] dark:bg-[#3b4043] rounded-full flex items-center justify-center mb-4">
                                <CalendarDays className="w-8 h-8 text-[#1a73e8] dark:text-[#8ab4f8]" aria-hidden="true" />
                            </div>
                            <h2 className="text-2xl font-semibold text-[#202124] dark:text-[#e8eaed] mb-2">考试日程助手已就绪</h2>
                            <p className="text-[15px] text-[#4d5156] dark:text-[#bdc1c6] mb-6">
                                请在顶部搜索框输入完整班级号，例如 <span className="font-mono bg-[#e8eaed] dark:bg-[#3c4043] px-1.5 py-0.5 rounded text-[#202124] dark:text-[#e8eaed]">B250403</span>。
                            </p>
                        </div>
                    </section>
                ) : showSearchResultsSection ? (
                    <section className="mt-8">
                        <div className="mb-4">
                            <h2 className="text-xl font-semibold text-[#202124] dark:text-[#e8eaed]">JWC sitegraph 搜索结果</h2>
                            <div className="flex gap-4 mt-2 mb-1 border-b border-[#dadce0] dark:border-[#3c4043] overflow-x-auto whitespace-nowrap">
                                <button onClick={() => setActiveFacet('all')} className={`shrink-0 pb-2 text-sm font-medium ${activeFacet === 'all' ? 'text-[#1a73e8] border-b-2 border-[#1a73e8]' : 'text-[#5f6368] hover:text-[#202124] dark:text-[#9aa0a6] dark:hover:text-[#e8eaed]'}`}>全部</button>
                                {availableFacets.map(facet => (
                                    <button
                                        key={facet}
                                        onClick={() => setActiveFacet(facet)}
                                        className={`shrink-0 pb-2 text-sm font-medium ${activeFacet === facet ? 'text-[#1a73e8] border-b-2 border-[#1a73e8]' : 'text-[#5f6368] hover:text-[#202124] dark:text-[#9aa0a6] dark:hover:text-[#e8eaed]'}`}
                                    >
                                        {FACET_LABELS[facet]}
                                    </button>
                                ))}
                            </div>
                            <p className="mt-1 text-sm text-[#70757a] dark:text-[#9aa0a6]">
                                {trimmedQuery.length >= 2
                                    ? `找到 ${filteredResults.length} 条结果。全文 shard 按当前候选按需加载。`
                                    : '输入至少两个字符搜索本科生院 / 教务处站点图。'}
                            </p>
                        </div>

                        {visibleResults.length > 0 ? (
                            <div>
                                {visibleResults.map(document => (
                                    <SearchResultCard key={document.id} document={document} onOpenClass={onOpenClass} />
                                ))}
                                {visibleCount < filteredResults.length && (
                                    <div className="pt-4 pb-2 text-center">
                                        <button
                                            onClick={() => setVisibleState({ key: visibleKey, count: visibleCount + 20 })}
                                            className="px-6 py-2 rounded-full border border-[#dadce0] dark:border-[#3c4043] bg-white dark:bg-[#202124] text-sm font-medium text-[#1a73e8] hover:bg-[#f8f9fa] dark:hover:bg-[#303134] transition-colors"
                                        >
                                            加载更多
                                        </button>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="border border-[#dadce0] dark:border-[#3c4043] rounded-md bg-white dark:bg-[#202124] p-6 text-[#4d5156] dark:text-[#bdc1c6] max-w-[692px]">
                                <p>没有找到匹配的 JWC sitegraph 记录。</p>
                                <p className="mt-2 text-sm">可以尝试“校历”“期末考试”“学生相关文件及表格”“教务管理系统”这类官网栏目或标题关键词。</p>
                            </div>
                        )}
                    </section>
                ) : null}
            </div>
            )}
        </main>
    );
}
