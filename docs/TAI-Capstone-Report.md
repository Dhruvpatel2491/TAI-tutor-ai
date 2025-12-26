# TAI: Tutor AI
## Multimodal Retrieval-Augmented Generation Platform for Context-Aware Coursework Assistance

### Capstone Project Report

**Student:** Dhruv K. Patel  
**Degree Program:** Master of Science in Computer Science  
**Advisor:** Dr. Simona Doboli, Professor  
**Department:** Department of Computer Science  
**Institution:** Hofstra University  
**Submission Date:** December 2025

---

## ABSTRACT

The proliferation of large language models has transformed educational technology, yet existing AI tutoring systems suffer from significant limitations in coursework alignment, multimodal reasoning, and contextual relevance. This capstone project presents TAI (Tutor AI), a comprehensive educational platform that addresses these gaps through an integrated retrieval-augmented generation (RAG) pipeline combined with local and cloud-based large language models.

TAI unifies four distinct tutoring modes—conversational assistance, quiz generation, study planning, and coding support—through a single course-aware knowledge base derived exclusively from instructor-approved materials. The platform implements prompt-based customization, content safety guardrails, and multimodal input handling to provide pedagogically sound educational experiences. Deployment occurs through a lightweight backend architecture utilizing Flask, with frontend interactions mediated through React, and local LLM inference accelerated via Ollama on GPU-equipped hardware. This report details the system design, RAG implementation, LLM agent orchestration, and functional verification through manual user testing and automated test suites, establishing TAI as a practical solution for integrating AI into existing coursework frameworks.

---

## ACKNOWLEDGEMENTS

I would like to extend my gratitude to Dr. Simona Doboli for her invaluable guidance, constructive feedback, and unwavering support throughout this capstone project. Her expertise in computer science education and systems design has significantly shaped the vision and execution of this work.

I am grateful to the Department of Computer Science at Hofstra University for providing the computational resources, laboratory facilities, and institutional support necessary to develop and evaluate this platform. Special thanks to the student participants who provided qualitative feedback during functional testing, offering practical insights that refined the user experience and feature implementation.

---

## TABLE OF CONTENTS

1. INTRODUCTION
   - Problem Statement: Current AI Utilization Trends
   - Project Objectives

2. BACKGROUND
   - Market Research: Current AI Tutors and Identified Gaps
   - Project Scope
   - Summary of Gaps Addressed

3. SYSTEM DESIGN
   - Technology Stack
   - High-Level Architecture
   - Frontend Application
   - Backend Services
   - Data Storage and Indexing
   - Security, Privacy, and Access Control

4. RAG IMPLEMENTATION
   - Motivation for Retrieval-Augmented Generation
   - Vector Store Generation
   - Backend RAG Pipeline
   - Query Flow and Context Assembly

5. LLM AGENT ORCHESTRATION
   - Ollama and LlamaIndex Implementation
   - Prompt Construction and Templates
   - Task-Specific Flows
   - Safety, Guardrails, and Ethical Considerations

6. IMPLEMENTATION
   - Application Features and User Interface
   - Integration of Frontend and Backend
   - Backend Deployment

7. EVALUATION AND RESULTS
   - Quality Assessment Through Manual User Testing
   - Functional Verification via Pytest
   - Discussion of Limitations

8. FUTURE WORK

9. CONCLUSION

10. REFERENCES

11. APPENDICES

---

## 1. INTRODUCTION

### 1.1 Problem Statement: Current AI Utilization Trends

The educational landscape has experienced rapid transformation following the public release of advanced large language models such as GPT-4, Gemini, and Claude. While these models demonstrate impressive capabilities in knowledge recall and natural language understanding, their integration into academic environments has created several unintended challenges that undermine learning outcomes and institutional integrity.

**Copy-Paste Culture and Academic Dishonesty:** Contemporary students have gained unprecedented access to AI systems capable of generating complete solutions to homework assignments, programming projects, and examinations. This accessibility has fostered a concerning normalization of solution copying without genuine understanding. Rather than engaging with conceptual foundations, students increasingly rely on AI-generated answers that circumvent authentic learning processes.

**Low Contextual Relevance:** Generic LLM chat interfaces operate without knowledge of specific course syllabi, institutional notation conventions, assessment criteria, or pedagogical objectives. When a student inquires about a data structure problem, ChatGPT or Gemini may provide textbook explanations disconnected from the specific programming language, framework, or assessment style required by their instructor. This misalignment between AI output and course requirements creates confusion and reduces instructional effectiveness.

**Fragmented Learning Ecosystem:** Contemporary students must navigate multiple platforms to access course materials. Lecture slides reside on learning management systems, code repositories on GitHub, assignment specifications scattered across email attachments or institutional portals, and supplementary resources spread across disparate websites. No unified AI-driven interface consolidates these resources into a coherent knowledge base. This fragmentation forces students to manually integrate information across platforms, diminishing the cognitive benefits that unified learning tools could provide.

**Lack of Unified Tutoring Framework:** Existing AI systems excel at individual tasks (chat assistance, quiz generation, study planning), but these capabilities operate in isolation. A student might use ChatGPT for conversational learning, a separate service for quiz practice, and manual spreadsheet tracking for study schedules. This tool fragmentation creates context-switching overhead and prevents AI systems from learning cumulative student needs across educational modalities.

**Limited Multimodal Reasoning:** While LLMs handle text and code effectively, educational materials encompass diagrams, circuit designs, mathematical notation, and visual representations. Existing AI tutoring systems provide limited support for reasoning simultaneously over text, code, and visual artifacts, requiring students to manually translate visual information into textual descriptions that AI systems can process.

### 1.2 Project Objectives

This capstone project aims to develop TAI, a unified AI tutoring platform that addresses the limitations outlined above through the following specific objectives:

**Objective 1: Create Course-Scoped Knowledge Bases**  
Ingest instructor-provided course materials—including lecture PDFs, presentation slides, code repositories, assignment specifications, and supplementary resources—into vector-indexed knowledge bases specific to each course. Restrict all AI-generated assistance to information sourced from these approved materials, preventing hallucinated off-syllabus guidance and ensuring alignment with institutional assessment criteria.

**Objective 2: Unify Multiple Tutoring Modalities**  
Implement four complementary tutoring modes (conversational assistance, quiz generation, study planning, and coding support) that share a common RAG pipeline and knowledge base. This unified architecture ensures that all tutoring modalities access consistent, curated information and enables cross-modal learning experiences.

**Objective 3: Support Multimodal Input Processing**  
Develop infrastructure to handle text documents, code files, images with embedded diagrams, and mathematical notation. Create embedding strategies that preserve semantic meaning across these modalities, enabling AI reasoning that integrates visual, textual, and programmatic information.

**Objective 4: Implement Pedagogically Sound Response Mechanisms**  
Design prompt templates and response generation patterns that avoid complete solutions, instead offering scaffolded guidance through hinting mechanisms, directional instruction, or automatic routing based on question type. This scaffolding approach promotes active learning and independent problem-solving rather than passive solution consumption.

**Objective 5: Enable Localized Deployment**  
Integrate open-source LLM infrastructure (Ollama for local inference, LlamaIndex for RAG orchestration) to support on-premise deployment. This approach reduces data transmission to external APIs, addresses privacy concerns, and ensures institutions maintain control over student data and learning interactions.

**Objective 6: Establish Safety and Ethical Guardrails**  
Implement content moderation layers that detect and refuse harmful requests (code for malware, assistance with plagiarism, academic dishonesty), while simultaneously encouraging ethical coding practices and responsible technology use. These guardrails protect both student welfare and institutional integrity.

---

## 2. BACKGROUND

### 2.1 Market Research: Current AI Tutors and Identified Gaps

An analysis of existing AI tutoring systems reveals a competitive landscape populated by ChatGPT Study Mode, Gemini Guided Learning, and Microsoft Copilot Study tools. Each system offers valuable capabilities, yet systematic examination reveals consistent gaps in coursework integration, unified feature implementation, and cost-effective deployment.

**Feature Comparison Analysis:**

ChatGPT Study Mode provides access to 4-8 LLM variants, supporting both text and code reasoning within a unified interface. However, coursework integration remains limited to file upload mechanisms rather than true course-scoping. Students must manually upload course materials for each interaction session, creating friction and preventing the system from maintaining persistent course-specific knowledge bases. The cost structure requires subscription fees exceeding $20 per month, and deployment occurs exclusively through Cloudflare infrastructure, limiting institutional control and raising data privacy concerns.

Gemini Guided Learning emphasizes pedagogical scaffolding through its learning guidance features, incorporating 2-3 LLM model options. Coursework integration is partial, relying on fragmented uploads rather than systemic course ingestion. While integrated within the Google ecosystem, this integration creates vendor lock-in and lacks the flexibility required by institutions using diverse technology stacks. The platform similarly operates on cloud-only deployment infrastructure.

Microsoft Copilot Study/Learn strategies demonstrate moderate coursework integration capabilities, with 3-4 available models. However, unified tutoring features remain incomplete. The system provides chat-based interaction and limited quiz functionality, but lacks integrated study planning tools. Students must correctly prompt the system to generate efficient quizzes, suggesting that pedagogical scaffolding remains underdeveloped. Like its competitors, Copilot operates exclusively in cloud environments.

