from enum import StrEnum
from typing import Final


# ==========================================================
# Document Classification
# ==========================================================


class Category(StrEnum):
    MATHEMATICS = "mathematics"
    COMPUTER_SCIENCE = "computer_science"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    ECONOMICS_BUSINESS = "economics_business"
    SOCIAL_SCIENCES_HUMANITIES = "social_sciences_humanities"
    LANGUAGE_LITERATURE = "language_literature"
    MEDICINE_HEALTH = "medicine_health"
    ARTS = "arts"
    OTHER = "other"


class Language(StrEnum):
    VI = "vi"
    EN = "en"
    OTHER = "other"


class Purpose(StrEnum):
    LEARNING_MATERIAL = "learning_material"
    EXAM = "exam"
    SOLUTION = "solution"
    ASSIGNMENT = "assignment"
    REFERENCE = "reference"


# ==========================================================
# Category Descriptions
# ==========================================================

CATEGORY_DESCRIPTIONS: Final[dict[Category, str]] = {
    Category.MATHEMATICS:
        "Mathematics and Statistics.",

    Category.COMPUTER_SCIENCE:
        "Computer Science and Software Engineering.",

    Category.PHYSICS:
        "Physics and related fields.",

    Category.CHEMISTRY:
        "Chemistry and related fields.",

    Category.BIOLOGY:
        "Biology and Life Sciences.",

    Category.ECONOMICS_BUSINESS:
        "Economics, Finance, Business and Management.",

    Category.SOCIAL_SCIENCES_HUMANITIES:
        "History, Geography, Philosophy, Law, Psychology and related disciplines.",

    Category.LANGUAGE_LITERATURE:
        "Languages, Linguistics and Literature.",

    Category.MEDICINE_HEALTH:
        "Medicine, Pharmacy, Nursing and Health Sciences.",

    Category.ARTS:
        "Arts, Music, Design and Architecture.",

    Category.OTHER:
        "None of the predefined categories.",
}


# ==========================================================
# Purpose Definitions
# ==========================================================

PURPOSE_DEFINITIONS: Final[dict[Purpose, str]] = {
    Purpose.LEARNING_MATERIAL:
        "Lecture notes, textbooks, learning materials or study guides.",

    Purpose.EXAM:
        "Exam papers, mock tests, quizzes or assessment documents.",

    Purpose.SOLUTION:
        "Answer keys, worked solutions or grading rubrics.",

    Purpose.ASSIGNMENT:
        "Homework, exercises, worksheets or project requirements.",

    Purpose.REFERENCE:
        "Reference documents that support learning but are not intended as primary teaching material.",
}

# ==========================================================
# Skill Taxonomy
# ==========================================================

SKILL_TAXONOMY: Final[dict[Category, list[str]]] = {
    Category.MATHEMATICS: [
        "Computation",
        "Problem Solving",
        "Logical Reasoning",
        "Proof Writing",
        "Abstraction & Generalization",
        "Spatial/Geometric Reasoning",
    ],
    Category.COMPUTER_SCIENCE: [
        "Algorithmic Thinking",
        "Data Structures & Complexity",
        "Debugging & Testing",
        "System Design",
        "Syntax/Implementation",
        "Problem Decomposition",
    ],
    Category.PHYSICS: [
        "Conceptual Understanding",
        "Mathematical Modeling",
        "Experimental Reasoning",
        "Data Interpretation",
        "Real-world Application",
    ],
    Category.CHEMISTRY: [
        "Conceptual Understanding",
        "Reaction Analysis",
        "Experimental Reasoning",
        "Data Interpretation",
        "Quantitative Application",
    ],
    Category.BIOLOGY: [
        "Conceptual Understanding",
        "Classification",
        "Experimental Reasoning",
        "Data Interpretation",
        "Real-world Application",
    ],
    Category.ECONOMICS_BUSINESS: [
        "Quantitative Analysis",
        "Conceptual Understanding",
        "Case Application",
        "Critical Evaluation",
        "Strategic Decision Making",
    ],
    Category.SOCIAL_SCIENCES_HUMANITIES: [
        "Conceptual Analysis",
        "Critical Reasoning",
        "Argumentation",
        "Case Application",
        "Contextual Understanding",
        "Ethical Reasoning",
    ],
    Category.LANGUAGE_LITERATURE: [
        "Vocabulary",
        "Grammar",
        "Reading Comprehension",
        "Writing",
        "Textual Analysis",
    ],
    Category.MEDICINE_HEALTH: [
        "Factual Recall",
        "Clinical Reasoning",
        "Case Application",
        "Lab/Data Interpretation",
        "Ethical Judgment",
    ],
    Category.ARTS: [
        "Technique",
        "Conceptual Understanding",
        "Creative Application",
        "Critical Appreciation",
        "Historical Context",
    ],
    Category.OTHER: [
        "Recall",
        "Comprehension",
        "Application",
        "Analysis",
    ],
}
