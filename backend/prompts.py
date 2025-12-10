"""
ChatPrompter - Manages different prompt templates for various response styles and types.

This module provides centralized prompt management for the TAI Tutor AI system.
It supports:
- Response Styles: Formal, Casual, Technical
- Response Types: Direct, Hinting, Socratic
- Response Lengths: Short, Medium, Long
- Conversation History Context
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


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
        "formal": """You are a professional academic tutor. Use formal language, proper terminology, 
and maintain a structured, educational tone throughout your response. Address the student respectfully 
and provide well-organized explanations.""",
        
        "casual": """You are a friendly study buddy. Use conversational language, relatable examples, 
and a warm, approachable tone. Feel free to use casual expressions while still being helpful and accurate.""",
        
        "technical": """You are a technical expert and mentor. Use precise technical terminology, 
provide detailed technical explanations, include relevant code examples or technical specifications 
when appropriate, and focus on accuracy and depth."""
    }
    
    # Response Type Templates
    TYPE_TEMPLATES = {
        "direct": """Provide a direct, clear answer to the question. Give the complete solution 
or explanation without holding back information. Be comprehensive but concise.""",
        
        "hinting": """Guide the student toward the answer using hints and scaffolding. 
Do NOT give the direct answer immediately. Instead:
1. Acknowledge what they're trying to solve
2. Provide a helpful hint or point them in the right direction
3. Ask a guiding question to help them think through the problem
4. Only reveal more if they seem stuck after multiple attempts""",
        
        "socratic": """Use the Socratic method to help the student discover the answer themselves.
Instead of providing direct answers:
1. Ask thought-provoking questions
2. Challenge assumptions
3. Guide through logical reasoning
4. Help them arrive at understanding through dialogue
5. Celebrate their discoveries and encourage deeper exploration"""
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
    
    # Base System Prompt
    BASE_SYSTEM_PROMPT = """You are TAI Tutor AI, an intelligent educational assistant designed to help 
students learn programming concepts, computer science fundamentals, and related topics.

Your primary goals:
- Help students understand concepts deeply
- Encourage learning and curiosity
- Provide accurate, helpful information
- Adapt to the student's learning style and needs

When answering questions about code:
- Explain the logic, not just the syntax
- Point out common pitfalls
- Suggest best practices
- Use clear, readable code examples when appropriate
"""

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


# Convenience functions for quick prompt generation
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


# Default instances for common use cases
DEFAULT_PROMPTER = ChatPrompter()
HINT_PROMPTER = ChatPrompter(response_type="hinting")
SOCRATIC_PROMPTER = ChatPrompter(response_type="socratic")