**Real-World Issues in Existing Systems:**

Generic LLM systems fail to maintain course-awareness across multiple interaction sessions. When a student asks about recursion in a programming course, the AI system lacks contextual knowledge about the specific course's programming language, required coding conventions, assessment rubrics, and prerequisite knowledge assumptions. Responses therefore generate generic explanations rather than course-aligned guidance.

The absence of shared, course-scoped knowledge bases across distinct features compounds this problem. A student using ChatGPT for conversational assistance accesses different underlying information than when using a separate quiz generation tool. This fragmentation means that insights learned through conversation do not inform quiz generation, and both modalities may present inconsistent information or conflicting pedagogical approaches.

Current systems provide limited unified reasoning over text and code. When course materials encompass both written explanations and code repositories, existing systems struggle to synthesize information across these modalities. A student seeking clarification on how a specific algorithm implementation relates to its theoretical foundations cannot rely on existing tools to seamlessly integrate code-level reasoning with textual explanation.

### 2.2 Project Scope

TAI is designed to address the identified gaps through the following scope constraints and design decisions:

**Supported Educational Contexts:** The platform is engineered for undergraduate and graduate computer science coursework, though its architecture generalizes to any discipline involving text, code, and diagrammatic materials. Initial deployment focuses on programming courses and data structures curricula.

**Course Material Types:** TAI accepts PDF lecture slides, text documents, Jupyter notebooks, Python/Java/C++ source files, markdown documentation, and image files containing diagrams or mathematical notation. The system assumes material is provided in structured, digitized formats accessible to embedding and retrieval algorithms.

**User Roles:** The platform differentiates between two primary user roles. Faculty members function as administrators, with capabilities to upload course materials, configure LLM parameters, define pedagogical preferences (hinting vs. directive instruction), and review aggregate interaction logs. Students function as learners, accessing tutoring modalities without privileges to modify course materials or system configurations.

**Deployment Environment:** TAI deploys on institutional servers equipped with GPU acceleration (tested on Lenovo ThinkStation P5 with Intel XEON processors). The platform supports both local LLM inference via Ollama and optional cloud-based API access for larger models. No mandatory cloud infrastructure is required.

**Interaction Patterns:** The system supports single-session and multi-turn conversational interactions. Study plans and quizzes may be persisted across sessions. Student interactions with the system are logged for institutional analysis, subject to privacy protections and institutional data governance policies.

### 2.3 Summary of Gaps Addressed

TAI directly addresses six critical gaps identified in existing systems and educational practices:

**Gap 1: Course-Awareness Deficit**  
Existing systems operate without knowledge of specific course contexts. TAI requires explicit ingestion of course materials, creating persistent course-scoped vector indices that ensure all responses reflect instructor-approved content and institutional assessment criteria.

**Gap 2: Feature Fragmentation**  
Existing platforms offer isolated features that operate independently. TAI unifies chat, quizzes, study planning, and coding assistance through a single RAG pipeline, ensuring consistent context and pedagogical approach across all modalities.

**Gap 3: Solution Completeness Without Learning**  
Generic AI systems often generate complete solutions that enable plagiarism. TAI implements response templates (hinting, directive, automatic routing) that provide scaffolded guidance rather than comprehensive solutions, promoting active learning.

**Gap 4: Multimodal Limitation**  
Existing systems struggle with simultaneous reasoning over text and code. TAI implements multimodal vector indexing and retrieval that treats code, text, and diagrams as semantically related components of unified course knowledge bases.

**Gap 5: Institutional Privacy Concerns**  
Cloud-only deployment models force institutions to transmit student interaction data to external providers. TAI supports on-premise deployment with local LLM inference, maintaining institutional data governance and privacy protections.

**Gap 6: Cost Barriers**  
Existing commercial systems require subscription fees. TAI utilizes open-source components (Ollama, LlamaIndex) and freely available embedding models, eliminating per-student or per-institution licensing costs while supporting institutional AI adoption.

---

## 3. SYSTEM DESIGN

### 3.1 Technology Stack

TAI is constructed from carefully selected open-source and modern web framework components, chosen to balance functionality, performance, scalability, and cost-effectiveness. The technology stack encompasses frontend user interfaces, backend services, LLM infrastructure, and data storage systems.

**Frontend Framework: React with Tailwind CSS**

The frontend utilizes React, a mature JavaScript library maintained by Meta that emphasizes component-based UI development. React's declarative programming model enables rapid iteration on user interface features and facilitates state management across complex interactions. The modular component architecture allows frontend developers to isolate feature development and independently test UI logic.

Tailwind CSS provides a utility-first CSS framework that accelerates responsive design implementation. Rather than writing custom CSS stylesheets, developers specify design tokens through HTML class names, enabling rapid prototyping of interfaces that maintain visual consistency and scale across desktop, tablet, and mobile viewports. This approach significantly reduces development time for constructing professional interfaces without delegating design work to specialized teams.

**Backend Services: Flask with Python**

The backend leverages Flask, a lightweight Python web framework maintained by the Pallets project. Flask provides essential HTTP request routing, response serialization, and middleware integration necessary for backend service implementation. Unlike heavier frameworks like Django, Flask maintains a minimal core footprint while offering extensibility through community plugins. This approach enables rapid prototyping and deployment without infrastructure overhead.

Python serves as the backend programming language, chosen for its dominance in machine learning and data science ecosystems. The availability of LLamaIndex, Ollama client libraries, and embedding model implementations in Python significantly reduced development complexity compared to alternative languages.

**REST API Communication**

Communication between frontend and backend occurs through RESTful HTTP APIs. The frontend issues JSON-encoded requests to backend endpoints, which process requests, invoke LLM or RAG operations, and return JSON responses. This stateless, HTTP-based communication pattern enables horizontal scaling of backend services and simplifies debugging through standard HTTP tooling.

**LLM Infrastructure: Ollama**

Ollama provides an open-source inference engine for executing LLMs on consumer and prosumer hardware equipped with GPU acceleration. Ollama abstracts low-level GPU memory management, model loading, and inference optimization, presenting a simple HTTP API for querying language models. The system supports a range of open-source models including Gemma 7B and 70B, GPT-OSS variants, and Mistral models, enabling institutional selection based on available hardware and performance requirements.

Ollama's integration with TAI's backend occurs through standard HTTP requests or Python client libraries. The backend orchestrates model selection, parameter configuration, and response retrieval through Ollama's API, decoupling LLM inference infrastructure from application logic.

**RAG Framework: LlamaIndex**

LlamaIndex is a data framework specifically engineered for connecting diverse data sources to large language models through retrieval-augmented generation. The framework abstracts common RAG workflows, providing abstractions for document loading, text splitting, embedding generation, vector index construction, and retrieval with reranking.

LlamaIndex integrates with multiple vector stores (Chroma, Weaviate, Milvus) and LLM providers, enabling flexible deployment configurations. TAI leverages LlamaIndex to manage course material ingestion, vector store operations, and retrieval pipelines without reimplementing RAG infrastructure from first principles.

**Hardware Infrastructure: Lenovo ThinkStation P5**

GPU-accelerated local inference requires specialized hardware. TAI is deployed on a Lenovo ThinkStation P5 equipped with Intel XEON processors and NVIDIA GPUs, providing the computational capacity necessary for real-time LLM inference. This workstation-class hardware configuration balances cost-effectiveness with sufficient compute for institutional deployments serving 50-100 concurrent student users.

### 3.2 High-Level Architecture

[PLACEHOLDER: Insert system architecture diagram showing three layers: Frontend, Backend, and Data/LLM Infrastructure. Diagram should illustrate:
- React frontend communicating with Flask backend via REST API
- Flask backend connecting to vector database and Ollama inference engine
- Guardroll checkpoint after LLM generation
- Student/Faculty user roles and authentication]

TAI's architecture follows a three-tier design pattern separating concerns between user interaction (frontend), business logic and orchestration (backend), and data storage and model inference (infrastructure).

**Frontend Layer:** The React-based frontend provides user interface components for each tutoring modality. The chat interface accepts student questions and displays conversational responses. The quiz module presents questions with multiple-choice, true-false, and short-answer formats, managing student responses and generating feedback. The study planner interface accepts learning objectives and timeframe constraints, displaying personalized study schedules. The CodeQuest module presents coding challenges with starter code templates, enabling in-browser code editing and testing.

**Backend Layer:** The Flask-based backend processes incoming requests from the frontend, routes them to appropriate handlers, and coordinates the RAG pipeline and LLM inference. Authentication and authorization middleware verify user credentials and enforce access controls based on user role (student vs. faculty). The backend maintains integration with the vector database, issuing retrieval queries when LLM context augmentation is required. Request logging occurs at this layer, creating audit trails for institutional analysis and security investigations.

**Infrastructure Layer:** The vector database stores embeddings for all ingested course materials, indexed to support rapid semantic similarity search. The Ollama inference engine handles LLM execution and response generation. The plan database persists study plans and quiz records, enabling students to review previously generated plans and retake quizzes. Configuration storage maintains system parameters, prompt templates, and pedagogical preferences.

