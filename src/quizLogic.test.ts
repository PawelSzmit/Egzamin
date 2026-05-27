import { existsSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import questions from "./data/questions.json";
import { emptyProgress } from "./storage";
import type { AnswerKey, ProgressState, Question } from "./types";
import {
  answerQuestion,
  createExam,
  finishExam,
  getOverallStats,
  getReviewQuestions,
  scoreExam,
} from "./quizLogic";

const typedQuestions = questions as Question[];

describe("question data", () => {
  it("contains the complete official 301-question set", () => {
    expect(typedQuestions).toHaveLength(301);
    expect(typedQuestions.map((question) => question.id)).toEqual(
      Array.from({ length: 301 }, (_, index) => index + 1),
    );
  });

  it("has three answers and a matching correct answer for every question", () => {
    for (const question of typedQuestions) {
      expect(Object.keys(question.options).sort()).toEqual(["A", "B", "C"]);
      expect(["A", "B", "C"]).toContain(question.correct);
      expect(question.correct_answer).toBe(question.options[question.correct]);
      expect(question.category.length).toBeGreaterThan(0);
      expect(question.question.length).toBeGreaterThan(0);
    }
  });

  it("marks visual questions with a page image", () => {
    const first = typedQuestions[0];
    expect(first.has_visual_reference).toBe(true);
    expect(first.page_image).toBe("exam-pages/page-01.jpg");
    expect(first.visual_image).toBe("question-images/question-001.jpg");
  });

  it("has generated crop files for every visual question", () => {
    const visualQuestions = typedQuestions.filter((question) => question.has_visual_reference);
    expect(visualQuestions).toHaveLength(68);
    expect(visualQuestions.every((question) => question.visual_image)).toBe(true);
    expect(typedQuestions.find((question) => question.id === 146)?.visual_image).toBe("question-images/question-146.jpg");
    expect(typedQuestions.find((question) => question.id === 147)?.visual_image).toBe("question-images/question-147.jpg");

    for (const question of visualQuestions) {
      expect(existsSync(`public/${question.visual_image}`)).toBe(true);
    }
  });
});

describe("quiz progress", () => {
  it("sends wrong answers to review and removes them after a correct retry", () => {
    const question = typedQuestions[0];
    const wrongAnswer = question.correct === "A" ? "B" : "A";
    const afterWrong = answerQuestion(emptyProgress(), question, wrongAnswer);
    expect(getReviewQuestions([question], afterWrong)).toHaveLength(1);

    const afterCorrect = answerQuestion(afterWrong, question, question.correct);
    expect(getReviewQuestions([question], afterCorrect)).toHaveLength(0);
    expect(getOverallStats([question], afterCorrect).percent).toBe(100);
  });
});

describe("exam session", () => {
  it("creates an exam without duplicate questions", () => {
    vi.spyOn(Math, "random").mockReturnValue(0.42);
    const exam = createExam(typedQuestions, 75);
    vi.restoreAllMocks();

    expect(exam.questionIds).toHaveLength(75);
    expect(new Set(exam.questionIds).size).toBe(75);
  });

  it("scores finished exams and treats unanswered questions as review material", () => {
    const sample = typedQuestions.slice(0, 3);
    const questionMap = new Map(sample.map((question) => [question.id, question]));
    const secondAnswer: AnswerKey = sample[1].correct === "A" ? "B" : "A";
    const progress: ProgressState = {
      ...emptyProgress(),
      exam: {
        questionIds: sample.map((question) => question.id),
        answers: {
          [sample[0].id]: sample[0].correct,
          [sample[1].id]: secondAnswer,
        },
        currentIndex: 0,
        completed: false,
        startedAt: new Date().toISOString(),
      },
    };

    const finished = finishExam(progress, questionMap);
    expect(finished.exam?.completed).toBe(true);
    expect(scoreExam(finished.exam!, questionMap)).toMatchObject({ correct: 1, total: 3 });
    expect(getReviewQuestions(sample, finished).map((question) => question.id)).toEqual([sample[1].id, sample[2].id]);
    expect(finished.records[sample[2].id].lastAnswer).toBeUndefined();
    expect(finished.records[sample[2].id].lastSkipped).toBe(true);
  });
});
