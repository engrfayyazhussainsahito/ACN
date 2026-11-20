# Chatbot tests
Run from the site root (the folder containing `index.html`):

    node source/tests/chat_test.js      # retrieval: 58 in-scope/out-of-scope questions
    node source/tests/heldout_test.js   # held-out questions
    node source/tests/rag_test.js       # RAG pipeline with a mock model
    node source/tests/worker_test.mjs   # the proxy Worker with a mock model provider
    npm install jsdom && node source/tests/ui_test.js   # the widget in a simulated browser

None of these call a real model. They check retrieval, prompt construction, citation handling, safety (escaping), fallbacks and the proxy's validation. They do not prove the quality of a real model's answers.
