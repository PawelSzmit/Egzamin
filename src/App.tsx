import {
  AlertCircle,
  Anchor,
  Bookmark,
  BookOpen,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Eye,
  Flag,
  HelpCircle,
  LifeBuoy,
  ListChecks,
  RotateCcw,
  Sailboat,
  TimerReset,
  Trophy,
  X,
  XCircle,
} from "lucide-react";
import type { CSSProperties } from "react";
import { useEffect, useMemo, useState } from "react";
import questionsData from "./data/questions.json";
import { clearProgress, emptyProgress, loadProgress, saveProgress } from "./storage";
import type { AnswerKey, Mode, Question } from "./types";
import {
  answerExamQuestion,
  answerQuestion,
  createExam,
  filterQuestions,
  finishExam,
  getCategories,
  getOverallStats,
  getRecord,
  moveExam,
  scoreExam,
  toggleBookmark,
} from "./quizLogic";

const questions = questionsData as Question[];
const answerKeys: AnswerKey[] = ["A", "B", "C"];
const modeLabels: Record<Mode, string> = {
  learn: "Nauka",
  exam: "Egzamin",
  review: "Powtórki",
  all: "Wszystkie",
};

const modeIcons = {
  learn: BookOpen,
  exam: TimerReset,
  review: RotateCcw,
  all: ListChecks,
};

const categoryIcon = (index: number) => {
  const icons = [Anchor, Sailboat, Flag, HelpCircle, AlertCircle, BookOpen, LifeBuoy];
  return icons[index % icons.length];
};

