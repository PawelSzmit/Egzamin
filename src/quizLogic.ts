import type { AnswerKey, CategorySummary, ExamSession, ProgressState, Question, QuestionRecord } from "./types";

export const EXAM_SIZE = 75;

const DEFAULT_RECORD: QuestionRecord = {
  attempts: 0,
  correctAttempts: 0,
  wrongAttempts: 0,
  needsReview: false,
  bookmarked: false,
};

export const getRecord = (progress: ProgressState, id: number): QuestionRecord => ({
  ...DEFAULT_RECORD,
  ...progress.records[id],
});

export const isCorrectAnswer = (question: Question, answer: AnswerKey): boolean => question.correct === answer;

export const answerQuestion = (
  progress: ProgressState,
  question: Question,
  answer: AnswerKey,
): ProgressState => {
  const previous = getRecord(progress, question.id);
  const correct = isCorrectAnswer(question, answer);
  const nextRecord: QuestionRecord = {
    ...previous,
    attempts: previous.attempts + 1,
    correctAttempts: previous.correctAttempts + (correct ? 1 : 0),
    wrongAttempts: previous.wrongAttempts + (correct ? 0 : 1),
    lastAnswer: answer,
    lastCorrect: correct,
    lastSkipped: false,
    needsReview: correct ? false : true,
  };

  return {
    ...progress,
    records: {
      ...progress.records,
      [question.id]: nextRecord,
    },
  };
};

export const toggleBookmark = (progress: ProgressState, questionId: number): ProgressState => {
  const previous = getRecord(progress, questionId);
  return {
    ...progress,
    records: {
      ...progress.records,
      [questionId]: {
        ...previous,
        bookmarked: !previous.bookmarked,
      },
    },
  };
};

export const getReviewQuestions = (questions: Question[], progress: ProgressState): Question[] =>
  questions.filter((question) => {
    const record = getRecord(progress, question.id);
    return record.needsReview || record.bookmarked;
  });

export const getCategories = (questions: Question[], progress: ProgressState): CategorySummary[] => {
  const summaries = new Map<string, CategorySummary>();
  for (const question of questions) {
    const record = getRecord(progress, question.id);
    const summary =
      summaries.get(question.category) ??
      ({
        name: question.category,
        total: 0,
        answered: 0,
        correct: 0,
        review: 0,
      } satisfies CategorySummary);
    summary.total += 1;
    summary.answered += record.attempts > 0 ? 1 : 0;
    summary.correct += record.lastCorrect ? 1 : 0;
    summary.review += record.needsReview || record.bookmarked ? 1 : 0;
    summaries.set(question.category, summary);
  }
  return Array.from(summaries.values());
};

export const getOverallStats = (questions: Question[], progress: ProgressState) => {
  const answered = questions.filter((question) => getRecord(progress, question.id).attempts > 0).length;
  const correct = questions.filter((question) => getRecord(progress, question.id).lastCorrect).length;
  const review = getReviewQuestions(questions, progress).length;
  return {
    total: questions.length,
    answered,
    correct,
    wrong: answered - correct,
    review,
    percent: answered === 0 ? 0 : Math.round((correct / answered) * 100),
  };
};

export const filterQuestions = (
  questions: Question[],
  progress: ProgressState,
  mode: "learn" | "review" | "all",
  category: string,
): Question[] => {
  const base = mode === "review" ? getReviewQuestions(questions, progress) : questions;
  return category === "all" ? base : base.filter((question) => question.category === category);
};

export const createExam = (questions: Question[], size = EXAM_SIZE): ExamSession => {
  const pool = [...questions];
  for (let index = pool.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [pool[index], pool[swapIndex]] = [pool[swapIndex], pool[index]];
  }
  return {
    questionIds: pool.slice(0, Math.min(size, pool.length)).map((question) => question.id),
    answers: {},
    currentIndex: 0,
    completed: false,
    startedAt: new Date().toISOString(),
  };
};

export const answerExamQuestion = (
  progress: ProgressState,
  questionId: number,
  answer: AnswerKey,
): ProgressState => {
  if (!progress.exam || progress.exam.completed) return progress;
  return {
    ...progress,
    exam: {
      ...progress.exam,
      answers: {
        ...progress.exam.answers,
        [questionId]: answer,
      },
    },
  };
};

export const moveExam = (progress: ProgressState, nextIndex: number): ProgressState => {
  if (!progress.exam) return progress;
  const currentIndex = Math.max(0, Math.min(nextIndex, progress.exam.questionIds.length - 1));
  return {
    ...progress,
    exam: {
      ...progress.exam,
      currentIndex,
    },
  };
};

export const finishExam = (progress: ProgressState, questionsById: Map<number, Question>): ProgressState => {
  if (!progress.exam || progress.exam.completed) return progress;
  let nextProgress: ProgressState = {
    ...progress,
    exam: {
      ...progress.exam,
      completed: true,
      finishedAt: new Date().toISOString(),
    },
  };

  for (const questionId of progress.exam.questionIds) {
    const question = questionsById.get(questionId);
    const answer = progress.exam.answers[questionId];
    if (question && answer) {
      nextProgress = answerQuestion(nextProgress, question, answer);
    } else if (question) {
      const previous = getRecord(nextProgress, question.id);
      const previousWithoutLastAnswer = { ...previous };
      delete previousWithoutLastAnswer.lastAnswer;
      nextProgress = {
        ...nextProgress,
        records: {
          ...nextProgress.records,
          [question.id]: {
            ...previousWithoutLastAnswer,
            attempts: previous.attempts + 1,
            wrongAttempts: previous.wrongAttempts + 1,
            lastCorrect: false,
            lastSkipped: true,
            needsReview: true,
          },
        },
      };
    }
  }
  return nextProgress;
};

export const scoreExam = (exam: ExamSession, questionsById: Map<number, Question>) => {
  let correct = 0;
  for (const questionId of exam.questionIds) {
    const question = questionsById.get(questionId);
    const answer = exam.answers[questionId];
    if (question && answer && question.correct === answer) correct += 1;
  }
  return {
    correct,
    total: exam.questionIds.length,
    answered: Object.keys(exam.answers).length,
    percent: exam.questionIds.length === 0 ? 0 : Math.round((correct / exam.questionIds.length) * 100),
  };
};