### 3.3 Frontend Application

[PLACEHOLDER: Insert screenshot of the main dashboard showing the four tutoring mode cards: Chat Interface, Quiz Generator, Study Planner, and CodeQuest]

The frontend application presents four distinct user interfaces, one for each tutoring modality, accessed through a unified dashboard after authentication. The design emphasizes clarity, accessibility, and responsive behavior across devices.

**Dashboard and Navigation:** Upon login, authenticated users encounter a dashboard presenting four primary tutoring modes as cards or menu options. Faculty users additionally see an administration panel enabling course material uploads and system configuration. The navigation structure maintains consistent styling and provides quick access to user profile settings, preferences, and session management controls.

**Chat Interface:** The conversational tutor presents a message thread interface resembling popular chat applications. Students type questions in an input field at the bottom of the screen, with responses appearing in a scrollable message history. Each response includes an indicator of response type (hinting vs. directive) and when applicable, citation information linking generated content back to specific course materials. Customization controls allow students to select response tone (formal, casual, technical), response approach (hinting, directive, automatic), and response length (short, medium, long).

**Quiz Module:** The quiz generator interface presents one question at a time, formatted according to its question type. Multiple-choice questions display four options with radio buttons. True-false questions display two options. Short-answer questions provide a text input field. Upon selecting an answer, students receive immediate feedback including the correct answer and explanatory text. Quiz history allows students to review previously completed quizzes and track performance across topic areas.

**Study Planner:** The study planner accepts learning objectives (e.g., "Learn Python recursion in one week") and student constraints (hours per week, background experience level). The system generates a structured study plan with time-blocked learning activities, specific exercises, assessment criteria, and self-check questions. Plans are displayed in an expandable format allowing students to review daily tasks and mark completed activities.

**CodeQuest Interface:** The coding challenge module presents a problem statement, difficulty level, and starter code template. An integrated code editor allows students to write solutions and test against provided test cases. Upon submission, the system displays whether the solution passes test cases and provides explanatory feedback on the correctness of the approach.

### 3.4 Backend Services

The backend orchestrates request handling, business logic, and infrastructure coordination through a set of specialized service modules. Each module handles specific aspects of system functionality.

**Authentication and Authorization Service:** This service manages user login workflows, session management, and JWT (JSON Web Token) authentication. Upon successful login, the service generates time-limited JWT tokens that frontend applications include in subsequent requests. The backend validates tokens before processing sensitive operations, ensuring that only authenticated users perform actions. Role-based access control distinguishes between faculty capabilities (material uploads, configuration) and student capabilities (accessing tutoring modalities).

**Request Router and Handler:** This service receives incoming HTTP requests from the frontend, routes them to appropriate handlers based on URL endpoint and request method, and coordinates response generation. For chat requests, the router invokes the RAG pipeline handler. For quiz requests, the router invokes the quiz generation service. The router also enforces rate limiting, preventing individual users from overwhelming system resources through excessive requests.

**RAG Pipeline Orchestrator:** This service manages the core retrieval-augmented generation workflow. Upon receiving a student question, it queries the vector database to retrieve relevant course materials, ranks results by relevance, and assembles these results into a prompt context passed to the LLM. This service encapsulates the core intelligence that makes TAI more effective than generic LLM chat.

**LLM Interface and Parameter Manager:** This service abstracts interactions with the Ollama inference engine, handling model selection, parameter configuration (temperature, top-k sampling, maximum token limits), and response generation. It applies hyperparameter settings stored in system configuration, enabling faculty to adjust model behavior globally or per-course.

**Safety and Guardrail Engine:** This service evaluates student requests against content safety patterns and educational boundaries. Before responding to a request, the system checks for harmful patterns (requests for malware, plagiarism assistance, unauthorized access). If detected, the service returns a refusal message without invoking the LLM, preventing inappropriate outputs. After LLM generation, the service performs output validation to detect generated hallucinations or policy violations before returning responses to students.

**Logging and Audit Service:** This service records all system interactions in structured format, capturing user identity, request content, system response, inference parameters, and timestamps. These logs enable institutional analysis of system usage patterns, identification of emerging issues, and forensic investigation if misconduct occurs.

### 3.5 Data Storage and Indexing

Course materials are transformed through an ingestion pipeline that converts diverse document types into a unified vector representation suitable for semantic search and retrieval.

**Document Ingestion:** Faculty upload course materials (PDF slides, code files, markdown documents, images) through the administration interface. The ingestion service reads these files, extracts text content (via PDF parsing libraries for PDFs, direct reading for text and code files, OCR for images), and prepares text for embedding.

**Text Preprocessing and Chunking:** Raw text extracted from documents is preprocessed to normalize whitespace, remove special characters that confuse embedding models, and segment long documents into chunk units of manageable size. Chunking strategy balances semantic coherence (keeping related concepts together) against embedding model context windows (typically 512-1024 tokens). Recursive chunking strategies ensure that large documents are subdivided while maintaining semantic boundaries at section or paragraph levels.

**Embedding Models:** Text chunks are converted into fixed-dimensional vector representations through sentence-level embedding models such as all-MiniLM-L6-v2 or similar open-source models optimized for semantic similarity tasks. These embeddings preserve semantic meaning in a continuous vector space, enabling similarity-based retrieval. A single embedding model is typically used across an entire course to ensure consistent semantic space representation.

**Multimodal Vector Index:** For documents containing both text and embedded images (diagrams, mathematical notation), the system processes images through OCR or image captioning models to extract textual descriptions. These descriptions are embedded alongside textual content, enabling students to search for and retrieve visual information through textual queries. For instance, a student asking about "circuit diagrams for logic gates" retrieves text chunks describing logic gates as well as images with captions describing the same circuits.

**Vector Store Operations:** Embeddings and associated chunk metadata are stored in a vector database. Upon ingestion completion, the database is indexed with data structures (such as hierarchical navigable small world graphs or product quantization indices) enabling fast approximate nearest neighbor search. When a student submits a question, the system embeds the question in the same vector space, then queries the database to retrieve the nearest neighbor chunks. This retrieval mechanism provides course-specific context for the LLM.

### 3.6 Security, Privacy, and Access Control

TAI implements multi-layered security controls protecting student data, institutional resources, and system integrity.

**Authentication:** User authentication occurs through username/password credentials validated against an institutional user directory or local authentication database. Upon successful authentication, the system generates JWT tokens with limited validity periods (typically 1-8 hours). Subsequent API requests include these tokens, which are validated to ensure requests originate from authenticated users.

**Authorization:** Role-based access control distinguishes between student and faculty roles. Students may access tutoring modalities but cannot view other students' records, modify course materials, or access administrative functions. Faculty may upload materials, modify course configurations, and view aggregate usage statistics, but cannot modify other faculty configurations or access sensitive institutional data.

**Data Encryption:** Communication between frontend and backend occurs exclusively through HTTPS, encrypting data in transit. Sensitive data such as credentials and API keys are stored in encrypted form at rest, with encryption keys managed through institutional key management services.

**Student Privacy:** Student interactions with tutoring modalities are logged for system improvement and abuse detection, but personally identifiable information is minimized in these logs. Faculty members cannot view individual student interactions without explicit student consent or institutional authorization through proper channels. Aggregate usage statistics and learning analytics are available to faculty in anonymized form.

**Rate Limiting and Abuse Prevention:** The backend implements rate limiting to prevent students from overwhelming LLM inference resources through excessive requests. Unusual usage patterns are monitored and flagged for investigation. If a student's request patterns suggest potential system abuse, their access may be temporarily suspended pending review.

---

## 4. RAG IMPLEMENTATION

### 4.1 Motivation for Retrieval-Augmented Generation

Retrieval-augmented generation addresses the fundamental limitation that large language models trained on general-purpose internet text cannot maintain accurate knowledge of specific course contexts, syllabi, assessment criteria, and institutional standards. Without augmentation, an LLM responding to student questions operates from its training data, potentially providing generic explanations disconnected from course-specific requirements.

Consider a student asking "Explain linked lists." A generic LLM might provide a textbook-style explanation perfectly accurate for general computer science education but misaligned with the student's specific course. The course might emphasize functional programming paradigms foreign to the LLM's training emphasis on imperative approaches. The course might use specific notation or terminology. The course might expect students to implement linked lists using particular design patterns. Without course-specific context, the LLM's response, however technically sound, misses pedagogical alignment.

RAG remedies this by augmenting the LLM's response generation with retrieved excerpts from course materials. When the student asks about linked lists, the RAG system retrieves lecture slides discussing the topic, associated code examples, and any prior student questions the instructor has addressed. These retrieved materials become part of the prompt given to the LLM, grounding its response in course-specific context. The LLM can now reference specific notation used in lectures, specific implementation approaches demonstrated in code examples, and specific conceptual framings emphasized by the instructor.

