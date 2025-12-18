"""
Chat-related prompts for TAI Tutor AI.

This module provides centralized prompt management for the chat system.
It supports:
- Response Styles: Formal, Casual, Technical
- Response Types: Direct, Hinting, Socratic
- Response Lengths: Short, Medium, Long
- Conversation History Context
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re


# Guardrail: Patterns that may indicate harmful or inappropriate requests
HARMFUL_PATTERNS = [
    r'\b(hack|exploit|crack|bypass|steal|phish|malware|virus|trojan)\b',
    r'\b(cheat|plagiarize|copy.*assignment|solve.*exam|homework.*solution)\b',
    r'\b(attack|ddos|dos|injection|xss|csrf)\b',
    r'\b(password.*crack|brute.*force|unauthorized.*access)\b',
]

# Educational exceptions - these are okay in an educational context
EDUCATIONAL_CONTEXT_PATTERNS = [
    r'\b(learn.*about|understand|study|research|what.*is)\b',
    r'\b(security|vulnerability|protection|defense|prevent)\b',
    r'\b(ethical.*hacking|penetration.*testing|security.*audit)\b',
]


@dataclass
class ConversationMessage:
    """Represents a single message in conversation history."""
    role: str  # 'user' or 'assistant'
    content: str


class ChatPrompter:
    """
    Manages prompt templates for the TAI Tutor AI.
    
    Combines response style, type, and length preferences with conversation
    history to generate context-aware prompts.
    """
    
    # Response Style Templates
    STYLE_TEMPLATES = {
        "formal": """You are a professional academic tutor with expertise in computer science education.
- Use formal, professional language and proper academic terminology
- Maintain a structured, methodical approach to explanations
- Address the student respectfully (e.g., "you" or "the student")
- Organize responses with clear structure: introduction, main points, conclusion
- Cite best practices and established principles when relevant
- Maintain an encouraging yet professional tone that builds confidence""",
        
        "casual": """You are a friendly and supportive study buddy who makes learning enjoyable.
- Use conversational, approachable language that feels natural
- Include relatable examples and analogies from everyday life
- Use a warm, encouraging tone with appropriate casual expressions
- Balance friendliness with accuracy and helpfulness
- Make complex topics feel accessible and less intimidating
- Maintain educational rigor while keeping the atmosphere light and positive""",
        
        "technical": """You are a technical expert and mentor with deep domain knowledge.
- Use precise technical terminology and industry-standard vocabulary
- Provide detailed, technically accurate explanations with appropriate depth
- Include relevant code examples, algorithms, or technical specifications
- Reference documentation, standards, and best practices
- Focus on correctness, efficiency, and professional-grade solutions
- Explain trade-offs, edge cases, and implementation considerations
- Assume the student wants to understand things at a deeper technical level"""
    }
    
    # Response Type Templates
    TYPE_TEMPLATES = {
        "direct": """Provide a direct, clear, and well-structured answer to the question. 
Give a complete explanation that helps the student understand the concept, not just the solution.
- Be comprehensive yet concise
- Explain the reasoning and context
- Include examples when helpful
- Highlight key takeaways
- Maintain educational value even when providing direct answers""",
        
        "hinting": """Guide the student toward discovering the answer through strategic hints and scaffolding. 
This promotes active learning and deeper understanding. Do NOT give the direct answer immediately. Instead:
1. Acknowledge their question and what they're trying to accomplish
2. Provide a targeted hint that points them in the right direction without solving it for them
3. Ask a guiding question that helps them think through the next step
4. Encourage them to try before revealing more
5. Only provide additional hints or partial solutions if they remain stuck after genuine effort
Remember: The goal is to help them learn to solve problems independently.""",
        
        "socratic": """Use the Socratic method to facilitate discovery learning and critical thinking.
Instead of providing direct answers, engage in a dialogue that leads students to insights:
1. Ask thought-provoking, open-ended questions that probe their understanding
2. Gently challenge assumptions and encourage them to justify their reasoning
3. Guide them through logical reasoning by breaking down complex problems
4. Build on their responses to lead them toward the correct understanding
5. Celebrate their discoveries and insights, reinforcing positive learning behaviors
6. Encourage deeper exploration by asking "what if" or "why do you think" questions
Focus on developing their problem-solving skills and metacognition."""
    }
    
    # Response Length Guidelines
    LENGTH_GUIDELINES = {
        "short": """Keep your response brief and to the point. 