function App() {
  const [progress, setProgress] = useState(loadProgress);
  const [mode, setMode] = useState<Mode>("learn");
  const [category, setCategory] = useState("all");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<AnswerKey | null>(null);
  const [visualQuestion, setVisualQuestion] = useState<Question | null>(null);
  const [reviewHoldId, setReviewHoldId] = useState<number | null>(null);

  const questionsById = useMemo(() => new Map(questions.map((question) => [question.id, question])), []);
  const categories = useMemo(() => getCategories(questions, progress), [progress]);
  const stats = useMemo(() => getOverallStats(questions, progress), [progress]);
  const activeQuestions = useMemo(() => {
    if (mode === "exam") {
      return progress.exam?.questionIds.map((id) => questionsById.get(id)).filter(Boolean) as Question[] | undefined;
    }
    const filtered = filterQuestions(questions, progress, mode, category);
    const heldQuestion = reviewHoldId ? questionsById.get(reviewHoldId) : null;
    if (mode === "review" && heldQuestion && !filtered.some((question) => question.id === heldQuestion.id)) {
      return [heldQuestion, ...filtered];
    }
    return filtered;
  }, [category, mode, progress, questionsById, reviewHoldId]);
  const visibleQuestions = activeQuestions ?? [];
  const currentQuestion = visibleQuestions[currentIndex] ?? null;
  const currentRecord = currentQuestion ? getRecord(progress, currentQuestion.id) : null;
  const examScore = progress.exam ? scoreExam(progress.exam, questionsById) : null;

  useEffect(() => {
    saveProgress(progress);
  }, [progress]);

  useEffect(() => {
    setCurrentIndex(0);
    setSelectedAnswer(null);
    setReviewHoldId(null);
  }, [category, mode]);

  useEffect(() => {
    if (mode === "exam" && !progress.exam) {
      setProgress((previous) => ({ ...previous, exam: createExam(questions) }));
    }
  }, [mode, progress.exam]);

  useEffect(() => {
    if (mode === "exam" && progress.exam) {
      setCurrentIndex(progress.exam.currentIndex);
    }
  }, [mode, progress.exam?.currentIndex]);

  const chooseAnswer = (answer: AnswerKey) => {
    if (!currentQuestion) return;
    if (mode === "exam") {
      setProgress((previous) => answerExamQuestion(previous, currentQuestion.id, answer));
      return;
    }
    if (selectedAnswer) return;
    setSelectedAnswer(answer);
    if (mode === "review") {
      setReviewHoldId(currentQuestion.id);
    }
    setProgress((previous) => answerQuestion(previous, currentQuestion, answer));
  };

  const nextQuestion = () => {
    setSelectedAnswer(null);
    setReviewHoldId(null);
    setCurrentIndex((index) => Math.min(index + 1, Math.max(visibleQuestions.length - 1, 0)));
    if (mode === "exam" && progress.exam) {
      setProgress((previous) => moveExam(previous, currentIndex + 1));
    }
  };

  const previousQuestion = () => {
    setSelectedAnswer(null);
    setReviewHoldId(null);
    setCurrentIndex((index) => Math.max(index - 1, 0));
    if (mode === "exam" && progress.exam) {
      setProgress((previous) => moveExam(previous, currentIndex - 1));
    }
  };

  const startNewExam = () => {
    setSelectedAnswer(null);
    setMode("exam");
    setCurrentIndex(0);
    setProgress((previous) => ({ ...previous, exam: createExam(questions) }));
  };

  const finishCurrentExam = () => {
    const unanswered = progress.exam
      ? progress.exam.questionIds.length - Object.keys(progress.exam.answers).length
      : 0;
    if (
      unanswered > 0 &&
      !window.confirm(
        `Masz ${unanswered} pytań bez odpowiedzi. Jeśli zakończysz egzamin teraz, będą policzone jako błędne. Zakończyć egzamin?`,
      )
    ) {
      return;
    }
    setProgress((previous) => finishExam(previous, questionsById));
  };

  const resetAll = () => {
    clearProgress();
    setProgress(emptyProgress());
    setSelectedAnswer(null);
    setCurrentIndex(0);
    setMode("learn");
    setCategory("all");
  };

  const selectedExamAnswer =
    mode === "exam" && currentQuestion ? progress.exam?.answers[currentQuestion.id] ?? null : null;
  const activeAnswer =
    mode === "exam" ? selectedExamAnswer : mode === "review" ? selectedAnswer : selectedAnswer ?? currentRecord?.lastAnswer ?? null;
  const feedbackVisible =
    currentQuestion &&
    mode !== "exam" &&
    (selectedAnswer !== null ||
      (mode !== "review" && (Boolean(currentRecord?.lastAnswer) || currentRecord?.lastSkipped === true)));
  const examCompleted = mode === "exam" && Boolean(progress.exam?.completed);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <Sailboat aria-hidden="true" />
          <span>Patent Żeglarza</span>
        </div>
        <div className="topbar-actions">
          <button className="ghost-button" type="button" onClick={startNewExam}>
            <TimerReset aria-hidden="true" />
            Nowy egzamin
          </button>
          <button className="ghost-button" type="button" onClick={resetAll}>
            <RotateCcw aria-hidden="true" />
            Reset postępu
          </button>
        </div>
      </header>

      <aside className="sidebar">
        <div className="sidebar-heading">
          <span>Działy</span>
          <span>Postęp</span>
        </div>
        <button
          className={category === "all" ? "category-row active" : "category-row"}
          type="button"
          onClick={() => setCategory("all")}
        >
          <ListChecks aria-hidden="true" />
          <span>
            <strong>Wszystkie pytania</strong>
            <small>
              {stats.answered} / {stats.total} ({stats.percent}%)
            </small>
          </span>
        </button>
        {categories.map((item, index) => {
          const Icon = categoryIcon(index);
          const percent = item.answered === 0 ? 0 : Math.round((item.correct / item.answered) * 100);
          return (
            <button
              className={category === item.name ? "category-row active" : "category-row"}
              key={item.name}
              type="button"
              onClick={() => setCategory(item.name)}
            >
              <Icon aria-hidden="true" />
              <span>
                <strong>{item.name}</strong>
                <small>
                  {item.answered} / {item.total} ({percent}%)
                </small>
              </span>
            </button>
          );
        })}
        <div className="sidebar-footer">
          <span>Baza pytań</span>
          <strong>{questions.length}</strong>
        </div>
      </aside>

      <section className="workspace">
        <nav className="mode-tabs" aria-label="Tryb pracy">
          {(Object.keys(modeLabels) as Mode[]).map((key) => {
            const Icon = modeIcons[key];
            return (
              <button
                className={mode === key ? "mode-tab active" : "mode-tab"}
                key={key}
                type="button"
                onClick={() => setMode(key)}
              >
                <Icon aria-hidden="true" />
                {modeLabels[key]}
              </button>
            );
          })}
        </nav>

        <article className="question-panel">
          <QuestionHeader
            category={currentQuestion?.category ?? category}
            current={currentIndex + 1}
            mode={mode}
            total={visibleQuestions.length}
          />

          {!currentQuestion ? (
            <EmptyState mode={mode} onStartExam={startNewExam} />
          ) : (
            <>
              <div className="question-title">
                <span>{currentQuestion.id}.</span>
                <h1>{currentQuestion.question}</h1>
              </div>

              {currentQuestion.has_visual_reference && (currentQuestion.visual_image || currentQuestion.page_image) ? (
                <button className="visual-reference" type="button" onClick={() => setVisualQuestion(currentQuestion)}>
                  <Eye aria-hidden="true" />
                  Zobacz wycinek z rysunkiem
                </button>
              ) : null}

              <div className="answers" role="group" aria-label="Odpowiedzi">
                {answerKeys.map((key) => {
                  const isSelected = activeAnswer === key;
                  const isCorrect = currentQuestion.correct === key;
                  const showResult = examCompleted || feedbackVisible;
                  return (
                    <button
                      className={[
                        "answer",
                        isSelected ? "selected" : "",
                        showResult && isCorrect ? "correct" : "",
                        showResult && isSelected && !isCorrect ? "wrong" : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                      key={key}
                      type="button"
                      onClick={() => chooseAnswer(key)}
                    >
                      <span className="answer-key">{key}</span>
                      <span>{currentQuestion.options[key]}</span>
                      {showResult && isCorrect ? <CheckCircle2 aria-hidden="true" /> : null}
                      {showResult && isSelected && !isCorrect ? <XCircle aria-hidden="true" /> : null}
                    </button>
                  );
                })}
              </div>

              {feedbackVisible ? (
                <div className={currentRecord?.lastCorrect ? "feedback correct" : "feedback wrong"}>
                  {currentRecord?.lastCorrect ? <CheckCircle2 aria-hidden="true" /> : <AlertCircle aria-hidden="true" />}
                  <div>
                    <strong>
                      {currentRecord?.lastCorrect
                        ? "Dobra odpowiedź"
                        : currentRecord?.lastSkipped
                          ? `Pominięto. Poprawna odpowiedź: ${currentQuestion.correct}`
                          : `Poprawna odpowiedź: ${currentQuestion.correct}`}
                    </strong>
                    <p>{currentQuestion.correct_answer}</p>
                  </div>
                </div>
              ) : null}

              {examCompleted && examScore ? (
                <div className="feedback correct">
                  <Trophy aria-hidden="true" />
                  <div>
                    <strong>
                      Wynik egzaminu: {examScore.correct} / {examScore.total} ({examScore.percent}%)
                    </strong>
                    <p>Błędne i puste odpowiedzi trafiły do powtórek.</p>
                  </div>
                </div>
              ) : null}

              <div className="question-actions">
                <button
                  className="ghost-button"
                  disabled={currentIndex === 0}
                  type="button"
                  onClick={previousQuestion}
                >
                  <ChevronLeft aria-hidden="true" />
                  Poprzednie
                </button>
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => setProgress((previous) => toggleBookmark(previous, currentQuestion.id))}
                >
                  <Bookmark aria-hidden="true" />
                  {currentRecord?.bookmarked ? "Usuń z oznaczonych" : "Dodaj do powtórek"}
                </button>
                {mode === "exam" && !examCompleted ? (
                  <button className="primary-button" type="button" onClick={finishCurrentExam}>
                    Zakończ egzamin
                  </button>
                ) : null}
                <button
                  className="primary-button"
                  disabled={currentIndex >= visibleQuestions.length - 1}
                  type="button"
                  onClick={nextQuestion}
                >
                  Następne pytanie
                  <ChevronRight aria-hidden="true" />
                </button>
              </div>
            </>
          )}
        </article>
      </section>

      <aside className="progress-panel">
        <ProgressCard stats={stats} />
        <div className="side-card">
          <div className="side-card-title">
            <span>Powtórki</span>
            <strong>{stats.review}</strong>
          </div>
          <p>Pytania błędne albo oznaczone wracają tutaj, żeby można było je spokojnie przećwiczyć.</p>
          <button className="ghost-button full" type="button" onClick={() => setMode("review")}>
            <RotateCcw aria-hidden="true" />
            Przejdź do powtórek
          </button>
        </div>
        <div className="side-card">
          <div className="side-card-title">
            <span>Egzamin</span>
            <strong>{progress.exam?.questionIds.length ?? 75}</strong>
          </div>
          <p>Sesja próbna losuje do 75 pytań i zapisuje błędne odpowiedzi do powtórek.</p>
          {examScore ? (
            <small>
              Odpowiedziano: {examScore.answered} / {examScore.total}
            </small>
          ) : null}
        </div>
      </aside>

      {visualQuestion ? <VisualModal question={visualQuestion} onClose={() => setVisualQuestion(null)} /> : null}
    </main>
  );
}