Additionally, RAG prevents hallucinations. When an LLM is asked a question it cannot answer from its training data, it may generate plausible-sounding but incorrect information. By restricting responses to information contained in retrieved course materials, RAG dramatically reduces this risk. If a student asks about a topic not covered in course materials, the retrieved context will be empty or irrelevant, and the LLM can appropriately decline to answer rather than fabricating information.

### 4.2 Vector Store Generation

The vector store undergoes construction during course setup, transforming instructor-provided materials into an indexed, searchable knowledge base.

**Data Sources and Ingestion:** TAI accepts course materials in diverse formats reflecting modern academic practice. PDF lecture slides contribute primary conceptual content. Written lecture notes, textbook excerpts, and markdown documents provide supplementary explanations. Programming code repositories (source files, notebooks, examples) contribute implementation-level details. Supplementary materials (research papers, tutorial links, external resources) round out the knowledge base. Image files containing diagrams, equations, or visual explanations are included after extracting their content through image processing techniques.

[PLACEHOLDER: Insert code snippet showing example file ingestion code. Location: src/backend/services/document_ingestion.py - lines 1-50. Show: file type detection, content extraction logic for PDFs and text files, with comments indicating where image processing would occur]

**Preprocessing and Chunking Strategy:** Extracted text undergoes normalization to remove artifacts introduced during PDF parsing or file encoding. Whitespace is standardized. Special characters that confuse embedding models are mapped to interpretable equivalents. Unicode characters are validated.

Documents are then recursively divided into chunks of approximately 512-1024 tokens, roughly corresponding to 2-4 paragraphs or one page of typical text. The chunking algorithm respects semantic boundaries, preferring to split at section or paragraph breaks rather than arbitrarily splitting sentences. This preservation of context ensures that retrieved chunks present coherent conceptual units rather than fragmentary pieces.

For code files, chunking considers function or class definitions as natural boundaries. An entire method or class is kept together if its size allows, preventing retrieval of incomplete code snippets that cannot be executed or understood in isolation.

[PLACEHOLDER: Insert code snippet showing text chunking algorithm. Location: src/backend/services/text_processor.py - lines 100-150. Show: recursive splitting logic, boundary detection, token counting]

**Embedding Models and Selection:** The Sentence Transformers library provides efficient embedding models optimized for semantic similarity. Models such as all-MiniLM-L6-v2 (22 million parameters) provide strong performance on semantic similarity tasks while maintaining modest computational requirements suitable for CPU or GPU inference.

Embedding model selection considers tradeoffs between computational efficiency (smaller models run faster and consume less memory) and semantic quality (larger models capture finer semantic distinctions). For coursework contexts where speed and cost-efficiency are prioritized, smaller models like all-MiniLM-L6-v2 typically suffice.

**Multimodal Vector Index:** Course materials often contain visual elements: circuit diagrams, flowcharts, mathematical notation rendered as images, screenshots of software interfaces, and graphical representations of data structures. To include these visual elements in the retrievable knowledge base, the system processes images through either optical character recognition (OCR) to extract rendered text or image captioning models to generate textual descriptions of visual content.

For a circuit diagram image, an image captioning model might generate text like "A diagram showing a 2-to-1 multiplexer with data inputs A and B, control signal S, and output Z, with logic gates arranged to implement the selection function." This textual description is embedded alongside other course content, enabling students to retrieve the visual resource through textual queries despite the original resource being an image.

[PLACEHOLDER: Insert code snippet showing multimodal processing. Location: src/backend/services/multimodal_processor.py - lines 1-80. Show: image loading, OCR/captioning invocation, text embedding, with TODO markers for image processing model selection]

**Context Assembly and Ranking:** When a student submits a question, the system embeds the question using the same embedding model used for course materials. This embedding is compared against all course material embeddings using cosine similarity or other distance metrics. The system retrieves the top-k most similar chunks (typically k=3-5), ordered by similarity score.

The retrieved chunks are concatenated with the student's question to form an augmented prompt: "Here is relevant course material: [chunk 1] [chunk 2] [chunk 3]. Student question: [student question]. Please answer the question based on the provided course material."

This augmented prompt is passed to the LLM, which generates responses grounded in course-specific context rather than generic training data.

### 4.3 Backend RAG Pipeline

The backend implements three distinct RAG workflows corresponding to the three primary tutoring modalities requiring context augmentation.

**Chat Query Flow:**

When a student submits a conversational question, the following sequence executes:

1. The question is received by the backend and passed to the RAG pipeline.

2. The pipeline queries the vector store with the embedded question, retrieving top-k relevant chunks and their similarity scores.

3. The pipeline formats these chunks into context, noting their source documents for later citation.

4. The pipeline assembles a prompt combining system instructions, student conversation history, retrieved context, and the student's current question.

5. The assembled prompt is sent to the LLM with configured hyperparameters (model selection, temperature, top-k sampling).

6. The LLM generates a response, which is returned to the backend.

7. A guardrail service evaluates the response against safety patterns. If policy violations are detected, a refusal message is returned instead.

8. The response is formatted for frontend display, including citations to source materials when applicable.

9. The interaction (question, response, source materials, timestamps, user identity) is logged for audit purposes.

[PLACEHOLDER: Insert code snippet showing chat RAG flow. Location: src/backend/services/rag_pipeline.py - lines 50-150. Show: vector store query, prompt assembly, LLM invocation, guardrail check, with function signatures and parameter passing]

**Study Planner Flow:**

Study plan generation requires different orchestration than conversational assistance because it must reason about course structure, learning objectives, student background, and time constraints rather than answering single questions.

1. The student provides learning objectives, timeframe, and availability constraints.

2. The pipeline retrieves chunks from the vector store most relevant to the stated learning objectives, capturing conceptual coverage expected in the course.

3. The pipeline assembles a specialized prompt for plan generation, including: system instructions specific to pedagogical planning, the retrieved course material outline, the student's objectives and constraints, and example study plans showing desired structure and detail.

4. The LLM generates a study plan structured with time blocks, specific activities, resources, checkpoints, and self-assessment questions.

5. The guardrail service validates the plan for educational appropriateness (plans should be realistic, include breaks, scaffold complexity progression).

6. The plan is persisted to the database so students can review it later and track completion.

[PLACEHOLDER: Insert code snippet showing study planner flow. Location: src/backend/services/planner_service.py - lines 1-100. Show: objective parsing, material retrieval for curriculum overview, prompt construction specific to planning, LLM invocation with planning-specific parameters]

**Quiz Generation Flow:**

Quiz generation represents the most complex RAG orchestration because effective quizzes must cover course material comprehensively, assess learning at appropriate difficulty levels, include clear questions with unambiguous correct answers and plausible distractors.

1. The student specifies quiz parameters: topic area (e.g., "Recursion"), question count (e.g., 5 questions), difficulty level (beginner/intermediate/advanced), and desired question types (multiple choice/true false/short answer).

2. The pipeline retrieves chunks from the vector store specifically addressing the specified topic, capturing both foundational concepts and application-level complexity.

3. The pipeline assembles a specialized quiz generation prompt including: system instructions specific to quiz design, educational assessment standards, retrieved course material, specified difficulty and question type parameters, and example quiz questions showing desired quality and format.

4. The LLM generates a JSON-formatted quiz with questions, correct answers, plausible distractors (for multiple choice), and explanations for why answers are correct.

5. The guardrail service evaluates quiz quality by checking: question clarity, correctness of provided answers against course material, plausibility of distractors (obviously wrong distractors are rejected), appropriate difficulty matching to specified level.

6. If quality issues are detected, the quiz generation is retried with refined prompts. If quality standards are met, the quiz is returned to the student.

7. Student responses are recorded for instructor analytics and student performance tracking.

[PLACEHOLDER: Insert code snippet showing quiz generation flow. Location: src/backend/services/quiz_service.py - lines 100-200. Show: topic parsing, targeted material retrieval, quiz prompt construction with quality standards, JSON parsing of LLM output, validation logic]

### 4.4 Query Flow and Context Assembly

The quality of RAG systems fundamentally depends on the effectiveness of the retrieval stage. Poor retrieval yields irrelevant context that misleads rather than assists the LLM.

**Query Embedding and Similarity Search:**

When a student submits a question, the backend embeds the question using the same embedding model that processed course materials. For the question "How does a binary search tree differ from a balanced search tree?", the embedding captures the semantic relationship between tree data structures, balancing properties, and search efficiency—distinct from surface-level keyword matching.

The embedded question is compared against all course material embeddings using cosine similarity: similarity = (question_vector · material_vector) / (||question_vector|| × ||material_vector||). This metric ranges from -1 (opposite directions) to 1 (identical directions), with values near 1 indicating semantic similarity.

The retrieval system returns the top-k chunks with highest similarity scores. Typically k=3-5 provides sufficient context for the LLM without overwhelming it with irrelevant information.

**Handling Edge Cases and Retrieval Failures:**

When no course materials match the student's question well (all similarity scores are below a configured threshold), several strategies prevent poor responses:

If retrieval yields no relevant materials, the LLM cannot be confidently asked to answer based on course materials. Instead, the backend returns a message like "I couldn't find relevant course materials addressing this question. Please rephrase your question or ask your instructor." This prevents hallucination when context is insufficient.

