// src/components/shared/icons.tsx
import React from "react";

export interface MaterialIconProps extends React.HTMLAttributes<HTMLSpanElement> {
  name: string;
  className?: string;
  size?: number;
}

/**
 * Base Google Material Symbols Icon Engine
 */
export const Icon: React.FC<MaterialIconProps> = ({
  name,
  className = "",
  size,
  style,
  ...props
}) => {
  return (
    <span
      className={`material-symbols-outlined select-none align-middle ${className}`}
      style={{ fontSize: size ? `${size}px` : undefined, ...style }}
      {...props}
    >
      {name}
    </span>
  );
};

type IconWrapperProps = Omit<MaterialIconProps, "name">;

/* ============================================================
 * Utility & Common Icons
 * ========================================================== */

export const CheckCircleIcon = (props: IconWrapperProps) => (
  <Icon name="check_circle" {...props} />
);

export const CancelIcon = (props: IconWrapperProps) => (
  <Icon name="cancel" {...props} />
);

export const MailIcon = (props: IconWrapperProps) => (
  <Icon name="mail" {...props} />
);

export const LockIcon = (props: IconWrapperProps) => (
  <Icon name="lock" {...props} />
);

export const PersonIcon = (props: IconWrapperProps) => (
  <Icon name="person" {...props} />
);

export const RefreshIcon = (props: IconWrapperProps) => (
  <Icon name="refresh" {...props} />
);

export const ArrowForwardIcon = (props: IconWrapperProps) => (
  <Icon name="arrow_forward" {...props} />
);

export const ArrowBackIcon = (props: IconWrapperProps) => (
  <Icon name="arrow_back" {...props} />
);

export const WarningIcon = (props: IconWrapperProps) => (
  <Icon name="warning" {...props} />
);

export const ProgressActivityIcon = (props: IconWrapperProps) => (
  <Icon name="progress_activity" {...props} />
);

/* ============================================================
 * Legacy Icons (Mapped to Material Symbols)
 * ========================================================== */

export const DocumentIcon = (props: IconWrapperProps) => (
  <Icon name="description" {...props} />
);

export const PenIcon = (props: IconWrapperProps) => (
  <Icon name="edit" {...props} />
);

export const GradeIcon = (props: IconWrapperProps) => (
  <Icon name="assignment" {...props} />
);

export const ChatIcon = (props: IconWrapperProps) => (
  <Icon name="chat" {...props} />
);

export const UserIcon = (props: IconWrapperProps) => (
  <Icon name="person" {...props} />
);

export const KeyIcon = (props: IconWrapperProps) => (
  <Icon name="key" {...props} />
);

export const LogoutIcon = (props: IconWrapperProps) => (
  <Icon name="logout" {...props} />
);

export const BookmarkIcon = (props: IconWrapperProps) => (
  <Icon name="bookmark" {...props} />
);

export const DocumentDuplicateIcon = (props: IconWrapperProps) => (
  <Icon name="content_copy" {...props} />
);

export const CheckIcon = (props: IconWrapperProps) => (
  <Icon name="check" {...props} />
);

export const TrashIcon = (props: IconWrapperProps) => (
  <Icon name="delete" {...props} />
);

export const SaveIcon = (props: IconWrapperProps) => (
  <Icon name="save" {...props} />
);

export const LightbulbIcon = (props: IconWrapperProps) => (
  <Icon name="lightbulb" {...props} />
);

export const FilterIcon = (props: IconWrapperProps) => (
  <Icon name="filter_alt" {...props} />
);

export const CloseIcon = (props: IconWrapperProps) => (
  <Icon name="close" {...props} />
);

export const AddIcon = (props: IconWrapperProps) => (
  <Icon name="add" {...props} />
);

export const EditIcon = (props: IconWrapperProps) => (
  <Icon name="edit" {...props} />
);

export const DeleteIcon = (props: IconWrapperProps) => (
  <Icon name="delete" {...props} />
);

export const ChatBubbleIcon = (props: IconWrapperProps) => (
  <Icon name="chat" {...props} />
);

export const BotMessageIcon = (props: IconWrapperProps) => (
  <Icon name="smart_toy" {...props} />
);

/* ============================================================
 * Quiz & Interactive Icons (Mapped to Material Symbols)
 * ========================================================== */

export const MultipleChoiceIcon = (props: IconWrapperProps) => (
  <Icon name="radio_button_checked" {...props} />
);

export const MultipleResponseIcon = (props: IconWrapperProps) => (
  <Icon name="check_box" {...props} />
);

export const TrueFalseIcon = (props: IconWrapperProps) => (
  <Icon name="rule" {...props} />
);

export const FillBlankIcon = (props: IconWrapperProps) => (
  <Icon name="space_bar" {...props} />
);

export const ShortAnswerIcon = (props: IconWrapperProps) => (
  <Icon name="short_text" {...props} />
);

export const CustomQuizIcon = (props: IconWrapperProps) => (
  <Icon name="tune" {...props} />
);

export const ChevronDownIcon = (props: IconWrapperProps) => (
  <Icon name="expand_more" {...props} />
);

export const ChevronRightIcon = (props: IconWrapperProps) => (
  <Icon name="chevron_right" {...props} />
);

export const InfoCircleIcon = (props: IconWrapperProps) => (
  <Icon name="info" {...props} />
);

export const CheckedBoxIcon = (props: IconWrapperProps) => (
  <Icon name="check_box" {...props} />
);

export const UncheckedBoxIcon = (props: IconWrapperProps) => (
  <Icon name="check_box_outline_blank" {...props} />
);