import { useMemo } from 'react';
import { Exam, SearchResult } from '@/types';

export const getClassSearchResult = (
    exams: Exam[],
    inputValue: string,
    manualSelection: string | null
): SearchResult => {
    const trimmed = inputValue.trim();
    if (trimmed.length < 2) {
        return { mode: 'EMPTY', classes: [], exams: [] };
    }

    if (manualSelection) {
        const selectedExams = exams.filter(exam => exam.class_name === manualSelection);
        if (selectedExams.length === 0) {
            return { mode: 'NOT_FOUND', classes: [], exams: [] };
        }
        return {
            mode: 'DETAIL',
            classes: [manualSelection],
            exams: selectedExams
        };
    }

    const term = trimmed.toUpperCase();
    const matchedExams = exams.filter(exam =>
        exam.class_name.toUpperCase().includes(term)
    );
    const uniqueClasses = Array.from(new Set(matchedExams.map(exam => exam.class_name))).sort();

    if (uniqueClasses.length === 0) {
        return { mode: 'NOT_FOUND', classes: [], exams: [] };
    }

    if (uniqueClasses.length === 1) {
        return { mode: 'DETAIL', classes: uniqueClasses, exams: matchedExams };
    }

    return { mode: 'LIST', classes: uniqueClasses, exams: [] };
};

export const useClassSearch = (
    exams: Exam[],
    inputValue: string,
    manualSelection: string | null
): SearchResult => {
    return useMemo(
        () => getClassSearchResult(exams, inputValue, manualSelection),
        [exams, inputValue, manualSelection]
    );
};