Aim for 2-3 sentences or a short paragraph. Focus on the essential information only.""",
        
        "medium": """Provide a balanced response with adequate detail. 
Aim for 2-3 paragraphs. Include key explanations and one or two examples if helpful.""",
        
        "long": """Provide a comprehensive, detailed response. 
Include thorough explanations, multiple examples, and cover related concepts. 
Use proper formatting (bullet points, numbered lists) for clarity."""
    }
    
    # Base System Prompt with Guardrails
    BASE_SYSTEM_PROMPT = """You are TAI Tutor AI, an intelligent educational assistant designed to help 
students learn programming concepts, computer science fundamentals, and related topics.

Your primary goals:
- Help students understand concepts deeply through clear, accurate explanations
- Encourage learning, critical thinking, and intellectual curiosity
- Provide accurate, helpful, and educational information
- Adapt to the student's learning style and needs
- Foster a positive, inclusive learning environment

When answering questions about code:
- Explain the logic and reasoning, not just the syntax
- Point out common pitfalls and misconceptions
- Suggest best practices and industry standards
- Use clear, readable, well-commented code examples when appropriate
- Emphasize secure coding practices and potential security implications

CONTENT GUARDRAILS - You must refuse to:
- Provide solutions for academic dishonesty (e.g., complete homework/exam solutions without educational value)
- Generate code for harmful, malicious, or unethical purposes (malware, exploits, harassment tools)
- Assist with bypassing security measures, accessing unauthorized systems, or violating privacy
- Produce content that is discriminatory, hateful, violent, sexually explicit, or promotes harm
- Help with plagiarism or copyright infringement
- Provide medical, legal, or financial advice outside educational context

EDUCATIONAL BOUNDARIES:
- When students ask for direct solutions, guide them toward understanding instead
- If a request seems inappropriate for an educational context, politely decline and explain why
- Focus on teaching concepts and problem-solving approaches, not just providing answers
- Encourage ethical coding practices and responsible technology use

