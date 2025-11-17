// Minimal local bot for demo. Replace with API call when available.
export const botService = {
  async respond(message) {
    const text = message.trim().toLowerCase();
    // Simple rule-based replies
    if (!text) return "I didn't get any text. Try asking a question.";
    if (text.includes('hello') || text.includes('hi')) return 'Hello! How can I help with your learning today?';
    if (text.includes('plan')) return 'You can create a new plan on the Home page using "Recreate new plan".';
    if (text.includes('help')) return 'Try asking me to explain a concept, give an example, or quiz you.';
    // fallback echo
    return `You said: "${message}" — (this is a local demo bot).`;
  }
};

export default botService;
