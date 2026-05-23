import { useMemo } from 'react';
import { SearchDocument, Exam, SearchCategory } from '@/types';
import { buildExamDocuments, rankSearchDocuments, getLearningResources } from '@/utils/searchIndex';

export function useSearchEngine(
    noticeDocuments: SearchDocument[],
    allExams: Exam[],
    searchQuery: string,
    selectedCategory: SearchCategory | '全部'
) {
    const examDocuments = useMemo(() => buildExamDocuments(allExams), [allExams]);
    const allDocuments = useMemo(() => [...noticeDocuments, ...examDocuments], [noticeDocuments, examDocuments]);
    
    const rankedResults = useMemo(
        () => rankSearchDocuments(allDocuments, searchQuery, selectedCategory),
        [allDocuments, searchQuery, selectedCategory]
    );
    
    const learningResources = useMemo(() => getLearningResources(searchQuery), [searchQuery]);

    return {
        rankedResults,
        learningResources
    };
}