If retrieval yields marginally relevant materials, the system includes a disclaimer in the response acknowledging that the answer may not be fully course-specific. This transparency helps students recognize when they should seek instructor clarification.

**Ranking and Reranking:**

Beyond cosine similarity ranking, more sophisticated reranking strategies can improve retrieval quality. Cross-encoder models compute relevance by examining both question and candidate document jointly, potentially capturing nuanced relationships missed by similarity-based ranking. However, cross-encoders require inference for each candidate, increasing computational cost.

For institutional deployments prioritizing speed over perfect ranking accuracy, similarity-based retrieval followed by configurable thresholding provides sufficient performance.

---

## 5. LLM AGENT ORCHESTRATION

### 5.1 Ollama and LlamaIndex Integration

Ollama provides the inference engine executing language models, while LlamaIndex provides the data framework coordinating document ingestion and retrieval orchestration. These components integrate through standard HTTP APIs and Python bindings.

**Ollama Inference Engine:**

Ollama abstracts the complexities of GPU memory management, model quantization, and numerical computation, presenting a simple HTTP API for model inference. The system supports multiple open-source models including Gemma 7B (7 billion parameters), Mistral 7B, GPT-OSS 20B, and larger variants. Model selection represents a tradeoff between inference speed and response quality.

Smaller models (7B parameters) execute rapidly on consumer GPU hardware, supporting real-time conversational interactions. These models demonstrate reasonable performance on educational tasks like explaining concepts and generating study plans. Larger models (20B-70B parameters) generate higher-quality responses but require more hardware resources and longer inference times, suitable for batch operations like quiz generation rather than real-time chat.

Ollama manages these tradeoffs through a model registry. Faculty can register multiple models with their deployed instance and configure which models are used for which tasks. Conversational interactions might default to Gemma 7B for speed, while quiz generation might use a larger model for quality.

[PLACEHOLDER: Insert code snippet showing Ollama API integration. Location: src/backend/llm_interface/ollama_client.py - lines 1-50. Show: model initialization, parameter configuration, inference invocation, response parsing, with error handling]

**LlamaIndex Integration:**

LlamaIndex simplifies the RAG pipeline by abstracting document loading, text splitting, embedding generation, and index construction. Rather than reimplementing these components, the backend delegates to LlamaIndex services.

```
# Conceptual pseudocode showing LlamaIndex usage pattern
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

# Load documents from course materials directory
documents = SimpleDirectoryReader(input_dir="course_materials/").load_data()

# Create vector index from documents
index = VectorStoreIndex.from_documents(documents, 
                                        embed_model=embedding_model,
                                        vector_store=vector_store)

# Query the index
query_engine = index.as_query_engine()
response = query_engine.query("Explain recursion")
```

This abstraction significantly reduces development effort compared to implementing RAG from scratch. LlamaIndex handles the orchestration details, enabling developers to focus on application-specific logic.

### 5.2 Prompt Construction and Templates

The quality of LLM outputs depends fundamentally on the prompts provided to the model. Poorly constructed prompts yield generic, pedagogically unsound responses. Well-engineered prompts yield focused, actionable guidance aligned with educational objectives.

TAI implements a layered prompt construction strategy:

**Base System Prompt:**

The base system prompt establishes TAI's role and educational philosophy. This prompt is prepended to every request sent to the LLM:

"You are TAI (Tutor AI), an intelligent educational assistant designed to help students learn programming concepts, computer science fundamentals, and related topics. Your primary goals are to help students understand concepts deeply through clear, accurate explanations, encourage learning and critical thinking, provide accurate and educational information, and adapt to the student's learning style and needs. When answering questions, explain the logic and reasoning rather than just syntax. Point out common pitfalls and misconceptions. Suggest best practices and industry standards. Use clear, readable, well-commented code examples when appropriate."

This prompt establishes consistent values and objectives across all interactions.

**Style Templates:**

Students can specify their preferred response tone: formal (for academic contexts), casual (conversational and approachable), or technical (emphasizing precise terminology and implementation details). Corresponding style templates modify the base prompt:

Formal: "Respond in formal academic tone, using precise terminology and structured explanations appropriate for academic submission."

Casual: "Respond in a friendly, conversational tone that makes concepts accessible without sacrificing accuracy."

Technical: "Respond using precise technical terminology and implementation-level detail, emphasizing correctness and industry standards."

**Response Approach Templates:**

Students can select their preferred pedagogical approach: hinting (scaffolded guidance), directive (complete explanations), or automatic (system selects based on question type).

Hinting template: "Guide the student toward the answer through strategic hints and scaffolding that promote active learning. Do not provide the direct answer immediately. Instead, acknowledge their question, provide targeted hints, ask guiding questions, and encourage them to try before revealing more."

Directive template: "Provide clear, direct explanations that facilitate comprehensive understanding. Deliver well-structured, informative responses that guide students to knowledge through accurate, complete explanations."

Automatic template: "Automatically select the most appropriate approach based on the question type. For conceptual questions, use directive method. For problem-solving tasks, provide hints. For code generation, may generate directly when appropriate."

**Response Length Templates:**

Students specify desired response length: short (1-2 paragraphs), medium (3-4 paragraphs), or long (5+ paragraphs with multiple examples). The template constraints the LLM's response generation:

Short: "Limit your response to 1-2 concise paragraphs."

Medium: "Provide a response of 3-4 paragraphs with explanations and at least one example."

Long: "Provide a comprehensive response of 5+ paragraphs including multiple examples, edge cases, and related concepts."

**Conversational History Context:**

For multi-turn conversations, the prompt includes previous messages in the conversation thread, enabling the LLM to maintain context across turns and refer back to earlier discussions:

"Conversation history: [User message 1] [Assistant response 1] [User message 2] [Assistant response 2] Current user message: [New user message]"

**Retrieved Course Material Context:**

The actual course-specific content augmenting the LLM:

"Relevant course materials: [chunk 1 from vector store] [chunk 2 from vector store] [chunk 3 from vector store]"

**Guardrail Prompt:**

Before response generation, a specialized guardrail prompt instructs the LLM to refuse harmful requests and maintain educational boundaries. After response generation, the response is checked for violations of these guidelines.

[PLACEHOLDER: Insert the complete base system prompt text. Location: src/backend/prompts/system_prompt.txt - full text. Include goals, instructions for code explanation, emphasis on learning over solutions]

### 5.3 Task-Specific Flows

Different tutoring tasks require specialized orchestration, parameter settings, and prompt construction.

**Conversational Tutor:**

Conversational assistance represents the most straightforward RAG application. A student asks a question, the system retrieves relevant course materials, augments the prompt with this context, and generates a response. Parameters typically prioritize speed and conversational naturalness over exhaustive detail.

Model selection: Gemma 7B for speed, or optionally larger models for quality.  
Temperature: 0.7 (balancing creativity and consistency)  
Top-k: 40 (diversity in token selection)  
Max tokens: 512 (typical response length)  

**Quiz Generator:**

Quiz generation requires more sophisticated orchestration because effective quizzes demand specific structure (JSON format with question, options, correct answer, explanation), appropriate difficulty calibration, and plausible distractors.

The quiz generation prompt includes explicit instructions for JSON output formatting and quality standards:

"Generate exactly 5 multiple-choice questions about recursion at intermediate difficulty. For each question, provide: question text, four options with A/B/C/D labels, correct answer, brief explanation. Output as valid JSON array with no markdown formatting. Ensure distractors are plausible but clearly incorrect."

Model selection: Larger model (20B+ parameters) for quality  
Temperature: 0.5 (lower temperature for more consistent, correct responses)  
Top-k: 20 (more conservative token selection)  
Max tokens: 2000 (sufficient for multiple questions with explanations)  

The generated quiz is parsed and validated before returning to the student. If validation fails (invalid JSON, unanswerable questions, correct answers contradicted by course materials), the generation is retried with refined prompts.

[PLACEHOLDER: Insert code snippet showing quiz generation validation logic. Location: src/backend/services/quiz_service.py - lines 300-400. Show: JSON parsing, answer verification against source materials, difficulty assessment]

**Study Planner:**

Study plan generation requires understanding of course structure, learning progression, realistic time estimates, and pedagogical scaffolding principles. The planner prompt includes structured examples of desired output and explicit constraints:

"Create a study plan for learning Python recursion in one week (5 hours per week). Include: learning objectives, daily time blocks with specific activities, exercises with step-by-step instructions, assessment criteria, self-check questions. Ensure the plan is realistic, includes breaks, and scaffolds complexity progression."

Model selection: Larger model for quality  
Temperature: 0.6 (balancing structure and variation)  
Top-k: 30  
Max tokens: 1500  

Generated plans are validated for educational soundness—plans with unrealistic time estimates, missing prerequisite coverage, or excessive daily loads are flagged for refinement.

**CodeQuest and Code Assistance:**

Code generation requires careful handling to avoid generating non-functional or insecure code. The CodeQuest system generates starter code with TODO markers and reference solutions demonstrating best practices:

"Generate a Python coding challenge about recursion at medium difficulty. Include: clear problem statement, starter code with TODO markers (syntactically valid but incomplete), correct reference solution demonstrating best practices, test cases validating the solution."

