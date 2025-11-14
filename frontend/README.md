# TAI Tutor - React Chatbot Frontend

A modern React.js chatbot interface for interacting with Ollama AI models.

## Features

- 💬 Conversational chatbot interface
- 🤖 Dropdown selector for Ollama models
- 🚀 POST requests to Ollama API for AI responses
- ⌨️ Keyboard shortcuts (Enter to send, Shift+Enter for new line)
- 📱 Responsive design
- ✨ Real-time message loading indicator
- 🎨 Modern UI with gradient design

## Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- Ollama running locally on `localhost:11434`

## Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

## Running the Application

1. Make sure Ollama is running:
   ```bash
   ollama serve
   ```
   Or on Windows, run the Ollama desktop application.

2. In a new terminal, start the React development server:
   ```bash
   npm start
   ```

3. The application will open in your browser at `http://localhost:3000`

## Usage

1. **Select a Model**: Use the dropdown in the header to select an Ollama model (e.g., llama2, mistral)
2. **Refresh Models**: Click the refresh button to reload available models from Ollama
3. **Send Message**: Type your question and click "Send" or press Enter
4. **Multi-line Input**: Use Shift+Enter to add line breaks in the input

## Project Structure

```
frontend/
├── public/
│   └── index.html          # Main HTML file
├── src/
│   ├── components/
│   │   └── ChatbotInterface.js    # Main chatbot component
│   ├── styles/
│   │   └── ChatbotInterface.css   # Component styles
│   ├── App.js              # Root app component
│   ├── App.css             # App styles
│   ├── index.js            # React entry point
│   └── index.css           # Global styles
└── package.json            # Project dependencies
```

## API Endpoints

### Get Available Models
```
GET http://localhost:11434/api/tags
```

### Generate Response
```
POST http://localhost:11434/api/generate
Content-Type: application/json

{
  "model": "llama2",
  "prompt": "Your question here",
  "stream": false
}
```

## Customization

### Changing the API URL
Update the base URL in `ChatbotInterface.js` if Ollama is running on a different address:

```javascript
const response = await fetch('http://your-api-url:11434/api/generate', {
  // ...
});
```

### Styling
All component styles are in `src/styles/ChatbotInterface.css`. Modify colors, sizes, and animations there.

### Adding More Features
- Add message persistence with localStorage
- Implement conversation history/threading
- Add typing indicators with streaming responses
- Integrate with different AI backends

## Troubleshooting

### "Error: fetch failed" or "Cannot connect to Ollama"
- Ensure Ollama is running on `localhost:11434`
- Check that your firewall allows local connections
- Verify CORS headers if accessing from different origin

### Models not loading
- Click the refresh button to reload models
- Check Ollama logs for errors
- Ensure Ollama has models installed (`ollama pull llama2`)

### No response from AI
- Check that selected model is installed (`ollama list`)
- Verify Ollama service is running properly
- Check browser console for detailed error messages

## Available Scripts

- `npm start` - Run development server
- `npm build` - Build for production
- `npm test` - Run tests
- `npm eject` - Eject from Create React App (not recommended)

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

MIT License - Feel free to use this project for your needs.

## Support

For issues with the frontend, check the browser console for errors. For Ollama-related issues, visit https://ollama.ai
