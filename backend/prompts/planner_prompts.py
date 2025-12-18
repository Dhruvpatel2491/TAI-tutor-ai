"""
Planner-related prompts for TAI Tutor AI.

This module contains prompt templates for learning plan generation.
All prompts include guardrails for appropriate educational content and realistic planning.
"""

from typing import Optional


# Content Safety and Quality Guidelines
PLANNER_GUIDELINES = """
LEARNING PLAN QUALITY STANDARDS:
- Create realistic, achievable plans based on the stated timeframe
- Use evidence-based learning principles (spaced repetition, active recall, practice)
- Ensure all recommendations are appropriate for educational contexts
- Do NOT create plans for harmful, unethical, or inappropriate topics
- Focus on legitimate educational and professional development goals
- Include appropriate time buffers and breaks in schedules
- Set achievable milestones that build confidence

CONTENT BOUNDARIES:
- Plans should support legitimate learning goals only
- Avoid creating plans that could facilitate academic dishonesty
- Do not include activities that violate ethical standards
- Redirect inappropriate requests toward legitimate educational alternatives
"""


def build_plan_prompt(
    requirement: str,
    user_id: str,
    original_plan: Optional[str] = None,
    edit_instructions: Optional[str] = None
) -> str:
    """
    Construct a plan generation prompt for the LLM.
    
    Args:
        requirement: User's learning requirement/goal
        user_id: User identifier
        original_plan: Previous plan for iterative editing
        edit_instructions: Specific editing instructions
    
    Returns:
        Formatted prompt string
    """
    base = (
        "You are an expert educational consultant and instructional designer specializing in personalized "
        "learning plans. Your role is to create comprehensive, actionable, and pedagogically sound study plans "
        "tailored to each learner's stated requirements and goals.\n\n"
        f"{PLANNER_GUIDELINES}\n\n"
        "YOUR TASK: Create a well-structured, realistic, and motivating learning plan in plain text using clear headings. "
        "Be explicit and concrete: translate the user's requirement into specific actions, realistic timeframes, "
        "measurable objectives, and practical exercises.\n\n"
        
        "Required sections (use these exact headings):\n"
        "- Title (1 line)\n"
        "- Learning Objectives (3-5 concise, measurable objectives)\n"
        "- Suggested Schedule (state total duration; provide a block-by-block or day-by-day schedule with minutes/hours)\n"
        "- Exercises (3 concrete practice activities; for one activity include step-by-step instructions and expected deliverable)\n"
        "- Assessment & Success Criteria (how the learner will know they succeeded; include quick rubric or pass/fail checks)\n"
        "- Quick Self-Check Questions (3 questions, mark one as 'Stretch')\n"
        "- Recommended Resources (2-4 named resources or short descriptions; prefer search terms or authoritative sources rather than raw links)\n"
        "- Tips for Study (2-4 tactical tips)\n"
        "- Optional Extensions & Differentiation (one recommendation each for 'Beginner' and 'Advanced')\n\n"
        
        "FORMATTING AND CONTENT RULES:\n"
        "1) Return ONLY the plan text in plain text with clear headings (no JSON, no extra commentary, no system notes).\n"
        "2) TIMEFRAME ADAPTATION: If the requirement mentions a specific timeframe (e.g., '1 month', '5 hours/week', '3 days'), "
        "adapt the Suggested Schedule to realistically fit that constraint. Include buffer time for review and unexpected delays.\n"
        "3) REALISTIC TIME ESTIMATES: Provide specific, realistic time estimates for each block and exercise. "
        "If no timeframe is provided, assume a default total of ~60 minutes. Consider actual human learning pace, not ideal conditions.\n"
        "4) CONCRETE CONTENT: Replace ANY placeholder tokens (e.g., '[insert ...]', '[TBD]', '[example]') with concrete, "
        "specific values derived directly from the requirement. Do NOT emit placeholder markers of any kind.\n"
        "5) BALANCED DETAIL: Keep output focused yet comprehensive. Include enough actionable detail for immediate use "
        "(specific examples, clear deliverables, measurable success checks). Target 800-1000 words for optimal usability.\n"
        "6) MOTIVATIONAL TONE: Frame the plan positively. Acknowledge challenges but emphasize achievability and growth.\n\n"
        
        "ADAPTATION STRATEGY: When adapting the requirement, prioritize clarity, structure, and immediate actionable next steps. "
        "If the requirement is too broad (e.g., 'learn programming'), narrow it to a clear, focused scope with a specific starting point "
        "(e.g., 'learn Python basics: variables, loops, and functions'). Explain this focus choice in the Title or Learning Objectives.\n\n"
        "SAFETY CHECK: If the requirement seems inappropriate, unclear, or potentially harmful, redirect to a related legitimate "
        "educational topic and note the adaptation in the plan.\n\n"
        
        "Requirement: {requirement}\n"
        "User: {user_id}\n\n"
    )
    
    prompt = base.format(requirement=requirement.strip(), user_id=user_id)
    
    if original_plan:
        prompt += "Previous plan:\n" + original_plan + "\n\n"
    
    if edit_instructions:
        prompt += "Edit instructions: " + edit_instructions + "\n\n"
    
    prompt += "Return only the plan text in plain text with headings. Keep the whole plan under 1000 words."
    
    return prompt


