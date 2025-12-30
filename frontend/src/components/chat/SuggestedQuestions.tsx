import { Button } from '@/components/ui/button';
import { Sparkles } from 'lucide-react';

interface SuggestedQuestionsProps {
  questions: string[];
  onQuestionClick: (question: string) => void;
  isLoading?: boolean;
  title?: string;
  className?: string;
}

export const SuggestedQuestions = ({
  questions,
  onQuestionClick,
  isLoading = false,
  title = "Try asking:",
  className = ""
}: SuggestedQuestionsProps) => {
  if (questions.length === 0) return null;

  return (
    <div className={`space-y-3 ${className}`}>
      {title && (
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Sparkles className="h-4 w-4" />
          <span>{title}</span>
        </div>
      )}
      <div className="grid gap-2">
        {questions.map((question, index) => (
          <Button
            key={index}
            variant="outline"
            onClick={() => onQuestionClick(question)}
            disabled={isLoading}
            className="text-left h-auto py-3 px-4 whitespace-normal justify-start hover:bg-secondary/80 transition-all"
          >
            <span className="text-sm">{question}</span>
          </Button>
        ))}
      </div>
    </div>
  );
};