type QuestionHeaderProps = {
  category: string;
  current: number;
  mode: Mode;
  total: number;
};

function QuestionHeader({ category, current, mode, total }: QuestionHeaderProps) {
  const progress = total === 0 ? 0 : Math.round((current / total) * 100);
  return (
    <header className="question-header">
      <div>
        <span>
          {modeLabels[mode]}: {total === 0 ? 0 : current} z {total}
        </span>
        <strong>{category === "all" ? "Wszystkie działy" : category}</strong>
      </div>
      <div className="meter" aria-label={`Postęp ${progress}%`}>
        <span style={{ width: `${progress}%` }} />
      </div>
    </header>
  );
}

type EmptyStateProps = {
  mode: Mode;
  onStartExam: () => void;
};

function EmptyState({ mode, onStartExam }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <LifeBuoy aria-hidden="true" />
      <h1>{mode === "review" ? "Nie masz teraz pytań do powtórki" : "Brak pytań w tym widoku"}</h1>
      <p>
        Gdy odpowiesz błędnie albo oznaczysz pytanie, pojawi się ono w powtórkach. Egzamin możesz rozpocząć w każdej
        chwili.
      </p>
      <button className="primary-button" type="button" onClick={onStartExam}>
        Rozpocznij egzamin
      </button>
    </div>
  );
}