def generate_fallback_plan(
    requirement: str,
    user_id: str,
    original_plan: Optional[str] = None,
    edit_instructions: Optional[str] = None
) -> str:
    """
    Generate a deterministic fallback plan when LLM is unavailable.
    
    Args:
        requirement: User's learning requirement
        user_id: User identifier
        original_plan: Previous plan for context
        edit_instructions: Editing instructions
    
    Returns:
        Formatted plan text
    """
    topic = requirement.strip() or "the requested topic"
    title = f"Fallback Study Plan: {topic[:60]}"
    
    # Derive objectives
    objectives = []
    if ":" in topic or "-" in topic:
        parts = [p.strip() for p in topic.replace('-', ':').split(':') if p.strip()]
        for p in parts[:4]:
            objectives.append(f"Understand and apply: {p}")
    else:
        objectives = [
            f"Understand the core concepts of {topic}",
            f"Be able to explain key use-cases and limitations of {topic}",
            f"Apply {topic} in a simple example or exercise",
        ]
    
    # Schedule blocks
    total_minutes = 60
    schedule_blocks = [
        (5, "Introduction: goals & quick review"),
        (20, "Direct instruction: concise reading or short video on the topic"),
        (15, "Guided practice: worked examples and walkthroughs"),
        (10, "Independent practice: try a short problem"),
        (10, "Reflection & self-check questions")
    ]
    
    # Exercises
    exercises = [
        {
            "title": f"Example problem applying {topic}",
            "time": "15 minutes",
            "task": f"Solve a short problem that requires using {topic}. Write the steps and final answer."
        },
        {
            "title": "Teaching exercise",
            "time": "10 minutes",
            "task": f"Summarize {topic} in your own words as if teaching a peer (3-5 sentences)."
        },
        {
            "title": "Extension challenge",
            "time": "15 minutes",
            "task": f"Modify the example to a slightly harder version and describe the differences in approach."
        }
    ]
    
    # Self-check questions
    self_checks = [
        f"What is the primary purpose of {topic}?",
        f"How would you choose an approach or technique when solving a problem involving {topic}?",
        f"Stretch: Describe a real-world scenario where {topic} is useful and why."
    ]
    
    # Resources
    resources = [
        f"Official intro or documentation about {topic} (search for '{topic} tutorial' or relevant docs)",
        f"A short video or article that gives a worked example of {topic}",
    ]
    
    # Tips
    tips = [
        "Take short notes and summarize after each block.",
        "Use active recall: try answering the self-checks without notes.",
        "If stuck, break the problem into smaller sub-steps and re-check assumptions."
    ]
    
    # Build plan text
    parts = [title]
    
    parts.append("\nLearning Objectives:")
    for obj in objectives:
        parts.append(f"- {obj}")
    
    parts.append(f"\nSuggested Schedule ({total_minutes} minutes):")
    for m, desc in schedule_blocks:
        parts.append(f"- {m} minutes — {desc}")
    
    parts.append("\nExercises:")
    for ex in exercises:
        parts.append(f"- {ex['title']} ({ex['time']}): {ex['task']}")
    
    parts.append("\nQuick Self-Check Questions:")
    for q in self_checks:
        parts.append(f"- {q}")
    
    parts.append("\nRecommended Resources:")
    for r in resources:
        parts.append(f"- {r}")
    
    parts.append("\nTips for Study:")
    for t in tips:
        parts.append(f"- {t}")
    
    # Include original plan/edit instructions if provided
    if original_plan:
        parts.append("\nNote: This plan was generated from the user's requirement; see previous plan below for comparison.")
        parts.append(original_plan)
    
    if edit_instructions:
        parts.append(f"\nEdit instructions applied: {edit_instructions}")
    
    return "\n".join(parts)