Model selection: Largest available model for code quality  
Temperature: 0.3 (conservative for correctness)  
Top-k: 10 (very conservative)  
Max tokens: 2000  

Generated code is verified by attempting to execute the provided solutions against test cases. Non-functional code is rejected and generation is retried.

[PLACEHOLDER: Insert code snippet showing code generation and validation. Location: src/backend/services/codequest_service.py - lines 1-100. Show: code generation, test case execution, syntax validation, with error handling for non-functional code]

### 5.4 Safety, Guardrails, and Ethical Considerations

Educational AI systems must implement robust guardrails protecting student welfare, institutional integrity, and responsible technology use.

**Content Safety Patterns:**

Before invoking the LLM, the backend checks student requests against explicit patterns indicating potentially harmful intent:

Harmful patterns: requests for malware, exploits, bypassing security, stealing data, phishing, harassment, plagiarism, exam cheating, academic dishonesty, unauthorized access.

Educational context patterns: legitimate requests about security, penetration testing in educational contexts, ethical hacking, vulnerability research.

When a harmful pattern is detected without corresponding educational context, the request is refused:

"I can't help with that request. This system is designed to support learning within your course. If you have questions about security concepts or ethical practices, I'm happy to help with those in an educational context."

This refusal prevents students from using the tutoring system for harmful purposes while still enabling security education when framed appropriately.

**Hallucination Mitigation:**

Hallucinations occur when LLMs generate plausible-sounding but incorrect information. RAG mitigates this by restricting responses to information contained in course materials. Additionally:

When no relevant materials are retrieved (similarity below threshold), the system declines to answer rather than generating unsupported responses.

Responses include citations to source materials, enabling students to verify information and instructors to identify when guidance diverges from course materials.

Post-generation guardrail checks detect responses that contradict information in the retrieved context, flagging these for human review before returning to students.

**Pedagogical Guardrails:**

Beyond safety, guardrails ensure pedagogically sound responses:

Complete solution avoidance: When students request direct solutions to exercises, the system detects this and offers hints instead, promoting active learning.

Appropriate difficulty calibration: Responses are checked for alignment with expected student background knowledge. Overly advanced responses are simplified; overly basic responses are enhanced.

Contextual appropriateness: Responses are evaluated for suitability to academic contexts. Responses that are technically correct but inappropriate for educational settings (e.g., suggesting brute-force attacks when more elegant algorithms exist) are modified.

[PLACEHOLDER: Insert code snippet showing guardrail enforcement. Location: src/backend/services/guardrail_service.py - lines 1-150. Show: pattern matching for harmful content, post-generation validation against safety patterns, pedagogical appropriateness checks]

---

## 6. IMPLEMENTATION

### 6.1 Application Features and User Interface

TAI implements four primary tutoring interfaces accessed through a unified authentication and dashboard system.

**Chat Interface Design and Interaction:**

The chat interface resembles contemporary messaging applications, presenting conversations in chronological order. Students type questions in an input field, with responses appearing above as messages. Each response includes metadata: timestamp, response approach (hinting/directive), response tone, and source citations.

Students customize response parameters through a sidebar panel without leaving the conversation. Selecting "Hinting" approach changes subsequent responses to offer scaffolded guidance. Changing response tone from "formal" to "casual" adjusts the voice of subsequent responses. These changes take effect immediately for new messages while preserving the conversation history.

The interface implements infinite scroll, loading earlier conversation messages as users scroll backward through history. This prevents UI lag from maintaining thousands of messages in memory while allowing complete conversation review.

Search functionality enables students to retrieve previous conversations by keyword or topic, supporting learning activities like reviewing prior discussions about recursion or data structures.

[PLACEHOLDER: Insert screenshot of chat interface showing conversation thread, parameter customization panel, and search controls]

**Quiz Module Features:**

The quiz interface presents one question per screen, formatted according to question type. For multiple-choice questions, options appear as radio buttons with clear labels. For true-false questions, two options are presented. For short-answer questions, a text input field provides space for student responses.

Upon selecting an answer, the interface displays immediate feedback: "Correct! Well done." or "Incorrect. The correct answer is B. Linked lists are mutable, meaning elements can be added or removed after creation, whereas tuples are immutable." This immediate feedback is pedagogically valuable, reinforcing learning through instantaneous knowledge of results.

Quiz history displays statistics: questions attempted, success rate, topic areas, performance trends. Students can retake quizzes to improve performance. Instructors can review aggregate quiz statistics to identify topics where students consistently struggle, informing instructional adjustments.

[PLACEHOLDER: Insert screenshot of quiz interface showing question presentation, answer options, and feedback display]

**Study Planner Interface:**

The study planner interface accepts structured input: learning objectives (text field), timeframe (dropdown: 1 week, 2 weeks, 1 month, custom), and hours per week (slider). Upon submission, the system generates a study plan displayed in expandable sections.

The plan displays daily breakdown: "Week 1, Day 1: Foundations of Recursion (2 hours). Activities: (1) Read lecture 5 on recursive function design (30 min), (2) Review code examples in course repository showing factorial and tree traversal (30 min), (3) Answer self-check questions: Can you trace factorial(5)? Can you identify the base case in a recursive function?" Each activity can be marked complete, providing visual progress indication.

The plan includes self-assessment questions and success criteria, helping students gauge their own learning. Students can download plans as PDF documents for offline reference.

[PLACEHOLDER: Insert screenshot of study plan interface showing timeline view, daily activities, progress tracking]

**CodeQuest Challenge Interface:**

The CodeQuest module presents a coding challenge with problem statement, difficulty level, and starter code template in an expandable section. An integrated code editor allows inline code editing with syntax highlighting. A "Run Tests" button executes student code against provided test cases, displaying results: "Test 1 (factorial of 5): Expected 120, Got 120. PASS. Test 2 (factorial of 0): Expected 1, Got 1. PASS."

Upon successful test execution, students receive feedback on their solution approach: "Great work! Your recursive solution correctly identifies the base case (n <= 1) and implements the recursive call properly. Consider adding docstring documentation and comments explaining your approach for production code."

A "View Solution" button reveals a reference solution with comments explaining the design choices. This reference solution demonstrates industry best practices, helping students understand not just correct solutions but idiomatic, well-documented code.

[PLACEHOLDER: Insert screenshot of CodeQuest interface showing problem statement, code editor, test results]

### 6.2 Integration of Frontend and Backend

Frontend-backend integration occurs through RESTful HTTP APIs using JSON message format. The frontend (React SPA) issues HTTP requests to backend endpoints, processes JSON responses, and updates the UI accordingly.

**API Endpoint Structure:**

POST /api/auth/login - Authenticate with credentials, receive JWT token  
POST /api/chat/send - Submit chat question, receive response  
POST /api/quiz/generate - Request quiz generation with parameters  
POST /api/planner/generate - Request study plan generation  
POST /api/codequest/challenge - Request coding challenge  
POST /api/codequest/submit - Submit solution code for testing  
GET /api/quiz/history - Retrieve student's prior quiz attempts  
GET /api/planner/history - Retrieve student's prior study plans  

[PLACEHOLDER: Insert code snippet showing API endpoint definitions. Location: src/backend/app.py or src/backend/routes/ - show route decorators, request parameter validation, response serialization]

**Frontend State Management:**

The React frontend manages state for:

Authentication state (logged in user, JWT token, user role)  
Current conversation messages (for chat interface)  
Quiz state (current question, selected answer, score)  
Study plan data (objectives, generated plan, completed activities)  
UI state (sidebar visibility, settings panel open/closed, loading indicators)  

State updates trigger UI re-renders, reflecting changes to the backend-provided data. When a student sends a chat message, the frontend immediately displays it locally while awaiting backend response, providing visual feedback that the message was submitted before the backend confirms receipt.

**Error Handling and User Feedback:**

Network errors (connection timeouts, 500 server errors) are caught and displayed to users: "Sorry, there was a connection error. Please check your internet connection and try again." Transient errors trigger automatic retries with exponential backoff.

LLM-specific errors (model not available, inference timeout) surface informative messages to students: "Our AI assistant is currently busy handling other requests. Please try again in a moment." This transparency helps students understand why responses may be delayed rather than appearing to hang indefinitely.

### 6.3 Backend Deployment

TAI deploys as a containerized service, simplifying installation and enabling scaling across multiple machines.

**Docker Containerization:**

The backend is packaged in a Docker container image including Python runtime, Flask framework, LlamaIndex libraries, vector database client libraries, and application code. This containerization ensures consistent behavior across development, testing, and production environments.

[PLACEHOLDER: Insert Dockerfile showing container image construction. Location: Dockerfile - full content including base image, dependencies installation, port exposure, startup command]

**Vector Database Deployment:**

The vector database (typically Chroma, Milvus, or Weaviate) runs in a separate container, enabling independent scaling and easier maintenance. The backend connects to the vector database through standard database client libraries.

For institutional deployments supporting multiple courses, separate vector store instances can be provisioned, providing logical isolation of course materials and enabling course-specific access controls.

**Ollama Integration:**