If you're uncertain whether a request violates these guidelines, err on the side of caution and 
redirect the conversation toward legitimate educational goals."""

    def __init__(
        self,
        style: str = "formal",
        response_type: str = "direct", 
        length: str = "medium",
        conversation_history: Optional[List[ConversationMessage]] = None
    ):
        """
        Initialize the ChatPrompter with preferences.
        
        Args:
            style: Response style - 'formal', 'casual', or 'technical'
            response_type: Response type - 'direct', 'hinting', or 'socratic'
            length: Response length - 'short', 'medium', or 'long'
            conversation_history: Optional list of previous conversation messages
        """
        self.style = style.lower() if style else "formal"
        self.response_type = response_type.lower() if response_type else "direct"
        self.length = length.lower() if length else "medium"
        self.conversation_history = conversation_history or []
        
        # Validate inputs
        if self.style not in self.STYLE_TEMPLATES:
            self.style = "formal"
        if self.response_type not in self.TYPE_TEMPLATES:
            self.response_type = "direct"
        if self.length not in self.LENGTH_GUIDELINES:
            self.length = "medium"
    
    def build_system_prompt(self) -> str:
        """Build the complete system prompt combining all preferences."""
        parts = [self.BASE_SYSTEM_PROMPT]
        
        # Add style instructions
        parts.append(f"\n## Response Style\n{self.STYLE_TEMPLATES[self.style]}")
        
        # Add response type instructions
        parts.append(f"\n## Response Approach\n{self.TYPE_TEMPLATES[self.response_type]}")
        
        # Add length guidelines
        parts.append(f"\n## Response Length\n{self.LENGTH_GUIDELINES[self.length]}")
        
        return "\n".join(parts)
    
    def format_conversation_history(self, max_messages: int = 10) -> str:
        """
        Format conversation history for context inclusion.
        
        Args:
            max_messages: Maximum number of recent messages to include
            
        Returns:
            Formatted conversation history string
        """
        if not self.conversation_history:
            return ""
        
        # Take the most recent messages
        recent = self.conversation_history[-max_messages:]
        
        formatted_parts = ["\n## Previous Conversation Context"]
        for msg in recent:
            role_label = "Student" if msg.role == "user" else "Tutor"
            # Truncate very long messages for context
            content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            formatted_parts.append(f"{role_label}: {content}")
        
        formatted_parts.append("\n## Current Question")
        return "\n".join(formatted_parts)
    
    def build_full_prompt(self, user_question: str) -> str:
        """
        Build the complete prompt with system instructions, history, and question.
        
        Args:
            user_question: The current question from the user
            
        Returns:
            Complete formatted prompt ready for LLM
        """
        parts = [self.build_system_prompt()]
        
        # Add conversation history if available
        history_context = self.format_conversation_history()
        if history_context:
            parts.append(history_context)
        
        # Add the current question
        parts.append(f"\nStudent's Question: {user_question}")
        parts.append("\nYour Response:")
        
        return "\n".join(parts)
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            role: 'user' or 'assistant'
            content: The message content
        """
        self.conversation_history.append(ConversationMessage(role=role, content=content))
    
    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.conversation_history = []
    
    def check_content_safety(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if the input text appears to request harmful or inappropriate content.
        
        Args:
            text: The text to check
            
        Returns:
            Tuple of (is_safe, warning_message)
            - is_safe: True if content seems safe, False if potentially harmful
            - warning_message: Optional message explaining the concern
        """
        text_lower = text.lower()
        
        # Check for harmful patterns
        has_harmful = False
        for pattern in HARMFUL_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                has_harmful = True
                break
        
        if not has_harmful:
            return (True, None)
        
        # Check if it's in an educational context
        has_educational_context = False
        for pattern in EDUCATIONAL_CONTEXT_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                has_educational_context = True
                break
        
        if has_educational_context:
            # Likely educational - allow but with reminder
            return (True, "educational_context_detected")
        
        # Appears to be requesting harmful content
        warning = (
            "I notice this request may involve content that could be used harmfully. "
            "I'm here to help with legitimate educational topics. If you're trying to learn "
            "about security concepts, please frame your question in an educational context "
            "(e.g., 'How can I learn about security vulnerabilities to protect my applications?')."
        )
        return (False, warning)
    
    def get_history_as_list(self) -> List[Dict[str, str]]:
        """Get conversation history as a list of dicts for JSON serialization."""
        return [{"role": msg.role, "content": msg.content} for msg in self.conversation_history]
    
    @classmethod
    def from_history_list(
        cls,
        history: List[Dict[str, str]],
        style: str = "formal",
        response_type: str = "direct",
        length: str = "medium"
    ) -> "ChatPrompter":
        """
        Create a ChatPrompter from a serialized history list.
        
        Args:
            history: List of dicts with 'role' and 'content' keys
            style: Response style preference
            response_type: Response type preference
            length: Response length preference
            
        Returns:
            Configured ChatPrompter instance
        """
        conv_history = [
            ConversationMessage(role=msg.get("role", "user"), content=msg.get("content", ""))
            for msg in history
        ]
        return cls(
            style=style,
            response_type=response_type,
            length=length,
            conversation_history=conv_history
        )


# =============================================================================
# Convenience Functions
# =============================================================================

def get_hint_prompt(question: str, style: str = "formal") -> str:
    """Generate a hint-mode prompt."""
    prompter = ChatPrompter(style=style, response_type="hinting", length="medium")
    return prompter.build_full_prompt(question)


def get_direct_prompt(question: str, style: str = "formal") -> str:
    """Generate a direct-answer prompt."""
    prompter = ChatPrompter(style=style, response_type="direct", length="medium")
    return prompter.build_full_prompt(question)


def get_socratic_prompt(question: str, style: str = "formal") -> str:
    """Generate a Socratic-method prompt."""
    prompter = ChatPrompter(style=style, response_type="socratic", length="medium")
    return prompter.build_full_prompt(question)


# =============================================================================
# Default Prompter Instances
# =============================================================================

DEFAULT_PROMPTER = ChatPrompter()
HINT_PROMPTER = ChatPrompter(response_type="hinting")
SOCRATIC_PROMPTER = ChatPrompter(response_type="socratic")
