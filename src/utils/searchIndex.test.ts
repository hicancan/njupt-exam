import { describe, expect, it } from 'vitest';
import { Exam, SearchDocument } from '@/types';
import { buildExamDocuments, getLearningResources, rankSearchDocuments } from './searchIndex';

const baseNotice: SearchDocument = {
    id: 'notice-1',
    kind: 'notice',
    source_id: 'xsc',
    channel_id: 'xsc_notice',
    channel: '学生工作通知',
    title: '关于2026年春季学期奖学金评选工作的通知',
    url: 'https://xsc.njupt.edu.cn/notice',
    source: '学生工作处',
    source_domain: 'xsc.njupt.edu.cn',
    source_type: 'central_admin',
    category: '奖助',
    domain: 'scholarship',
    intent: 'publicity',
    lifecycle: 'active',
    evidence: ['奖学金评选工作的通知'],
    confidence: 0.9,
    sub_category: null,
    deadline: null,
    action_required: false,
    action_type: null,
    action_summary: null,
    required_materials: [],
    sensitive: false,
    sensitive_types: [],
    review_required: false,
    risk_flags: [],
    audience: ['本科生'],
    published_at: '2026-05-20',
    content: '奖学金 评优 公示 学生资助',
    summary: '奖学金评选通知',
    attachments: [],
    student_score: 0.95,
    freshness_score: 1,
    importance_score: 0.9,
    source_weight: 0.96,
    tags: ['奖学金', '评优', '公示'],
    hash: 'notice-1',
    canonical: {
        doc_id: 'notice-1',
        canonical_url: 'https://xsc.njupt.edu.cn/notice',
        content_hash: 'notice-1',
        dedupe_key: 'notice-1',
    },
    rule_guard: {
        restricted: false,
        sensitive: false,
        low_evidence: false,
        duplicate: false,
        expired: false,
        evergreen: false,
        risk_flags: [],
        allow_llm: true,
        allow_full_text_display: true,
        review_required: false,
    },
    task_frames: [{
        task_id: 'task-notice-1',
        doc_id: 'notice-1',
        source_mode: 'llm',
        task_type: 'application',
        who: { audience: ['本科生'], college: [], grade: [], major: [], class_name: [] },
        what: '奖学金评选',
        action: { required: false, verb: '查看', object: '评选通知', summary: '查看奖学金评选通知。' },
        time: { published_at: '2026-05-20', deadline: null, lifecycle: 'active', urgency_days: null },
        materials: [],
        location: { place: null, online: null, contact: null },
        source: { source_id: 'xsc', channel_id: 'xsc_notice', authority: 0.96, official: true },
        evidence: [{ field: 'action', text: '奖学金评选工作的通知' }],
        risk: { sensitive: false, restricted: false, low_evidence: false, review_required: false },
        confidence: 0.9,
    }],
};

describe('rankSearchDocuments', () => {
    it('ranks student-facing notices by direct keyword match', () => {
        const lowPriority: SearchDocument = {
            ...baseNotice,
            id: 'notice-2',
            title: '党委理论学习中心组学习通知',
            category: '公告',
            content: '党委理论学习 会议',
            student_score: 0.2,
            tags: ['公告'],
            hash: 'notice-2',
        };

        const results = rankSearchDocuments([lowPriority, baseNotice], '奖学金 公示');

        expect(results[0]?.id).toBe('notice-1');
        expect(results[0]?.score).toBeGreaterThan(results[1]?.score || 0);
    });

    it('converts exam records into searchable exam documents', () => {
        const exam: Exam = {
            id: 'sheet-2',
            class_name: 'B250403',
            course_name: '数据结构',
            location: '教2-201',
            start_timestamp: '2026-06-29T08:00:00+08:00',
            end_timestamp: '2026-06-29T09:50:00+08:00',
            duration_minutes: 110,
            raw_time: '2026年06月29日(08:00-09:50)',
        };

        const [document] = buildExamDocuments([exam]);

        expect(document?.kind).toBe('exam');
        expect(document?.category).toBe('考试');
        expect(document?.class_name).toBe('B250403');
        expect(rankSearchDocuments([document as SearchDocument], 'B250403')[0]?.id).toBe('exam-sheet-2');
    });

    it('does not use category filtering for result inclusion', () => {
        const document: SearchDocument = {
            ...baseNotice,
            id: 'notice-misaligned-category',
            category: '公告',
            domain: 'scholarship',
            intent: 'publicity',
            title: '2026年奖学金名单公示',
            content: '奖学金 公示 名单',
            tags: ['奖学金', '公示'],
            hash: 'notice-misaligned-category',
        };

        expect(rankSearchDocuments([document], '奖学金 公示')[0]?.id).toBe('notice-misaligned-category');
    });

    it('only shows learning resources for course or exam intent', () => {
        expect(getLearningResources('数据结构 复习').length).toBeGreaterThan(0);
        expect(getLearningResources('后勤 停电')).toHaveLength(0);
    });
});