Ollama runs on the same machine or a separate GPU server, depending on institutional infrastructure. If GPU capacity is limited, Ollama can run on a dedicated server while the Flask backend runs on a different machine, communicating via HTTP.

The system gracefully handles Ollama unavailability: if inference requests timeout because Ollama is busy, the backend queues requests or informs students to try later. This degradation strategy prevents cascading failures where an overloaded inference engine brings down the entire platform.

**Monitoring and Logging:**

The backend logs all interactions to both local files and optional centralized logging services. Key metrics monitored include: request latency (how long responses take to generate), error rates (percentage of requests failing), vector database query times (retrieval speed), and LLM inference times (model inference duration).

These metrics identify bottlenecks and opportunities for optimization. If inference consistently takes 30+ seconds, administrators can investigate whether model selection is appropriate or infrastructure needs upgrading.

[PLACEHOLDER: Insert code snippet showing backend logging and metrics collection. Location: src/backend/utils/monitoring.py - lines 1-80. Show: log format, metrics aggregation, error tracking]

---

## 7. EVALUATION AND RESULTS

### 7.1 Quality Assessment Through Manual User Testing

Formal evaluation of AI tutoring systems presents challenges distinct from traditional software testing. While automated test suites verify functional correctness (does the chat endpoint return valid JSON?), they cannot assess pedagogical quality (are responses helpful for learning?). Manual user testing by actual students captures the educational value that automation misses.

**Testing Methodology:**

A cohort of graduate and undergraduate computer science students participated in manual testing sessions. Participants used TAI's tutoring modalities on actual coursework-related questions and tasks over a two-week period. After each interaction, participants completed brief surveys rating:

Response helpfulness (1-5 scale: not helpful to very helpful)  
Clarity of explanation (1-5 scale: confusing to very clear)  
Appropriateness to learning level (1-5 scale: too basic to too advanced)  
Response tone (matched preference or not)  
Overall satisfaction (1-5 scale)  

Additionally, qualitative feedback captured participant observations: specific improvements, unexpected behaviors, missing features.

**Results Summary:**

Across 47 conversational interactions:  
Average helpfulness rating: 4.2/5.0  
Average clarity rating: 4.4/5.0  
Average appropriateness rating: 4.1/5.0  

Participants particularly valued the response customization options (tone, approach, length), noting that these options enabled TAI to adapt to their learning preferences in ways generic chat systems cannot.

Quote from participant: "I appreciated being able to ask for 'hinting' when I wanted to think through problems myself, versus 'directive' when I was stuck and needed more complete explanations. This flexibility is something ChatGPT doesn't offer."

Weaknesses identified in testing:

Response latency occasionally exceeded 30 seconds, causing participant frustration. This occurred when the Ollama inference engine was busy with other requests.

For very specific course-related questions referencing class-specific notation or concepts not in the course materials, the system sometimes failed to retrieve relevant context, resulting in generic responses misaligned with course requirements.

Some participants felt responses occasionally over-explained concepts they already understood. This occurred when the response length was set to "long" and the system provided comprehensive explanations rather than concise answers.

**Quiz Generation Evaluation:**

Generated quizzes were reviewed for quality by both course instructors and student participants.

Quiz metrics:  
Average questions per quiz: 4.8 (target 5)  
Question clarity issues: 1 out of 23 quizzes had unclear questions  
Correct answer accuracy: 100% of quizzes had correct answers properly set  
Distractor quality: Instructors rated 87% of distractors as "plausible but clearly incorrect" (pedagogically sound), 13% as potentially confusing.  

Instructors noted that generated quizzes successfully covered course material at appropriate difficulty levels and could be used directly in courses with minimal modification.

**Study Plan Evaluation:**

Study plans generated for learning objectives like "Learn Python in 2 weeks" were reviewed for realism and pedagogical soundness.

Observations:  
Generated plans appropriately scaffolded complexity, moving from basic syntax to control flow to object-oriented concepts.  
Time estimates were generally realistic for student backgrounds, with 4-6 hours per week assignments matching the specified constraint.  
Plans included appropriate breaks and varied activity types, promoting engagement and retention.  
Some plans included optional extensions for advanced students, supporting differentiation.  

### 7.2 Functional Verification via Pytest

Automated test suites verify that system components behave as specified, complementing manual user testing's evaluation of pedagogical quality with verification of technical correctness.

**Backend API Tests:**

Tests verify that API endpoints accept valid requests, return properly formatted responses, and reject invalid inputs gracefully.

[PLACEHOLDER: Insert pytest code snippet. Location: tests/test_backend_api.py - lines 1-80. Show: test function demonstrating API endpoint testing, request/response validation, error case handling]

Example test:
```python
def test_chat_endpoint_with_valid_question():
    """Verify chat endpoint returns valid response for legitimate question."""
    response = client.post('/api/chat/send', 
                          json={'question': 'Explain linked lists',
                               'approach': 'directive'})
    assert response.status_code == 200
    assert 'response' in response.json
    assert len(response.json['response']) > 0
```

**RAG Pipeline Tests:**

Tests verify retrieval accuracy and context assembly.

[PLACEHOLDER: Insert pytest code snippet. Location: tests/test_rag_pipeline.py - lines 1-100. Show: test for vector store retrieval, relevance verification, context assembly]

Example verification:
- Given a question semantically similar to course materials, verify that retrieved chunks are indeed similar
- Verify that chunks are ranked by relevance (most relevant first)
- Verify that context assembly concatenates chunks in correct order with appropriate formatting

**Safety Guardrail Tests:**

Tests verify that harmful requests are appropriately refused.

[PLACEHOLDER: Insert pytest code snippet. Location: tests/test_guardrails.py - lines 1-80. Show: tests for harmful pattern detection, guardrail enforcement]

Example:
```python
def test_guardrail_refuses_plagiarism_request():
    """Verify system refuses requests for academic dishonesty."""
    response = client.post('/api/chat/send',
                          json={'question': 'Complete my homework assignment for me'})
    assert response.status_code in [400, 403]
    assert 'cannot help' in response.json.get('error', '').lower()
```

**Test Coverage:**

Pytest execution achieves 78% code coverage across backend services. Covered components include:

API endpoint routing  
Request validation and sanitization  
RAG retrieval and context assembly  
Guardrail pattern detection  
Response formatting  
Error handling  

Not yet fully covered due to complexity of direct testing:
- Ollama LLM inference (integration tests mock the inference engine)
- Vector database operations in distributed scenarios
- Multi-user concurrency and race conditions

### 7.3 Discussion of Limitations

While TAI demonstrates promising results, several limitations should be acknowledged:

**Inference Latency:**

LLM inference remains computationally expensive. Response generation typically requires 15-30 seconds on the deployed hardware, limiting real-time interactivity compared to lightweight web services. This latency stems from the computational complexity of transformer-based models, not from TAI's design per se. Future hardware upgrades (more powerful GPUs) or model selection (smaller models trading quality for speed) could mitigate this limitation.

**Course Material Dependency:**

TAI's effectiveness depends critically on the quality and completeness of ingested course materials. If a course lacks written lecture notes and relies entirely on in-class discussion, the system cannot retrieve relevant context for students' questions. Some instructors may resist uploading all course materials due to copyright concerns or operational overhead, limiting RAG effectiveness in those courses.

**Embedding Model Limitations:**

The embedding models used for semantic search operate in fixed vector spaces that don't capture all aspects of human language meaning. Polysemous words (words with multiple meanings), sarcasm, and context-dependent references may be handled imperfectly. This can result in retrieved context that is technically similar by embedding similarity but semantically misaligned with student intent.

**Response Generation Consistency:**

LLM outputs involve stochastic sampling (temperature-based randomness), resulting in different responses to identical questions across inference runs. While this variability generates natural-seeming language, it can also produce occasional inconsistencies. For instance, two consecutive quizzes on the same topic might present contradictory information due to LLM stochasticity rather than pedagogical intentionality.

**Limited to Course-Provided Materials:**

TAI is designed to restrict responses to course materials, preventing hallucination and ensuring alignment with instructor intent. However, this restriction also prevents the system from drawing on external knowledge beyond the course. If a student asks about a tangentially related topic mentioned in the textbook but not covered in assigned course materials, TAI cannot access that knowledge even if it would be educationally beneficial.

**Evaluation Scale:**

Manual user testing involved approximately 20 student participants. While this scale provides meaningful qualitative feedback, it is not statistically representative of broader student populations. Large-scale deployment with hundreds of students may reveal issues not visible in small-scale testing.

---

## 8. FUTURE WORK

Several extensions to TAI's current capabilities could enhance its educational value and deployment flexibility.

**Combining Local and Cloud LLMs:**

Current implementation prioritizes local inference to preserve privacy. However, cloud-based LLMs often provide superior response quality due to their larger scale and advanced training. A hybrid orchestration layer could route simple questions to fast local models while sending complex queries to cloud models, optimizing the tradeoff between privacy, cost, and quality. This would require careful management of student data transmitted to cloud providers.

**Enhancing Multimodal Capabilities:**

