export type AnswerKey = "A" | "B" | "C";

export type Mode = "learn" | "exam" | "review" | "all";

export type Question = {
  id: number;
  category: string;
  question: string;
  options: Record<AnswerKey, string>;
  correct: AnswerKey;
  correct_answer: string;
  page: number;
  has_visual_reference: boolean;
  page_image: string | null;
  visual_image: string | null;
};

export type QuestionRecord = {
  attempts: number;
  correctAttempts: number;
  wrongAttempts: number;
  lastAnswer?: AnswerKey;
  lastCorrect?: boolean;
  lastSkipped?: boolean;
  needsReview: boolean;
  bookmarked: boolean;
};

export type ExamSession = {
  questionIds: number[];
  answers: Record<number, AnswerKey>;
  currentIndex: number;
  completed: boolean;
  startedAt: string;
  finishedAt?: string;
};

export type ProgressState = {
  version: 1;
  records: Record<number, QuestionRecord>;
  exam: ExamSession | null;
};

export type CategorySummary = {
  name: string;
  total: number;
  answered: number;
  correct: number;
  review: number;
};
