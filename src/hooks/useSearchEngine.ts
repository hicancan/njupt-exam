import { useMemo } from 'react';
import { SearchDocument, Exam } from '@/types';
import { buildExamDocuments, rankSearchDocuments, getLearningResources } from '@/utils/searchIndex';

export function useSearchEngine(
    noticeDocuments: SearchDocument[],
    allExams: Exam[],
    searchQuery: string
) {
    const examDocuments = useMemo(() => buildExamDocuments(allExams), [allExams]);
    const allDocuments = useMemo(() => [...noticeDocuments, ...examDocuments], [noticeDocuments, examDocuments]);
    
    const rankedResults = useMemo(
        () => rankSearchDocuments(allDocuments, searchQuery),
        [allDocuments, searchQuery]
    );
    
    const learningResources = useMemo(() => getLearningResources(searchQuery), [searchQuery]);

    return {
        rankedResults,
        learningResources
    };
}