type ProgressCardProps = {
  stats: ReturnType<typeof getOverallStats>;
};

function ProgressCard({ stats }: ProgressCardProps) {
  return (
    <div className="progress-card">
      <h2>Twój postęp</h2>
      <div className="ring" style={{ "--percent": `${stats.percent}%` } as CSSProperties}>
        <span>{stats.percent}%</span>
      </div>
      <dl>
        <div>
          <dt>Poprawne</dt>
          <dd>{stats.correct}</dd>
        </div>
        <div>
          <dt>Błędne</dt>
          <dd>{stats.wrong}</dd>
        </div>
        <div>
          <dt>Bez odpowiedzi</dt>
          <dd>{stats.total - stats.answered}</dd>
        </div>
      </dl>
    </div>
  );
}

type VisualModalProps = {
  question: Question;
  onClose: () => void;
};

function VisualModal({ question, onClose }: VisualModalProps) {
  const image = `${import.meta.env.BASE_URL}${question.visual_image ?? question.page_image}`;
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Podgląd rysunku do pytania">
      <div className="modal">
        <div className="modal-header">
          <div>
            <strong>Pytanie {question.id}</strong>
            <span>Wycinek ze strony {question.page} oficjalnego PDF-a</span>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Zamknij podgląd">
            <X aria-hidden="true" />
          </button>
        </div>
        <div className="modal-image-scroll">
          <img src={image} alt={`Wycinek z rysunkiem do pytania ${question.id}`} />
        </div>
      </div>
    </div>
  );
}

export default App;