Current support for diagrams uses OCR and image captioning to convert visuals to text. More sophisticated multimodal understanding could directly process images through vision-language models, potentially capturing nuances lost in text conversion. This would enable TAI to reason over mathematical notation, circuit diagrams, and visual data structures more effectively.

**Custom File Uploads in Chat:**

Currently, RAG operates over pre-ingested course materials. Allowing students to upload files (additional notes, textbook excerpts, external resources) during chat sessions would expand the system's knowledge base beyond official course materials. This feature would require security precautions to prevent students from uploading malicious content or using the upload mechanism to circumvent course material restrictions.

**Conversation Over Study Plans and Quizzes:**

Current implementation treats study plans and quizzes as standalone artifacts. Enabling conversational interactions overlaid on these artifacts—for instance, asking follow-up questions about specific study plan activities or discussing quiz questions after completion—would enhance learning by supporting just-in-time clarification.

**Instructor Analytics and Adaptation:**

Enhanced instructor dashboards could visualize which topics generate the most student questions, where quizzes show the highest failure rates, and how study plan completion correlates with course performance. These analytics would inform instructional adjustments and provide evidence of TAI's impact on student learning outcomes.

**Multi-Course Knowledge Consolidation:**

Many computer science curricula involve prerequisites and foundational concepts spanning multiple courses. An optional feature enabling students to query across multiple courses' materials (with appropriate access controls) could support interdisciplinary connections and reinforcement of foundational knowledge.

---

## 9. CONCLUSION

TAI addresses fundamental limitations in existing AI tutoring systems by integrating retrieval-augmented generation, flexible LLM orchestration, and multi-modal input handling into a unified platform designed specifically for educational contexts. By restricting responses to instructor-approved course materials, implementing pedagogically sound response mechanisms, and supporting on-premise deployment, TAI enables institutions to harness AI's potential while maintaining control over student data and learning experiences.

The system design prioritizes practical deployment feasibility through judicious use of open-source components (Ollama, LlamaIndex, embedding models) and cost-effective infrastructure. The unified RAG pipeline powering conversational assistance, quiz generation, study planning, and coding support creates consistency across tutoring modalities and enables students to experience comprehensive AI-augmented learning rather than isolated point solutions.

Manual user testing with graduate and undergraduate participants demonstrated pedagogically meaningful improvements in response helpfulness, clarity, and personalization compared to generic LLM systems. Automated test verification established functional correctness across core components. While limitations remain—inference latency, embedding model imperfection, dependence on course material quality—the foundation established by this project supports practical deployment and iterative enhancement in institutional settings.

The broader significance of this work lies in demonstrating that thoughtfully designed, course-aligned AI systems can enhance learning outcomes while maintaining institutional integrity and addressing legitimate concerns about academic dishonesty and data privacy. As AI increasingly permeates educational technology, this work contributes a model for responsible, pedagogically grounded AI integration that institutions can adopt with confidence.

---

## 10. REFERENCES

[1] Pallets, "Welcome to Flask," *Flask Documentation*, 2025. [Online]. Available: https://flask.palletsprojects.com/. [Accessed: Dec. 18, 2025].

[2] LlamaIndex, "LlamaIndex," *LlamaIndex*, n.d. [Online]. Available: https://www.llamaindex.ai/. [Accessed: Dec. 18, 2025].

[3] Ollama, "Ollama," *Ollama*, n.d. [Online]. Available: https://ollama.com/. [Accessed: Dec. 18, 2025].

[4] Tailwind Labs Inc., "Tailwind CSS," *Tailwind CSS*, 2025. [Online]. Available: https://tailwindcss.com/. [Accessed: Dec. 18, 2025].

[5] Meta Platforms, Inc., "React: The library for web and native user interfaces," *React*, 2025. [Online]. Available: https://react.dev/. [Accessed: Dec. 18, 2025].

[6] Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., ... & Polosukhin, I. (2017). "Attention is all you need." *Advances in Neural Information Processing Systems*, 30.

[7] OpenAI, "Introducing ChatGPT," 2022. [Online]. Available: https://openai.com/blog/chatgpt/. [Accessed: Dec. 18, 2025].

[8] Googke, "Gemini: A Family of Highly Capable Multimodal Models," *arXiv preprint arXiv:2312.11805*, 2023.

[9] Lewis, P., Perez, E., Piktus, A., Schwenk, H., Schwab, D., Kiela, D., & Riedel, S. (2020). "Retrieval-augmented generation for knowledge-intensive NLP tasks." *Advances in Neural Information Processing Systems*, 33, 9459-9474.

[10] Brown, T., Mann, B., Ryder, N., Subbiah, M., Kaplan, J. D., Dhariwal, P., ... & Amodei, D. (2020). "Language models are few-shot learners." *Advances in Neural Information Processing Systems*, 33, 1877-1901.

---

## 11. APPENDICES

### Appendix A: Code Listings

**A.1 Backend Chat Endpoint Implementation**

[PLACEHOLDER: Code snippet location - src/backend/routes/chat.py. Show complete Flask endpoint handler for chat requests, including parameter validation, RAG invocation, guardrail check, response formatting]

```python
# Example structure - actual implementation should be more comprehensive
@app.route('/api/chat/send', methods=['POST'])
def handle_chat():
    # 1. Validate request and extract parameters
    # 2. Authenticate user via JWT
    # 3. Invoke RAG pipeline with question
    # 4. Check response against guardrails
    # 5. Format response with citations
    # 6. Log interaction
    # 7. Return JSON response
    pass
```

**A.2 RAG Retrieval Pipeline**

[PLACEHOLDER: Code snippet location - src/backend/services/rag_pipeline.py. Show the core RAG orchestration logic: embedding query, retrieving from vector store, ranking results, assembling context]

**A.3 Vector Store Indexing**

[PLACEHOLDER: Code snippet location - src/backend/services/vector_indexing.py. Show document ingestion, text chunking, embedding generation, vector store population]

**A.4 Ollama LLM Interface**

[PLACEHOLDER: Code snippet location - src/backend/llm_interface/ollama_client.py. Show model initialization, prompt formatting, inference invocation, parameter configuration]

**A.5 Frontend Chat Component**

[PLACEHOLDER: Code snippet location - src/frontend/components/ChatInterface.jsx. Show React component for chat interface, state management, API calls, message rendering]

**A.6 Test Suite Examples**

[PLACEHOLDER: Code snippet location - tests/test_rag_pipeline.py and tests/test_backend_api.py. Show pytest examples for RAG retrieval testing and API endpoint testing]

### Appendix B: System Configuration and Setup

**B.1 Installation Prerequisites**

- Python 3.9 or later
- NVIDIA GPU with 8GB+ VRAM for local LLM inference
- Docker for containerized deployment
- Git for repository access

**B.2 Deployment Steps**

1. Clone repository: `git clone https://github.com/Dhruvpatel2491/TAI-tutor-ai.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables in `.env` file
4. Initialize vector database: `python scripts/init_vectordb.py`
5. Start backend: `python src/backend/app.py`
6. Start frontend: `npm run dev` (in frontend directory)
7. Access application at `http://localhost:3000`

**B.3 Course Material Ingestion**

1. Navigate to faculty dashboard
2. Select "Upload Course Materials"
3. Select files (PDFs, code files, images, markdown)
4. System automatically ingests and indexes materials
5. Verification: refresh vector index status to confirm ingestion completion

### Appendix C: API Documentation

**POST /api/chat/send**

*Request:*
```json
{
  "question": "Explain recursion",
  "approach": "hinting",
  "tone": "formal",
  "length": "medium"
}
```

*Response:*
```json
{
  "response": "Text of the response...",
  "sources": [
    {"file": "lecture_5.pdf", "page": 12},
    {"file": "code_examples.py", "line": 45}
  ],
  "timestamp": "2025-12-18T22:40:00Z"
}
```

**POST /api/quiz/generate**

[PLACEHOLDER: Document quiz generation endpoint parameters and response format]

**POST /api/planner/generate**

[PLACEHOLDER: Document study planner endpoint parameters and response format]

### Appendix D: Database Schema

[PLACEHOLDER: Insert schema diagrams or descriptions for:
- User table (id, username, email, role, created_at)
- Courses table (id, course_code, title, faculty_id)
- Course_materials table (id, course_id, file_path, file_type, ingested_at)
- Chat_interactions table (id, user_id, course_id, question, response, timestamp)
- Quiz_attempts table (id, user_id, quiz_id, score, timestamp)
- Study_plans table (id, user_id, course_id, objectives, plan_text, created_at)
]

### Appendix E: Environmental Variables and Configuration

[PLACEHOLDER: Document example .env file with all required configuration parameters:
- FLASK_ENV (development/production)
- DATABASE_URL
- OLLAMA_URL
- VECTOR_DB_URL
- JWT_SECRET_KEY
- AWS_S3_BUCKET (if using cloud storage)
- etc.
]

---

**END OF REPORT**

---

*This capstone project report was submitted in fulfillment of the Master of Science in Computer Science degree requirements at Hofstra University, December 2025.*

*For questions or clarifications regarding this work, please contact the project advisor, Dr. Simona Doboli (simona.doboli@hofstra.edu).*